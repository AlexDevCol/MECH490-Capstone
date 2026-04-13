#!/usr/bin/env python3
"""
Launch RViz visualization for any robot in the robot_description package.

This launch file sets up the complete visualization environment for any robot,
including robot state publisher, joint state publisher, and RViz2. It handles loading
and processing of URDF/XACRO files and controller configurations.

The robot is selected via the 'robot' argument:
    robot:=panda  # Load panda robot
    robot:=rob    # Load rob robot
    robot:=bb01   # Load bb01 robot

:author: MECH490-Capstone Team
:date: January 20, 2026
"""
import os
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, GroupAction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def process_ros2_controllers_config(context):
    """Process the ROS 2 controller configuration yaml file before loading the URDF.

    This function reads a template configuration file, replaces placeholder values
    with actual configuration, and writes the processed file to both source and
    install directories.

    Args:
        context: Launch context containing configuration values

    Returns:
        list: Empty list as required by OpaqueFunction
    """
    # Get the robot value (robot_name not available yet, defaults to robot anyway)
    robot_val = LaunchConfiguration('robot').perform(context)
    robot_name = robot_val  # robot_name defaults to robot value

    # Note: Controller config processing can be added here if needed
    # For now, this is a placeholder that matches the original structure
    return []


def generate_launch_description():
    """Generate the launch description for robot visualization.

    This function sets up all necessary nodes and parameters for visualizing
    any robot in RViz, including:
    - Robot state publisher for broadcasting transforms
    - Joint state publisher for simulating joint movements
    - RViz for visualization

    Returns:
        LaunchDescription: Complete launch description for the visualization setup
    """
    # Define the arguments for the XACRO file
    ARGUMENTS = [
        DeclareLaunchArgument(
            'robot',
            default_value='rob',
            choices=['panda', 'rob', 'bb01'],
            description='Robot to load (panda, rob, or bb01)'
        ),
        DeclareLaunchArgument(
            'add_world',
            default_value='true',
            choices=['true', 'false'],
            description='Whether to add world link'
        ),
        DeclareLaunchArgument(
            'use_camera',
            default_value='false',
            choices=['true', 'false'],
            description='Whether to use the RGBD Gazebo plugin for point cloud'
        ),
        DeclareLaunchArgument(
            'use_gazebo',
            default_value='false',
            choices=['true', 'false'],
            description='Whether to use Gazebo simulation'
        ),
    ]

    # Use OpaqueFunction to configure launch based on robot selection
    def configure_launch(context):
        """Configure launch description based on robot selection."""
        robot_val = LaunchConfiguration('robot').perform(context)
        
        # robot_name defaults to robot value
        robot_name_val = robot_val
        
        # Get package share directory
        pkg_share_description = get_package_share_directory('robot_description')
        
        # Build URDF path: robots/<robot>/urdf/<robot>.urdf.xacro
        urdf_file = os.path.join(
            pkg_share_description,
            'robots',
            robot_val,
            'urdf',
            f'{robot_val}.urdf.xacro'
        )
        
        # Build RViz config path based on robot
        rviz_config_file = os.path.join(
            pkg_share_description,
            'rviz',
            f'display_{robot_val}.rviz'
        )
        
        # Launch configuration variables
        jsp_gui = LaunchConfiguration('jsp_gui')
        rviz_config_file_cfg = LaunchConfiguration('rviz_config_file')
        urdf_model = LaunchConfiguration('urdf_model')
        use_rviz = LaunchConfiguration('use_rviz')
        use_sim_time = LaunchConfiguration('use_sim_time')
        robot_name = LaunchConfiguration('robot_name')

        # Declare the launch arguments
        declare_jsp_gui_cmd = DeclareLaunchArgument(
            name='jsp_gui',
            default_value='true',
            choices=['true', 'false'],
            description='Flag to enable joint_state_publisher_gui'
        )

        declare_rviz_config_file_cmd = DeclareLaunchArgument(
            name='rviz_config_file',
            default_value=rviz_config_file,
            description='Full path to the RVIZ config file to use'
        )

        declare_urdf_model_path_cmd = DeclareLaunchArgument(
            name='urdf_model',
            default_value=urdf_file,
            description='Absolute path to robot urdf file'
        )

        declare_use_rviz_cmd = DeclareLaunchArgument(
            name='use_rviz',
            default_value='true',
            description='Whether to start RVIZ'
        )

        declare_use_sim_time_cmd = DeclareLaunchArgument(
            name='use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'
        )

        declare_robot_name_cmd = DeclareLaunchArgument(
            name='robot_name',
            default_value=robot_name_val,
            description='Name of the robot (defaults to robot argument value)'
        )

        # Build robot description content with xacro
        robot_description_content = ParameterValue(Command([
            'xacro', ' ', urdf_model, ' ',
            'robot_name:=', robot_name, ' ',
            'add_world:=', LaunchConfiguration('add_world'), ' ',
            'use_camera:=', LaunchConfiguration('use_camera'), ' ',
            'use_gazebo:=', LaunchConfiguration('use_gazebo'), ' ',
        ]), value_type=str)

        # Subscribe to the joint states of the robot, and publish the 3D pose of each link.
        start_robot_state_publisher_cmd = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'robot_description': robot_description_content
            }]
        )

        # Publish the joint state values for the non-fixed joints in the URDF file.
        start_joint_state_publisher_cmd = Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            parameters=[{'use_sim_time': use_sim_time}],
            condition=UnlessCondition(jsp_gui)
        )

        # Depending on gui parameter, either launch joint_state_publisher or joint_state_publisher_gui
        start_joint_state_publisher_gui_cmd = Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(jsp_gui)
        )

        jsp_group = GroupAction(
            actions=[
                start_joint_state_publisher_cmd,
                start_joint_state_publisher_gui_cmd,
            ],
            # This group only runs if use_gazebo is false
            condition=UnlessCondition(LaunchConfiguration('use_gazebo'))
        )

        # Launch RViz
        start_rviz_cmd = Node(
            condition=IfCondition(use_rviz),
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file_cfg],
            parameters=[{'use_sim_time': use_sim_time}]
        )

        return [
            declare_jsp_gui_cmd,
            declare_rviz_config_file_cmd,
            declare_urdf_model_path_cmd,
            declare_use_rviz_cmd,
            declare_use_sim_time_cmd,
            declare_robot_name_cmd,
            jsp_group,
            start_robot_state_publisher_cmd,
            start_rviz_cmd,
        ]

    # Create the launch description and populate
    ld = LaunchDescription(ARGUMENTS)

    # Process the controller configuration before starting nodes (if needed)
    ld.add_action(OpaqueFunction(function=process_ros2_controllers_config))

    # Configure launch based on robot selection
    ld.add_action(OpaqueFunction(function=configure_launch))

    return ld
