#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <control_msgs/msg/joint_jog.hpp>
#include <moveit_msgs/srv/servo_command_type.hpp>
#include <termios.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <thread>
#include <chrono>
#include <map>

// Non-blocking keyboard input
int getch()
{
  static struct termios oldt, newt;
  tcgetattr(STDIN_FILENO, &oldt);
  newt = oldt;
  newt.c_lflag &= ~(ICANON | ECHO);
  tcsetattr(STDIN_FILENO, TCSANOW, &newt);
  int c = getchar();
  tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
  return c;
}

// Check if a key is pressed (non-blocking)
bool kbhit()
{
  struct termios oldt, newt;
  int ch;
  int oldf;

  tcgetattr(STDIN_FILENO, &oldt);
  newt = oldt;
  newt.c_lflag &= ~(ICANON | ECHO);
  tcsetattr(STDIN_FILENO, TCSANOW, &newt);
  oldf = fcntl(STDIN_FILENO, F_GETFL, 0);
  fcntl(STDIN_FILENO, F_SETFL, oldf | O_NONBLOCK);

  ch = getchar();

  tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
  fcntl(STDIN_FILENO, F_SETFL, oldf);

  if (ch != EOF)
  {
    ungetc(ch, stdin);
    return true;
  }

  return false;
}

class KeyboardServoNode : public rclcpp::Node
{
public:
  KeyboardServoNode() : Node("keyboard_servo_node")
  {
    // Parameters
    this->declare_parameter("planning_frame", "base_link");
    this->declare_parameter("cartesian_speed_scale", 0.5);
    this->declare_parameter("joint_speed_scale", 0.5);

    planning_frame_ = this->get_parameter("planning_frame").as_string();
    cartesian_speed_scale_ = this->get_parameter("cartesian_speed_scale").as_double();
    joint_speed_scale_ = this->get_parameter("joint_speed_scale").as_double();

    // Publishers
    twist_pub_ = this->create_publisher<geometry_msgs::msg::TwistStamped>(
        "/servo_node/delta_twist_cmds", 10);
    joint_jog_pub_ = this->create_publisher<control_msgs::msg::JointJog>(
        "/servo_node/delta_joint_cmds", 10);

    // Service Client
    switch_command_client_ = this->create_client<moveit_msgs::srv::ServoCommandType>(
        "/servo_node/switch_command_type");

    // Joint names for bb01
    joint_names_ = {"joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"};

    // Start input loop thread
    input_thread_ = std::thread(&KeyboardServoNode::inputLoop, this);

    RCLCPP_INFO(this->get_logger(), "Keyboard Servo Node Initialized");
    printInstructions();
  }

  ~KeyboardServoNode()
  {
    running_ = false;
    if (input_thread_.joinable())
      input_thread_.join();
  }

private:
  void printInstructions()
  {
    std::cout << "\n==========================================\n";
    std::cout << "BB01 Keyboard Servo Control (C++)\n";
    std::cout << "==========================================\n";
    std::cout << "\n*** Starts in JOINT JOG mode ***\n";
    std::cout << "*** Use 1-6 keys to jog the arm away ***\n";
    std::cout << "*** from singularity before switching ***\n";
    std::cout << "*** to Twist mode with 't' key.      ***\n";
    std::cout << "\nJoint Jog Mode (default):\n";
    std::cout << "  1 - 6      : Jog Joints 1-6 (+)\n";
    std::cout << "  Shift+1-6  : Jog Joints 1-6 (-)\n";
    std::cout << "\nTwist Mode:\n";
    std::cout << "  Arrow Keys : Linear X/Y\n";
    std::cout << "  u / o      : Linear Z +/- \n";
    std::cout << "  j / l      : Angular Roll (X) +/- \n";
    std::cout << "  i / k      : Angular Pitch (Y) +/- \n";
    std::cout << "  n / m      : Angular Yaw (Z) +/- \n";
    std::cout << "\nGeneral:\n";
    std::cout << "  t          : Switch to Twist Mode\n";
    std::cout << "  g          : Switch to Joint Jog Mode\n";
    std::cout << "  q          : Quit\n";
    std::cout << "==========================================\n";
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
    current_mode_ = mode;
    RCLCPP_INFO(this->get_logger(), "Switched to mode: %d", mode);
  }

  void publishTwist(double lx, double ly, double lz, double ax, double ay, double az)
  {
    auto twist_msg = std::make_unique<geometry_msgs::msg::TwistStamped>();
    twist_msg->header.stamp = this->now();
    twist_msg->header.frame_id = planning_frame_;

    twist_msg->twist.linear.x = lx * cartesian_speed_scale_;
    twist_msg->twist.linear.y = ly * cartesian_speed_scale_;
    twist_msg->twist.linear.z = lz * cartesian_speed_scale_;
    twist_msg->twist.angular.x = ax * cartesian_speed_scale_;
    twist_msg->twist.angular.y = ay * cartesian_speed_scale_;
    twist_msg->twist.angular.z = az * cartesian_speed_scale_;

    twist_pub_->publish(std::move(twist_msg));
  }

