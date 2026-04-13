#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joy.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <control_msgs/msg/joint_jog.hpp>
#include <moveit_msgs/srv/servo_command_type.hpp>
#include <thread>

class JoyToServoNode : public rclcpp::Node
{
public:
  JoyToServoNode() : Node("joy_to_servo_node")
  {
    // Parameters
    this->declare_parameter("move_group_name", "arm");
    this->declare_parameter("planning_frame", "base_link");
    this->declare_parameter("ee_frame", "link_6");
    this->declare_parameter("cartesian_speed_scale", 1.0);
    this->declare_parameter("joint_speed_scale", 1.0);

    planning_frame_ = this->get_parameter("planning_frame").as_string();
    ee_frame_ = this->get_parameter("ee_frame").as_string();
    cartesian_speed_scale_ = this->get_parameter("cartesian_speed_scale").as_double();
    joint_speed_scale_ = this->get_parameter("joint_speed_scale").as_double();

    // Publishers
    twist_pub_ = this->create_publisher<geometry_msgs::msg::TwistStamped>(
        "/servo_node/delta_twist_cmds", 10);
    joint_jog_pub_ = this->create_publisher<control_msgs::msg::JointJog>(
        "/servo_node/delta_joint_cmds", 10);

    // Subscribers
    joy_sub_ = this->create_subscription<sensor_msgs::msg::Joy>(
        "/joy", 10, std::bind(&JoyToServoNode::joyCallback, this, std::placeholders::_1));

    // Service Client
    switch_command_client_ = this->create_client<moveit_msgs::srv::ServoCommandType>(
        "/servo_node/switch_command_type");

    // Initialize state
    current_mode_ = moveit_msgs::srv::ServoCommandType::Request::TWIST;
    
    // Joint names for bb01 (could be parameterized, but hardcoded for robustness for now)
    joint_names_ = {"joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"};

    RCLCPP_INFO(this->get_logger(), "Joy to Servo Node Initialized");
    RCLCPP_INFO(this->get_logger(), "Press 'A' for Twist Mode, 'B' for Joint Jog Mode");
  }

private:
  void joyCallback(const sensor_msgs::msg::Joy::SharedPtr msg)
  {
    // Xbox Controller Mapping (Standard)
    // Axes:
    // 0: Left Stick L/R (Linear Y)
    // 1: Left Stick U/D (Linear X)
    // 2: LT (Angular Roll - X) - Note: often 0 to -1 or 1 range
    // 3: Right Stick L/R (Angular Yaw - Z)
    // 4: Right Stick U/D (Linear Z)
    // 5: RT (Angular Pitch - Y)
    // 6: D-Pad L/R
    // 7: D-Pad U/D
    
    // Buttons:
    // 0: A (Twist Mode)
    // 1: B (Joint Jog Mode)
    // 2: X
    // 3: Y
    // 4: LB
    // 5: RB
    
    // Mode Switching
    if (msg->buttons[0] && current_mode_ != moveit_msgs::srv::ServoCommandType::Request::TWIST) {
      switchMode(moveit_msgs::srv::ServoCommandType::Request::TWIST);
    } else if (msg->buttons[1] && current_mode_ != moveit_msgs::srv::ServoCommandType::Request::JOINT_JOG) {
      switchMode(moveit_msgs::srv::ServoCommandType::Request::JOINT_JOG);
    }

    if (current_mode_ == moveit_msgs::srv::ServoCommandType::Request::TWIST) {
      publishTwist(msg);
    } else {
      publishJointJog(msg);
    }
  }

