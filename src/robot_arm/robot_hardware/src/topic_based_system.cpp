#include "robot_hardware/topic_based_system.hpp"

#include <chrono>
#include <mutex>
#include <string>
#include <vector>

#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp/rclcpp.hpp"

namespace robot_hardware
{

TopicBasedSystem::TopicBasedSystem()
: open_loop_(true),
  cmd_topic_name_("/joint_position_commands"),
  feedback_topic_name_("/joint_position_feedback")
{
}

TopicBasedSystem::~TopicBasedSystem()
{
  if (executor_running_.load()) {
    executor_running_.store(false);
    if (executor_thread_.joinable()) {
      executor_thread_.join();
    }
  }
}

hardware_interface::CallbackReturn TopicBasedSystem::on_init(
  const hardware_interface::HardwareInfo & info)
{
  if (hardware_interface::SystemInterface::on_init(info) !=
    hardware_interface::CallbackReturn::SUCCESS)
  {
    return hardware_interface::CallbackReturn::ERROR;
  }

  // Extract joint names from hardware info
  joint_names_.clear();
  for (const auto & joint : info_.joints) {
    joint_names_.push_back(joint.name);
  }

  // Read parameters from URDF
  if (info_.hardware_parameters.find("open_loop") != info_.hardware_parameters.end()) {
    open_loop_ = (info_.hardware_parameters.at("open_loop") == "true");
  }

  if (info_.hardware_parameters.find("cmd_topic") != info_.hardware_parameters.end()) {
    cmd_topic_name_ = info_.hardware_parameters.at("cmd_topic");
  }

  if (info_.hardware_parameters.find("feedback_topic") != info_.hardware_parameters.end()) {
    feedback_topic_name_ = info_.hardware_parameters.at("feedback_topic");
  }

  // Initialize feedback vector
  latest_feedback_.resize(joint_names_.size(), 0.0);

  // Initialize state and command storage
  joint_states_.resize(joint_names_.size(), 0.0);
  joint_commands_.resize(joint_names_.size(), 0.0);

  RCLCPP_INFO(
    get_logger(),
    "TopicBasedSystem initialized with %zu joints, open_loop=%s",
    joint_names_.size(), open_loop_ ? "true" : "false");

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn TopicBasedSystem::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // Create internal ROS node
  node_ = std::make_shared<rclcpp::Node>("topic_based_system_node");

  // Create publisher for joint position commands (RELIABLE — matches ESP32's subscriber)
  cmd_publisher_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>(
    cmd_topic_name_, rclcpp::QoS(10).reliable());

  // Create subscriber for joint position feedback
  // Use BEST_EFFORT to reduce serial overhead (no ACK required).
  // A BEST_EFFORT subscriber matches a RELIABLE publisher (micro-ROS agent).
  feedback_subscriber_ = node_->create_subscription<std_msgs::msg::Float64MultiArray>(
    feedback_topic_name_, rclcpp::SensorDataQoS(),
    std::bind(&TopicBasedSystem::feedback_callback, this, std::placeholders::_1));

  // Create executor and start it in a background thread
  executor_ = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
  executor_->add_node(node_);

  executor_running_.store(true);
  executor_thread_ = std::thread([this]() {
      while (executor_running_.load() && rclcpp::ok()) {
        executor_->spin_once(std::chrono::milliseconds(10));
      }
    });

  RCLCPP_INFO(
    get_logger(),
    "TopicBasedSystem configured: cmd_topic='%s', feedback_topic='%s'",
    cmd_topic_name_.c_str(), feedback_topic_name_.c_str());

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn TopicBasedSystem::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // Initialize state interfaces to 0.0 (home position)
  for (size_t i = 0; i < joint_names_.size(); ++i) {
    joint_states_[i] = 0.0;
    joint_commands_[i] = 0.0;
  }

  // Publish initial command to prevent jump on startup
  std_msgs::msg::Float64MultiArray initial_cmd;
  initial_cmd.data.resize(joint_names_.size(), 0.0);
  cmd_publisher_->publish(initial_cmd);

  RCLCPP_INFO(get_logger(), "TopicBasedSystem activated");

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn TopicBasedSystem::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_INFO(get_logger(), "TopicBasedSystem deactivated");
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn TopicBasedSystem::on_cleanup(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // Stop executor thread
  executor_running_.store(false);
  if (executor_thread_.joinable()) {
    executor_thread_.join();
  }

  // Clean up publishers/subscribers
  cmd_publisher_.reset();
  feedback_subscriber_.reset();
  executor_.reset();
  node_.reset();

  RCLCPP_INFO(get_logger(), "TopicBasedSystem cleaned up");

  return hardware_interface::CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> TopicBasedSystem::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> state_interfaces;

  for (size_t i = 0; i < joint_names_.size(); ++i) {
    state_interfaces.emplace_back(
      hardware_interface::StateInterface(
        joint_names_[i],
        hardware_interface::HW_IF_POSITION,
        &joint_states_[i]
      )
    );
  }

  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface> TopicBasedSystem::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> command_interfaces;

  for (size_t i = 0; i < joint_names_.size(); ++i) {
    command_interfaces.emplace_back(
      hardware_interface::CommandInterface(
        joint_names_[i],
        hardware_interface::HW_IF_POSITION,
        &joint_commands_[i]
      )
    );
  }

  return command_interfaces;
}

hardware_interface::return_type TopicBasedSystem::read(
  const rclcpp::Time & /*time*/,
  const rclcpp::Duration & /*period*/)
{
  if (open_loop_) {
    // Echo command values into state interfaces
    for (size_t i = 0; i < joint_names_.size(); ++i) {
      joint_states_[i] = joint_commands_[i];
    }
  } else {
    // Copy latest feedback into state interfaces
    std::lock_guard<std::mutex> lock(feedback_mutex_);
    if (latest_feedback_.size() == joint_names_.size()) {
      for (size_t i = 0; i < joint_names_.size(); ++i) {
        joint_states_[i] = latest_feedback_[i];
      }
    }
  }

  return hardware_interface::return_type::OK;
}

hardware_interface::return_type TopicBasedSystem::write(
  const rclcpp::Time & /*time*/,
  const rclcpp::Duration & /*period*/)
{
  // Read command values from interfaces and pack into Float64MultiArray
  std_msgs::msg::Float64MultiArray cmd_msg;
  cmd_msg.data.resize(joint_names_.size());

  for (size_t i = 0; i < joint_names_.size(); ++i) {
    cmd_msg.data[i] = joint_commands_[i];
  }

  // Throttle publishing to ~10 Hz to avoid flooding micro-ROS serial transport.
  // ros2_control calls write() at 100 Hz, but the ESP32 serial link (115200 baud)
  // cannot sustain 100 msgs/s without buffer overflow and session drops.
  static auto last_publish_time = std::chrono::steady_clock::now();
  auto now = std::chrono::steady_clock::now();
  auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_publish_time).count();
  if (elapsed_ms >= 100) {  // publish at most every 100 ms = 10 Hz
    cmd_publisher_->publish(cmd_msg);
    last_publish_time = now;
  }

  return hardware_interface::return_type::OK;
}

void TopicBasedSystem::feedback_callback(
  const std_msgs::msg::Float64MultiArray::SharedPtr msg)
{
  if (msg->data.size() == joint_names_.size()) {
    std::lock_guard<std::mutex> lock(feedback_mutex_);
    latest_feedback_ = msg->data;
  } else {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), 5000,
      "Received feedback with %zu elements, expected %zu",
      msg->data.size(), joint_names_.size());
  }
}

}  // namespace robot_hardware

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(robot_hardware::TopicBasedSystem, hardware_interface::SystemInterface)
