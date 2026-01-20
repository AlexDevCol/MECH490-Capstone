#!/usr/bin/env python3
"""
Launch file to spawn BB01_URDF robot in Gazebo Sim.

This launch file starts Gazebo Sim with an empty world, spawns the BB01_URDF robot,
and sets up necessary transforms and bridges.
"""

import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # --- Package Paths ---
    pkg_share = get_package_share_directory('BB01_URDF')
    ros_gz_sim_pkg_share = get_package_share_directory("ros_gz_sim")
    
    # --- Declare Launch Arguments ---
    model_arg = DeclareLaunchArgument(
        name="model",
        default_value=os.path.join(pkg_share, "urdf", "BB01_URDF.urdf"),
        description="Absolute path to robot URDF file"
    )
    
    robot_name_arg = DeclareLaunchArgument(
        name="robot_name",
        default_value="BB01_URDF",
        description="Name for the robot model in Gazebo"
    )
    
    # --- Environment Variable Setup ---
    # Set GZ_SIM_RESOURCE_PATH so Gazebo can find meshes
    gazebo_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=[str(Path(pkg_share).parent.resolve())]
    )
    
    # --- Robot Description Processing ---
    # Load URDF file content
    default_urdf_path = os.path.join(pkg_share, "urdf", "BB01_URDF.urdf")
    with open(default_urdf_path, 'r') as infile:
        robot_description_content = infile.read()
    
    robot_description = ParameterValue(robot_description_content, value_type=str)
    
    # --- Nodes ---
    # Robot State Publisher
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": True
        }],
        output="screen"
    )
    
    # Gazebo Simulation (Include the standard Gazebo Sim launch file)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_pkg_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": " -v 4 -r empty.sdf"
        }.items()
    )
    
    # Static transform publisher from base_link to base_footprint
    static_tf_footprint = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="tf_footprint_base",
        arguments=["0", "0", "0", "0", "0", "0", "base_link", "base_footprint"],
        output="screen"
    )
    
    # Gazebo Spawner (Creates the robot entity in Gazebo)
    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "/robot_description",
            "-name", LaunchConfiguration("robot_name"),
            "-allow_renaming", "true",
            "-x", "0.0",
            "-y", "0.0",
            "-z", "0.1",
            "-R", "0.0",
            "-P", "0.0",
            "-Y", "0.0"
        ],
        parameters=[{'use_sim_time': True}]
    )
    
    # ROS-Gazebo Bridge for clock
    gz_ros2_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock]"],
        parameters=[{'use_sim_time': True}],
        output="screen"
    )
    
    # --- Assemble Launch Description ---
    return LaunchDescription([
        # Declare Arguments
        model_arg,
        robot_name_arg,
        
        # Set Environment Variable
        gazebo_resource_path,
        
        # Launch Nodes
        robot_state_publisher_node,
        gazebo,
        static_tf_footprint,
        gz_spawn_entity,
        gz_ros2_bridge
    ])
