#!/usr/bin/env python3
"""
Launch MoveIt Servo for any robot (panda, rob, bb01).

This script creates a ROS 2 launch file that starts the MoveIt Servo node
for realtime control of any robot. It loads servo configuration files from
robots/<robot>/config/, and integrates with the existing move_group node.

The robot is selected via the 'robot' argument:
    robot:=panda  # Load panda robot servo config
    robot:=rob    # Load rob robot servo config
    robot:=bb01   # Load bb01 robot servo config

:author: MECH490-Capstone Team
:date: February 2026
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from launch_param_builder import ParameterBuilder
from moveit_configs_utils import MoveItConfigsBuilder
from ament_index_python.packages import get_package_share_directory


from launch.conditions import IfCondition

# Robot configuration dictionary
ROBOT_CONFIGS = {
    'panda': {
        'default_robot_name': 'panda',
        'move_group_name': 'panda_arm',
    },
    'rob': {
        'default_robot_name': 'rob',
        'move_group_name': 'arm',
    },
    'bb01': {
        'default_robot_name': 'bb01',
        'move_group_name': 'arm',
    },
}


def generate_launch_description():
    """
    Generate a launch description for MoveIt Servo with any robot.

    This function sets up the necessary configuration and nodes to launch MoveIt Servo
    for controlling any robot. It includes setting up paths to config files,
    declaring launch arguments, and configuring the servo_node.

    Returns:
        LaunchDescription: A complete launch description for MoveIt Servo
    """
    # Constants for paths to different files and folders
    package_name_moveit_config = 'robot_moveit_config'

    # Launch configuration variables
    robot = LaunchConfiguration('robot')
    use_gazebo = LaunchConfiguration('use_gazebo')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_xbox = LaunchConfiguration('use_xbox')

    # Get the package share directory
    pkg_share_moveit_config_temp = FindPackageShare(package=package_name_moveit_config)

    # Declare the launch arguments
    declare_robot_cmd = DeclareLaunchArgument(
        name='robot',
        default_value='bb01',
        choices=['panda', 'rob', 'bb01'],
        description='Robot to use (panda, rob, or bb01)')

    declare_robot_name_cmd = DeclareLaunchArgument(
        name='robot_name',
        default_value='',
        description='Name of the robot (defaults to robot argument value)')

    declare_use_gazebo_cmd = DeclareLaunchArgument(
        name='use_gazebo',
        default_value='true',
        description='Use Gazebo simulation if true, real hardware if false')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true. Should match use_gazebo parameter.')

    declare_use_xbox_cmd = DeclareLaunchArgument(
        name='use_xbox',
        default_value='false',
        description='Launch Xbox controller bridge (joy_node + joy_to_servo_node)')

    declare_use_keyboard_cmd = DeclareLaunchArgument(
        name='use_keyboard',
        default_value='false',
        description='Launch C++ keyboard input node (requires its own terminal -- better to run manually)')

    def configure_setup(context):
        """Configure Servo and create nodes with proper string conversions."""
        # Get the robot selection and name
        robot_str = robot.perform(context)
        robot_name_str = LaunchConfiguration('robot_name').perform(context)
        
        # If robot_name not provided, use robot value
        if not robot_name_str:
            robot_name_str = robot_str
        
        # Validate robot selection
        if robot_str not in ROBOT_CONFIGS:
            raise ValueError(f"Unknown robot: {robot_str}. Must be one of {list(ROBOT_CONFIGS.keys())}")

        # Get robot config
        config = ROBOT_CONFIGS[robot_str]

        # Get package path
        pkg_share_moveit_config = pkg_share_moveit_config_temp.find(package_name_moveit_config)

        # Construct file paths using robot name string
        # Configs are in robots/<robot>/config/
        config_path = os.path.join(pkg_share_moveit_config, 'robots', robot_str, 'config')

        # Define servo config file path
        servo_config_file_path = os.path.join(config_path, f'{robot_name_str}_servo.yaml')

        # Check if servo config exists, if not, use default servo_parameters.yaml structure
        if not os.path.exists(servo_config_file_path):
            raise FileNotFoundError(
                f"Servo config file not found: {servo_config_file_path}\n"
                f"Please create {robot_name_str}_servo.yaml in {config_path}/"
            )

        # Define other config file paths needed for MoveIt
        joint_limits_file_path = os.path.join(config_path, 'joint_limits.yaml')
        kinematics_file_path = os.path.join(config_path, 'kinematics.yaml')
        srdf_model_path = os.path.join(config_path, f'{robot_name_str}.srdf')
        pilz_cartesian_limits_file_path = os.path.join(config_path, 'pilz_cartesian_limits.yaml')

        # Load the URDF via xacro so we can pass robot_description explicitly to the servo node.
        # The official MoveIt Servo tutorial passes robot_description as a node parameter.
        # Without it, the servo node must subscribe to /robot_description topic, which can have
        # timing issues and may cause Jacobian computation failures (manifesting as singularity errors).
        pkg_share_description = get_package_share_directory('robot_description')
        urdf_xacro_path = os.path.join(
            pkg_share_description, 'robots', robot_str, 'urdf', f'{robot_str}.urdf.xacro'
        )
        # Get use_gazebo value from context
        use_gazebo_str = use_gazebo.perform(context)
        robot_description_content = ParameterValue(
            Command(['xacro ', urdf_xacro_path,
                     ' add_world:=true',
                     f' use_gazebo:={use_gazebo_str}',
                     f' robot_name:={robot_name_str}']),
            value_type=str
        )
        robot_description_param = {'robot_description': robot_description_content}

        # Create MoveIt configuration
        # We explicitly provide file paths to avoid MoveItConfigsBuilder trying to infer paths.
        # We provide pilz_cartesian_limits to prevent MoveItConfigsBuilder from trying to infer it.
        moveit_config = (
            MoveItConfigsBuilder(robot_name_str, package_name=package_name_moveit_config)
            .robot_description_semantic(file_path=srdf_model_path)
            .joint_limits(file_path=joint_limits_file_path)
            .robot_description_kinematics(file_path=kinematics_file_path)
            .pilz_cartesian_limits(file_path=pilz_cartesian_limits_file_path)
            .to_moveit_configs()
        )

        # Get parameters for the Servo node using ParameterBuilder
        # ParameterBuilder needs the relative path from package share
        servo_config_relative_path = os.path.join("robots", robot_str, "config", f"{robot_name_str}_servo.yaml")
        servo_params = {
            "moveit_servo": ParameterBuilder("robot_moveit_config")
            .yaml(servo_config_relative_path)
            .to_dict()
        }

        # Parameters for the acceleration limiting filter
        acceleration_filter_update_period = {"update_period": 0.01}
        planning_group_name = {"planning_group_name": config['move_group_name']}

        # Create servo_node
        # Pass robot_description explicitly (as recommended by official MoveIt Servo tutorial)
        start_servo_node_cmd = Node(
            package="moveit_servo",
            executable="servo_node",
            name="servo_node",
            output="screen",
            parameters=[
                servo_params,
                acceleration_filter_update_period,
                planning_group_name,
                robot_description_param,
                moveit_config.robot_description_semantic,
                moveit_config.robot_description_kinematics,
                moveit_config.joint_limits,
                {'use_sim_time': use_sim_time}
            ],
        )

        # Launch joy_node for Xbox controller
        start_joy_node_cmd = Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_xbox')),
            parameters=[{'use_sim_time': use_sim_time}]
        )

        # Launch C++ joy_to_servo bridge
        start_joy_to_servo_node_cmd = Node(
            package='rob_cpp_pkg',
            executable='joy_to_servo_node',
            name='joy_to_servo_node',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_xbox')),
            parameters=[
                {'use_sim_time': use_sim_time},
                {'move_group_name': config['move_group_name']},
                {'planning_frame': 'world'},  # bb01 uses world/base_link
                {'ee_frame': 'link_6'},       # bb01 end effector
                {'cartesian_speed_scale': 1.0},
                {'joint_speed_scale': 1.0}
            ]
        )

        # Launch C++ keyboard servo node (optional, default off)
        # This node requires its own terminal with stdin access for keyboard capture.
        # Recommended: run it manually in a separate terminal instead:
        #   ros2 run rob_cpp_pkg keyboard_servo_node --ros-args -p planning_frame:=world -p use_sim_time:=true
        start_keyboard_servo_node_cmd = Node(
            package='rob_cpp_pkg',
            executable='keyboard_servo_node',
            name='keyboard_servo_node',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_keyboard')),
            parameters=[
                {'use_sim_time': use_sim_time},
                {'planning_frame': 'world'},
                {'cartesian_speed_scale': 0.5},
                {'joint_speed_scale': 0.5}
            ]
        )

        return [start_servo_node_cmd, start_joy_node_cmd, start_joy_to_servo_node_cmd, start_keyboard_servo_node_cmd]

    # Create the launch description
    ld = LaunchDescription()

    # Add the launch arguments
    ld.add_action(declare_robot_cmd)
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_use_gazebo_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_use_xbox_cmd)
    ld.add_action(declare_use_keyboard_cmd)

    # Add the setup and node creation
    ld.add_action(OpaqueFunction(function=configure_setup))

    return ld
