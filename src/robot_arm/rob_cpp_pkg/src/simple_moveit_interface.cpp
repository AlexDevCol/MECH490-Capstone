#include <memory>
#include <chrono>
#include "rclcpp/rclcpp.hpp"
#include "moveit/move_group_interface/move_group_interface.hpp"

void move_robot(const std::shared_ptr<rclcpp::Node> node)
{
    // Move the arm
    {
        auto move_group = moveit::planning_interface::MoveGroupInterface(node, "arm");
        move_group.setMaxVelocityScalingFactor(0.5);
        move_group.setMaxAccelerationScalingFactor(0.5);
        if (!move_group.setJointValueTarget({0.0, 0.0, 0.0, 0.0, 0.0})) {
            RCLCPP_WARN(node->get_logger(), "Target joint positions for arm out of bounds");
            return;
        }
        moveit::planning_interface::MoveGroupInterface::Plan plan;
        if (move_group.plan(plan) == moveit::core::MoveItErrorCode::SUCCESS) {
            move_group.execute(plan);
            rclcpp::sleep_for(std::chrono::seconds(1));
        } else {
            RCLCPP_ERROR(node->get_logger(), "Arm planning failed");
        }
    }

    // Move the gripper
    {
        auto move_group = moveit::planning_interface::MoveGroupInterface(node, "gripper");
        move_group.setMaxVelocityScalingFactor(0.5);
        move_group.setMaxAccelerationScalingFactor(0.5);
        if (!move_group.setJointValueTarget({1.0})) {
            RCLCPP_WARN(node->get_logger(), "Target joint positions for gripper out of bounds");
            return;
        }
        moveit::planning_interface::MoveGroupInterface::Plan plan;
        if (move_group.plan(plan) == moveit::core::MoveItErrorCode::SUCCESS) {
            move_group.execute(plan);
            rclcpp::sleep_for(std::chrono::seconds(1));
        } else {
            RCLCPP_ERROR(node->get_logger(), "Gripper planning failed");
        }
    }
}

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("simple_moveit_interface");
    
    // Wait for system initialization
    rclcpp::sleep_for(std::chrono::seconds(2));

    // Move the robot
    move_robot(node);

    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}