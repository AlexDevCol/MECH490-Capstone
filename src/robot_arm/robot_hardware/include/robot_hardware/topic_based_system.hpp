#ifndef ROBOT_HARDWARE__TOPIC_BASED_SYSTEM_HPP_
#define ROBOT_HARDWARE__TOPIC_BASED_SYSTEM_HPP_

#include <atomic>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"

namespace robot_hardware
{

class TopicBasedSystem : public hardware_interface::SystemInterface
{
public:
  TopicBasedSystem();
  ~TopicBasedSystem();

  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareInfo & info) override;

  hardware_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_cleanup(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::return_type read(
    const rclcpp::Time & time,
    const rclcpp::Duration & period) override;

  hardware_interface::return_type write(
    const rclcpp::Time & time,
    const rclcpp::Duration & period) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;

  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

private:
  // Internal ROS node for pub/sub
  std::shared_ptr<rclcpp::Node> node_;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
  std::thread executor_thread_;
  std::atomic<bool> executor_running_{false};

  // Publishers and subscribers
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr cmd_publisher_;
  rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr feedback_subscriber_;

  // Latest feedback received (protected by mutex or atomic operations)
  std::vector<double> latest_feedback_;
  std::mutex feedback_mutex_;

  // Configuration parameters
  bool open_loop_;
  std::string cmd_topic_name_;
  std::string feedback_topic_name_;

  // Joint names from URDF
  std::vector<std::string> joint_names_;

  // State and command storage (indexed by [joint_index])
  std::vector<double> joint_states_;   // position values for each joint
  std::vector<double> joint_commands_; // position commands for each joint

  // Feedback callback
  void feedback_callback(const std_msgs::msg::Float64MultiArray::SharedPtr msg);
};

}  // namespace robot_hardware

#endif  // ROBOT_HARDWARE__TOPIC_BASED_SYSTEM_HPP_
