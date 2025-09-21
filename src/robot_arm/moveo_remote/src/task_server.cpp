#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <rclcpp_components/register_node_macro.hpp>
#include "moveo_interfaces/action/moveo_task.hpp"
#include <moveit/move_group_interface/move_group_interface.hpp>
#include <control_msgs/action/gripper_command.hpp>

#include <memory>
#include <thread>

using namespace std::placeholders;

namespace moveo_remote
{
class TaskServer : public rclcpp::Node
{
public:
  explicit TaskServer(const rclcpp::NodeOptions & options = rclcpp::NodeOptions())
    : Node("task_server", options)
  {
    RCLCPP_INFO(this->get_logger(), "Task server started");
    action_server_ = rclcpp_action::create_server<moveo_interfaces::action::MoveoTask>(
      this, "task_server", std::bind(&TaskServer::goalCallback, this, _1, _2),
      std::bind(&TaskServer::cancelCallback, this, _1),
      std::bind(&TaskServer::acceptCallback, this, _1));
  }

private:
  using Task = moveo_interfaces::action::MoveoTask;
  using GoalHandleTask = rclcpp_action::ServerGoalHandle<Task>;

  rclcpp_action::Server<Task>::SharedPtr action_server_;
  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> arm_move_group_;
  std::vector<double> arm_joint_goal_;
  double gripper_position_;

  rclcpp_action::GoalResponse goalCallback(
    const rclcpp_action::GoalUUID & uuid,
    std::shared_ptr<const Task::Goal> goal)
  {
    RCLCPP_INFO(this->get_logger(), "Received goal request with task-number %d", goal->task_number);
    (void)uuid;  // Ignore unused variable warning
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse cancelCallback(
    const std::shared_ptr<GoalHandleTask> goal_handle)
  {
    RCLCPP_INFO(this->get_logger(), "Received cancel request");
    if(arm_move_group_)
    {
      arm_move_group_->stop();
    }
    (void)goal_handle;  // Ignore unused variable warning
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void acceptCallback(
    const std::shared_ptr<GoalHandleTask> goal_handle)
  {
    std::thread{ std::bind(&TaskServer::execute, this, goal_handle) }.detach();
  }

  void execute(const std::shared_ptr<GoalHandleTask> goal_handle)
  {
    RCLCPP_INFO(this->get_logger(), "Executing task");
    if(!arm_move_group_)
    {
      arm_move_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(shared_from_this(), "arm");
    }
    auto result = std::make_shared<Task::Result>();

    // Arm joint goals
    if(goal_handle->get_goal()->task_number == 0){
      arm_joint_goal_ = {0.0, 0.0, 0.0, 0.0, 0.0};
      // Gripper position for task 0
      gripper_position_ = 0.0;
    } else if(goal_handle->get_goal()->task_number == 1){
        arm_joint_goal_ = {1.5, 0.0, 0.0, 0.0, 0.0};
        // Gripper position for task 1
        gripper_position_ = 0.5;
    } else if(goal_handle->get_goal()->task_number == 2){
        arm_joint_goal_ = {1.5, 0.0, 0.0, 0.0, 1.5};
        // Gripper position for task 2
        gripper_position_ = 1.0;
    } else {
        RCLCPP_ERROR(this->get_logger(), "Invalid task number");
        return;
    }

    // Arm movement
    arm_move_group_->setStartState(*arm_move_group_->getCurrentState());
    bool arm_within_bounds = arm_move_group_->setJointValueTarget(arm_joint_goal_);
    if(!arm_within_bounds)
    {
      RCLCPP_ERROR(this->get_logger(), "Target position is out of bounds");
      return;
    }

    arm_move_group_->setMaxVelocityScalingFactor(1.0);
    arm_move_group_->setMaxAccelerationScalingFactor(1.0);

    moveit::planning_interface::MoveGroupInterface::Plan arm_plan;
    bool arm_plan_success = (arm_move_group_->plan(arm_plan) == moveit::core::MoveItErrorCode::SUCCESS);

    if(arm_plan_success)
    {
      arm_move_group_->move();
      RCLCPP_INFO(this->get_logger(), "Arm task executed successfully");
    }
    else
    {
      RCLCPP_ERROR(this->get_logger(), "Failed to plan arm task");
      return;
    }

    // Gripper action
    using GripperCommand = control_msgs::action::GripperCommand;
    auto gripper_action_client = rclcpp_action::create_client<GripperCommand>(shared_from_this(), "/gripper_controller/gripper_cmd");

    if (!gripper_action_client->wait_for_action_server(std::chrono::seconds(5))) {
      RCLCPP_ERROR(this->get_logger(), "Gripper action server not available");
      return;
    }

    auto goal_msg = GripperCommand::Goal();
    goal_msg.command.position = gripper_position_; // Set gripper position based on task
    goal_msg.command.max_effort = 5.0;

    auto send_goal_options = rclcpp_action::Client<GripperCommand>::SendGoalOptions();
    send_goal_options.result_callback = [this](const auto & result) {
      if (result.code == rclcpp_action::ResultCode::SUCCEEDED) {
        RCLCPP_INFO(this->get_logger(), "Gripper action succeeded");
      } else {
        RCLCPP_ERROR(this->get_logger(), "Gripper action failed");
      }
    };

    gripper_action_client->async_send_goal(goal_msg, send_goal_options);

    result->success = true;
    goal_handle->succeed(result);
    RCLCPP_INFO(this->get_logger(), "Task completed");
  }
};
} // namespace moveo_remote

RCLCPP_COMPONENTS_REGISTER_NODE(moveo_remote::TaskServer)