  void publishJointJog(int joint_idx, double direction)
  {
    if (joint_idx < 0 || joint_idx >= static_cast<int>(joint_names_.size())) return;

    auto joint_msg = std::make_unique<control_msgs::msg::JointJog>();
    joint_msg->header.stamp = this->now();
    joint_msg->header.frame_id = planning_frame_;
    
    joint_msg->joint_names.push_back(joint_names_[joint_idx]);
    joint_msg->velocities.push_back(direction * joint_speed_scale_);

    joint_jog_pub_->publish(std::move(joint_msg));
  }

  void inputLoop()
  {
    // Start in JOINT_JOG mode to avoid singularity issues at home pose.
    // The user should jog the arm away from the singular candle position
    // before switching to TWIST mode with 't'.
    std::this_thread::sleep_for(std::chrono::seconds(2));
    switchMode(moveit_msgs::srv::ServoCommandType::Request::JOINT_JOG);

    while (running_ && rclcpp::ok())
    {
      int c = getch();

      // Check for arrow keys (escape sequences)
      if (c == 27) {
        getch(); // skip [
        switch(getch()) {
          case 'A': // Up
            if (current_mode_ == moveit_msgs::srv::ServoCommandType::Request::TWIST)
              publishTwist(1.0, 0, 0, 0, 0, 0);
            break;
          case 'B': // Down
            if (current_mode_ == moveit_msgs::srv::ServoCommandType::Request::TWIST)
              publishTwist(-1.0, 0, 0, 0, 0, 0);
            break;
          case 'C': // Right
            if (current_mode_ == moveit_msgs::srv::ServoCommandType::Request::TWIST)
              publishTwist(0, -1.0, 0, 0, 0, 0);
            break;
          case 'D': // Left
            if (current_mode_ == moveit_msgs::srv::ServoCommandType::Request::TWIST)
              publishTwist(0, 1.0, 0, 0, 0, 0);
            break;
        }
        continue;
      }

      switch (c)
      {
        case 'q':
          running_ = false;
          rclcpp::shutdown();
          break;
        case 't':
          switchMode(moveit_msgs::srv::ServoCommandType::Request::TWIST);
          break;
        case 'g':
          switchMode(moveit_msgs::srv::ServoCommandType::Request::JOINT_JOG);
          break;
        
        // Cartesian Z
        case 'u': publishTwist(0, 0, 1.0, 0, 0, 0); break;
        case 'o': publishTwist(0, 0, -1.0, 0, 0, 0); break;

        // Angular
        case 'j': publishTwist(0, 0, 0, 1.0, 0, 0); break;
        case 'l': publishTwist(0, 0, 0, -1.0, 0, 0); break;
        case 'i': publishTwist(0, 0, 0, 0, 1.0, 0); break;
        case 'k': publishTwist(0, 0, 0, 0, -1.0, 0); break;
        case 'n': publishTwist(0, 0, 0, 0, 0, 1.0); break;
        case 'm': publishTwist(0, 0, 0, 0, 0, -1.0); break;

        // Joint Jog (1-6)
        case '1': publishJointJog(0, 1.0); break;
        case '2': publishJointJog(1, 1.0); break;
        case '3': publishJointJog(2, 1.0); break;
        case '4': publishJointJog(3, 1.0); break;
        case '5': publishJointJog(4, 1.0); break;
        case '6': publishJointJog(5, 1.0); break;
        
        // Joint Jog Negative (! through ^)
        case '!': publishJointJog(0, -1.0); break;
        case '@': publishJointJog(1, -1.0); break;
        case '#': publishJointJog(2, -1.0); break;
        case '$': publishJointJog(3, -1.0); break;
        case '%': publishJointJog(4, -1.0); break;
        case '^': publishJointJog(5, -1.0); break;
      }
      
      // Small sleep to prevent CPU hogging
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
  }

  // Members
  std::string planning_frame_;
  double cartesian_speed_scale_;
  double joint_speed_scale_;
  std::vector<std::string> joint_names_;
  int8_t current_mode_;
  bool running_ = true;
  std::thread input_thread_;

  rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr twist_pub_;
  rclcpp::Publisher<control_msgs::msg::JointJog>::SharedPtr joint_jog_pub_;
  rclcpp::Client<moveit_msgs::srv::ServoCommandType>::SharedPtr switch_command_client_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<KeyboardServoNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
