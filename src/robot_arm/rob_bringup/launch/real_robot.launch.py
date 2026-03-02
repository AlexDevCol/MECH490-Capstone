#!/usr/bin/env python3
"""
Launch file for real BB01 robot hardware bringup.

This launch file starts all necessary nodes for operating the BB01 robot
with real hardware (ESP32 via micro-ROS), including:
- robot_state_publisher (with use_gazebo:=false to load TopicBasedSystem plugin)
- controller_manager with ros2_controllers.yaml
- Sequential controller loading (joint_state_broadcaster -> arm_controller)
- micro_ros_agent (serial bridge to ESP32)
- MoveIt move_group
- Optional RViz (via move_group.launch.py with proper MoveIt configuration)

Usage:
    ros2 launch rob_bringup real_robot.launch.py [robot:=bb01] [use_rviz:=true] [port:=/dev/ttyUSB0]

:author: MECH490-Capstone Team
:date: February 2026
"""

import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess,
    TimerAction,
    RegisterEventHandler,
    OpaqueFunction,
)
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    """Generate launch description for real robot bringup."""

    # Declare launch arguments
    declare_robot_cmd = DeclareLaunchArgument(
        name='robot',
        default_value='bb01',
        choices=['bb01'],
        description='Robot to use (currently only bb01 supported)'
    )

    declare_use_rviz_cmd = DeclareLaunchArgument(
        name='use_rviz',
        default_value='true',
        description='Whether to start RViz'
    )

    declare_port_cmd = DeclareLaunchArgument(
        name='port',
        default_value='/dev/ttyUSB0',
        description='Serial port for micro-ROS agent (e.g., /dev/ttyUSB0)'
    )

    # Use OpaqueFunction to configure launch based on robot selection
    ld = LaunchDescription()
    ld.add_action(declare_robot_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_port_cmd)
    ld.add_action(OpaqueFunction(function=configure_launch))

    return ld


def configure_launch(context):
    """Configure launch description based on robot selection."""
    robot = LaunchConfiguration('robot').perform(context)
    use_rviz = LaunchConfiguration('use_rviz')
    port = LaunchConfiguration('port')

    # Get package share directories
    pkg_share_description = get_package_share_directory('robot_description')
    pkg_share_moveit = get_package_share_directory('robot_moveit_config')

    # Build URDF path: robots/<robot>/urdf/<robot>.urdf.xacro
    urdf_file = os.path.join(
        pkg_share_description,
        'robots',
        robot,
        'urdf',
        f'{robot}.urdf.xacro'
    )

    # Build robot description content with xacro (use_gazebo:=false loads TopicBasedSystem)
    robot_description_content = ParameterValue(
        Command([
            'xacro', ' ', urdf_file, ' ',
            'robot_name:=', robot, ' ',
            'add_world:=true', ' ',
            'use_camera:=false', ' ',
            'use_gazebo:=false',
        ]),
        value_type=str
    )

    # Create robot_description parameter dict for passing to nodes
    robot_description = {'robot_description': robot_description_content}

    # Start robot_state_publisher (standalone node, no joint_state_publisher or RViz)
    robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': False},
            robot_description
        ],
    )

    # Start controller_manager with ros2_controllers.yaml
    # Pass robot_description as parameter so it doesn't need to subscribe to topic
    controller_config_file = os.path.join(
        pkg_share_moveit, 'robots', robot, 'config', 'ros2_controllers.yaml'
    )

    controller_manager_cmd = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            controller_config_file,
            robot_description  # Pass URDF directly as parameter
        ],
        output='screen',
        remappings=[
            ("~/robot_description", "/robot_description"),
        ],
    )

    # Load controllers using spawner nodes (standard ros2_control tool)
    # Spawner automatically waits for controller_manager to be ready
    # First: joint_state_broadcaster
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output='screen',
    )

    # Second: arm_controller (after joint_state_broadcaster loads)
    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_controller"],
        output='screen',
    )

    # Sequence controllers: arm_controller after joint_state_broadcaster
    load_arm_controller_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner]
        )
    )

    # Start micro-ROS agent (serial bridge to ESP32)
    micro_ros_agent_cmd = ExecuteProcess(
        cmd=['ros2', 'run', 'micro_ros_agent', 'micro_ros_agent', 'serial', '--dev', port],
        output='screen'
    )

    # Delay micro-ROS agent startup (wait for controller_manager)
    delayed_micro_ros_agent = TimerAction(
        period=2.0,
        actions=[micro_ros_agent_cmd]
    )

    # Start MoveIt move_group (with RViz if requested)
    # Pass use_rviz through so move_group.launch.py creates properly-configured RViz
    move_group_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share_moveit, 'launch', 'move_group.launch.py')
        ]),
        launch_arguments={
            'robot': robot,
            'use_sim_time': 'false',
            'use_rviz': use_rviz,  # Pass through use_rviz argument
        }.items(),
    )

    # Delay MoveIt startup (wait for controllers to be loaded)
    delayed_move_group = TimerAction(
        period=5.0,
        actions=[move_group_cmd]
    )

    return [
        robot_state_publisher_cmd,
        controller_manager_cmd,
        joint_state_broadcaster_spawner,
        load_arm_controller_handler,
        delayed_micro_ros_agent,
        delayed_move_group,
    ]
