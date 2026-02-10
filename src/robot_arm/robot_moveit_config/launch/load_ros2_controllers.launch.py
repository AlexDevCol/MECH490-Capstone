#!/usr/bin/env python3
"""
Launch ROS 2 controllers for any robot (panda, rob, bb01).

This script creates a launch description that starts the necessary controllers
for operating any robot in a specific sequence.

The robot is selected via the 'robot' argument:
    robot:=panda  # Load panda robot controllers
    robot:=rob    # Load rob robot controllers
    robot:=bb01   # Load bb01 robot controllers

Controller sequences:
    - rob: joint_state_broadcaster -> arm_controller -> gripper_action_controller
    - bb01: joint_state_broadcaster -> arm_controller (no gripper)
    - panda: joint_state_broadcaster -> panda_arm_controller -> panda_hand_controller

:author: MECH490-Capstone Team
:date: February 2026
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, RegisterEventHandler, TimerAction, OpaqueFunction
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration


# Robot controller configuration dictionary
ROBOT_CONTROLLERS = {
    'panda': {
        'arm_controller': 'panda_arm_controller',
        'gripper_controller': 'panda_hand_controller',
        'has_gripper': True,
    },
    'rob': {
        'arm_controller': 'arm_controller',
        'gripper_controller': 'gripper_action_controller',
        'has_gripper': True,
    },
    'bb01': {
        'arm_controller': 'arm_controller',
        'gripper_controller': None,
        'has_gripper': False,
    },
}


def generate_launch_description():
    """Generate a launch description for sequentially starting robot controllers.

    Returns:
        LaunchDescription: Launch description containing sequenced controller starts
    """
    # Declare robot argument
    declare_robot_cmd = DeclareLaunchArgument(
        name='robot',
        default_value='rob',
        choices=['panda', 'rob', 'bb01'],
        description='Robot to use (panda, rob, or bb01)')

    def configure_controllers(context):
        """Configure controllers based on robot selection."""
        robot_str = LaunchConfiguration('robot').perform(context)
        
        # Validate robot selection
        if robot_str not in ROBOT_CONTROLLERS:
            raise ValueError(f"Unknown robot: {robot_str}. Must be one of {list(ROBOT_CONTROLLERS.keys())}")
        
        config = ROBOT_CONTROLLERS[robot_str]
        
        # Start arm controller
        start_arm_controller_cmd = ExecuteProcess(
            cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
                 config['arm_controller']],
            output='screen')

        # Launch joint state broadcaster
        start_joint_state_broadcaster_cmd = ExecuteProcess(
            cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
                 'joint_state_broadcaster'],
            output='screen')

        # Add delay to joint state broadcaster (wait for Gazebo)
        delayed_start = TimerAction(
            period=10.0,
            actions=[start_joint_state_broadcaster_cmd]
        )

        # Register event handlers for sequencing
        # Launch the arm controller after launching the joint state broadcaster
        load_arm_controller_cmd = RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=start_joint_state_broadcaster_cmd,
                on_exit=[start_arm_controller_cmd]))

        actions = [delayed_start, load_arm_controller_cmd]

        # If robot has gripper, add gripper controller after arm controller
        if config['has_gripper']:
            start_gripper_controller_cmd = ExecuteProcess(
                cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
                     config['gripper_controller']],
                output='screen')

            load_gripper_controller_cmd = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=start_arm_controller_cmd,
                    on_exit=[start_gripper_controller_cmd]))
            
            actions.append(load_gripper_controller_cmd)

        return actions

    # Create the launch description
    ld = LaunchDescription()

    # Add the robot argument
    ld.add_action(declare_robot_cmd)

    # Add the controller configuration
    ld.add_action(OpaqueFunction(function=configure_controllers))

    return ld
