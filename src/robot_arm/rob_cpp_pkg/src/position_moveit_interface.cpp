#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>

int main(int argc, char **argv)
{
  // Initialize ROS 2
  rclcpp::init(argc, argv);
  auto const node = std::make_shared<rclcpp::Node>(
    "position_moveit_interface",
    rclcpp::NodeOptions().automatically_declare_parameters_from_overrides(true)
  );

  auto const logger = rclcpp::get_logger("position_moveit_interface");

  // Enable simulation time if needed
  if (node->get_parameter("use_sim_time").as_bool()) {
    RCLCPP_INFO(logger, "Simulation time enabled.");
  }

  // Setup MoveIt MoveGroupInterface
  using moveit::planning_interface::MoveGroupInterface;
  auto arm_group_interface = MoveGroupInterface(node, "arm");

  arm_group_interface.setEndEffectorLink("link5");

  // Wait for valid joint states
  auto start_time = node->now();
  while (!arm_group_interface.getCurrentState() && (node->now() - start_time).seconds() < 10.0) {  // Increased timeout from 5.0 to 10.0 seconds
    RCLCPP_WARN(logger, "Waiting for valid joint states...");
    rclcpp::sleep_for(std::chrono::milliseconds(500));
  }

  if (!arm_group_interface.getCurrentState()) {
    RCLCPP_ERROR(logger, "Failed to fetch valid joint states within timeout. Ensure joint states are being published.");
    rclcpp::shutdown();
    return 1;
  }

  // Get current pose
  auto current_pose = arm_group_interface.getCurrentPose();
  RCLCPP_INFO(logger, "x position: %f", current_pose.pose.position.x);
  RCLCPP_INFO(logger, "y position: %f", current_pose.pose.position.y);
  RCLCPP_INFO(logger, "z position: %f", current_pose.pose.position.z);
  RCLCPP_INFO(logger, "x orientation: %f", current_pose.pose.orientation.x);
  RCLCPP_INFO(logger, "y orientation: %f", current_pose.pose.orientation.y);
  RCLCPP_INFO(logger, "z orientation: %f", current_pose.pose.orientation.z);
  RCLCPP_INFO(logger, "w orientation: %f", current_pose.pose.orientation.w);

  // Print reference frame and end-effector link
  RCLCPP_INFO(logger, "Reference frame: %s", arm_group_interface.getPlanningFrame().c_str());
  RCLCPP_INFO(logger, "End effector link: %s", arm_group_interface.getEndEffectorLink().c_str());

  // Set target pose
  geometry_msgs::msg::Pose target_pose1;
  target_pose1.position.x = 0.120679;
  target_pose1.position.y = 0.072992;
  target_pose1.position.z = 0.569166;
  target_pose1.orientation.x = -0.386473;
  target_pose1.orientation.y = -0.418023;
  target_pose1.orientation.z = -0.760978;
  target_pose1.orientation.w = 0.311139;

  arm_group_interface.setPoseTarget(target_pose1);

  // Plan and execute
  auto const [success, plan] = [&arm_group_interface] {
    moveit::planning_interface::MoveGroupInterface::Plan msg;
    auto const ok = static_cast<bool>(arm_group_interface.plan(msg));
    return std::make_pair(ok, msg);
  }();

  if (success)
  {
    RCLCPP_INFO(logger, "Visualizing plan 1 (pose goal)");
    arm_group_interface.execute(plan);
  }
  else
  {
    RCLCPP_ERROR(logger, "Planning failed!");
  }

  rclcpp::shutdown();
  return 0;
}