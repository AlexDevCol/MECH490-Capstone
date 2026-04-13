#!/usr/bin/env python3
"""
Launch RViz display for any robot in the robot_description package.

This is a simpler launch file for quick visualization and testing.
It loads the robot model, joint state publisher GUI, and RViz2.

The robot is selected via the 'robot' argument:
    robot:=panda  # Load panda robot
    robot:=rob    # Load rob robot
    robot:=bb01   # Load bb01 robot

:author: MECH490-Capstone Team
:date: January 20, 2026
"""
import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from ament_index_python.packages import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import Command, LaunchConfiguration


def generate_launch_description():
    """Generate the launch description for robot display.

    This function sets up the nodes for visualizing any robot in RViz:
    - Robot state publisher for broadcasting transforms
    - Joint state publisher GUI for manual joint control
    - RViz2 for visualization

    Returns:
        LaunchDescription: Complete launch description for the display setup
    """
    # Define robot selection argument
    robot_arg = DeclareLaunchArgument(
        name='robot',
        default_value='rob',
        choices=['panda', 'rob', 'bb01'],
        description='Robot to load (panda, rob, or bb01)'
    )

    def configure_display(context):
        """Configure display nodes based on robot selection."""
        robot_val = LaunchConfiguration('robot').perform(context)
        
        # Get package share directory
        pkg_share = get_package_share_directory('robot_description')
        
        # Build URDF path: robots/<robot>/urdf/<robot>.urdf.xacro
        urdf_file = os.path.join(
            pkg_share,
            'robots',
            robot_val,
            'urdf',
            f'{robot_val}.urdf.xacro'
        )
        
        # Build RViz config path based on robot
        rviz_config_file = os.path.join(
            pkg_share,
            'rviz',
            f'display_{robot_val}.rviz'
        )
        
        # Declare model argument with computed default
        model_arg = DeclareLaunchArgument(
            name='model',
            default_value=urdf_file,
            description='Absolute path to the robot URDF file'
        )
        
        # Build robot description from xacro
        robot_description = ParameterValue(
            Command(['xacro ', LaunchConfiguration('model')]),
            value_type=str
        )
        
        # Robot state publisher node
        robot_state_publisher = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}]
        )
        
        # Joint state publisher GUI node
        joint_state_publisher_gui = Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui'
        )
        
        # RViz2 node
        rviz2_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file]
        )
        
        return [
            model_arg,
            robot_state_publisher,
            joint_state_publisher_gui,
            rviz2_node
        ]

    # Create the launch description
    ld = LaunchDescription()
    
    # Add robot selection argument
    ld.add_action(robot_arg)
    
    # Configure and add nodes based on robot selection
    ld.add_action(OpaqueFunction(function=configure_display))
    
    return ld
