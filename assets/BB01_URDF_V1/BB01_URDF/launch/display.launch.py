#!/usr/bin/env python3
"""
Launch file to display BB01_URDF robot in RViz2.

This launch file starts the robot state publisher, joint state publisher GUI,
and RViz2 for visualizing the BB01_URDF robot model.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
import os
from ament_index_python.packages import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterValue


def generate_nodes(context):
    """Generate nodes with robot description loaded from URDF file."""
    # Get the model path from launch configuration
    model_path = LaunchConfiguration('model').perform(context)
    
    # Read URDF file
    with open(model_path, 'r') as infile:
        robot_description_content = infile.read()
    
    robot_description = ParameterValue(robot_description_content, value_type=str)
    
    # Robot state publisher node
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen"
    )
    
    # Joint state publisher GUI node
    joint_state_publisher_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        output="screen"
    )
    
    # RViz2 node
    rviz2_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen"
    )
    
    return [robot_state_publisher, joint_state_publisher_gui, rviz2_node]


def generate_launch_description():
    # Get package share directory
    pkg_share = get_package_share_directory('BB01_URDF')
    
    # Default URDF file path
    default_urdf_path = os.path.join(pkg_share, "urdf", "BB01_URDF.urdf")
    
    # Declare launch argument for URDF model
    model_arg = DeclareLaunchArgument(
        name="model",
        default_value=default_urdf_path,
        description="Absolute path to the robot URDF file"
    )
    
    # Generate nodes using OpaqueFunction to properly evaluate LaunchConfiguration
    nodes = OpaqueFunction(function=generate_nodes)
    
    return LaunchDescription([
        model_arg,
        nodes
    ])