  void publishTwist(const sensor_msgs::msg::Joy::SharedPtr msg)
  {
    auto twist_msg = std::make_unique<geometry_msgs::msg::TwistStamped>();
    twist_msg->header.stamp = this->now();
    twist_msg->header.frame_id = planning_frame_;

    // Map axes to Twist
    // Left Stick: Linear X/Y
    twist_msg->twist.linear.x = msg->axes[1] * cartesian_speed_scale_;
    twist_msg->twist.linear.y = msg->axes[0] * cartesian_speed_scale_;
    
    // Right Stick U/D: Linear Z
    twist_msg->twist.linear.z = msg->axes[4] * cartesian_speed_scale_;

    // Triggers/Bumpers for Rotation
    // LT/RT for Roll (X) - mapped to axes 2 and 5
    // Note: Triggers often rest at 1.0 and go to -1.0. We need to normalize.
    // Simple mapping: RB/LB buttons for Roll
    double roll = 0.0;
    if (msg->buttons[5]) roll -= 1.0; // RB
    if (msg->buttons[4]) roll += 1.0; // LB
    twist_msg->twist.angular.x = roll * cartesian_speed_scale_;

    // Right Stick L/R: Yaw (Z)
    twist_msg->twist.angular.z = msg->axes[3] * cartesian_speed_scale_;

    // D-Pad U/D: Pitch (Y)
    twist_msg->twist.angular.y = msg->axes[7] * cartesian_speed_scale_;

    twist_pub_->publish(std::move(twist_msg));
  }

  void publishJointJog(const sensor_msgs::msg::Joy::SharedPtr msg)
  {
    auto joint_msg = std::make_unique<control_msgs::msg::JointJog>();
    joint_msg->header.stamp = this->now();
    joint_msg->header.frame_id = planning_frame_;
    
    // Map D-Pad and Buttons to Joints
    // D-Pad L/R: Joint 1
    if (std::abs(msg->axes[6]) > 0.1) {
      joint_msg->joint_names.push_back(joint_names_[0]);
      joint_msg->velocities.push_back(msg->axes[6] * joint_speed_scale_);
    }
    
    // D-Pad U/D: Joint 2
    if (std::abs(msg->axes[7]) > 0.1) {
      joint_msg->joint_names.push_back(joint_names_[1]);
      joint_msg->velocities.push_back(msg->axes[7] * joint_speed_scale_);
    }

    // Left Stick U/D: Joint 3
    if (std::abs(msg->axes[1]) > 0.1) {
      joint_msg->joint_names.push_back(joint_names_[2]);
      joint_msg->velocities.push_back(msg->axes[1] * joint_speed_scale_);
    }

    // Left Stick L/R: Joint 4
    if (std::abs(msg->axes[0]) > 0.1) {
      joint_msg->joint_names.push_back(joint_names_[3]);
      joint_msg->velocities.push_back(msg->axes[0] * joint_speed_scale_);
    }

    // Right Stick U/D: Joint 5
    if (std::abs(msg->axes[4]) > 0.1) {
      joint_msg->joint_names.push_back(joint_names_[4]);
      joint_msg->velocities.push_back(msg->axes[4] * joint_speed_scale_);
    }

    // Right Stick L/R: Joint 6
    if (std::abs(msg->axes[3]) > 0.1) {
      joint_msg->joint_names.push_back(joint_names_[5]);
      joint_msg->velocities.push_back(msg->axes[3] * joint_speed_scale_);
    }

    if (!joint_msg->joint_names.empty()) {
      joint_jog_pub_->publish(std::move(joint_msg));
    }
  }

  void switchMode(int8_t mode)
  {
    if (!switch_command_client_->wait_for_service(std::chrono::seconds(1))) {
      RCLCPP_WARN(this->get_logger(), "Switch command service not available");
      return;
    }

    auto request = std::make_shared<moveit_msgs::srv::ServoCommandType::Request>();
    request->command_type = mode;

    auto future = switch_command_client_->async_send_request(request);
    
    // Don't block in callback, just log
    // In a real application, we might want to handle the response
    current_mode_ = mode;
    RCLCPP_INFO(this->get_logger(), "Switched to mode: %d", mode);
  }

  // Members
  std::string planning_frame_;
  std::string ee_frame_;
  double cartesian_speed_scale_;
  double joint_speed_scale_;
  std::vector<std::string> joint_names_;
  int8_t current_mode_;

  rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr twist_pub_;
  rclcpp::Publisher<control_msgs::msg::JointJog>::SharedPtr joint_jog_pub_;
  rclcpp::Subscription<sensor_msgs::msg::Joy>::SharedPtr joy_sub_;
  rclcpp::Client<moveit_msgs::srv::ServoCommandType>::SharedPtr switch_command_client_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<JoyToServoNode>());
  rclcpp::shutdown();
  return 0;
}
