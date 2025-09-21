#!/usr/bin/env python3
import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():

    # --- Package Paths ---
    # Use the correct package name for rob
    rob_description_pkg_name = "rob_description"
    rob_description_dir = get_package_share_directory(rob_description_pkg_name)
    ros_gz_sim_pkg_share = get_package_share_directory("ros_gz_sim")

    # --- Declare Launch Arguments ---
    # Argument for the URDF/XACRO model file
    model_arg = DeclareLaunchArgument(
        name="model",
        default_value=os.path.join(rob_description_dir, "urdf", "rob.urdf.xacro"),
        description="Absolute path to robot urdf file"
    )
    # Argument for the robot name (used in XACRO and spawning)
    robot_name_arg = DeclareLaunchArgument(
        name="robot_name",
        default_value="rob",
        description="Name for the robot and urdf argument"
    )

    declare_use_camera_cmd = DeclareLaunchArgument(
        name='use_camera',
        default_value='false',
        description='Flag to enable the RGBD camera for Gazebo point cloud simulation')

    # Argument for use_gazebo (required by your XACRO)
    use_gazebo_arg = DeclareLaunchArgument(
        name="use_gazebo",
        default_value="true", # Must be 'true' for Gazebo-specific tags in URDF
        description="Flag indicating Gazebo is being used (for XACRO)"
    )

    # --- Environment Variable Setup (Using the method from the working example) ---
    # This sets GZ_SIM_RESOURCE_PATH to the parent of the package share directory
    # e.g., /path/to/ws/install/rob_description/share
    # This is less specific but might be what worked previously.
    gazebo_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=[
            str(Path(rob_description_dir).parent.resolve())
        ]
    )

    # --- XACRO Processing Arguments (Based on original example + your needs) ---
    # Check ROS distro to potentially set 'is_ignition' flag if your XACRO uses it
    # Note: Modern Gazebo Sim doesn't strictly need this 'is_ignition' concept
    ros_distro = os.environ.get("ROS_DISTRO", "jazzy") # Default to jazzy if not set
    is_ignition = "true" # Let's assume modern Gazebo Sim for simplicity, adjust if needed

    # --- Robot Description Processing ---
    # Process the XACRO file, passing all required arguments
    robot_description = ParameterValue(
        Command([
            "xacro ",
            LaunchConfiguration("model"),
            # Pass the required arguments from LaunchConfiguration
            " robot_name:=", LaunchConfiguration("robot_name"),
            " use_gazebo:=", LaunchConfiguration("use_gazebo"),
            # Keep 'is_ignition' if your xacro file still uses it, otherwise remove
            " is_ignition:=", is_ignition
        ]),
        value_type=str
    )

    # --- Nodes ---
    # Robot State Publisher (Loads description parameter, publishes TF)
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": True # Essential for Gazebo
        }]
    )

    # Gazebo Simulation (Include the standard Gazebo Sim launch file)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_pkg_share, "launch", "gz_sim.launch.py")
        ),
        # Launch with an empty world and run automatically (-r)
        # Keep physics engine logic if relevant for your Humble setup originally
        launch_arguments={
            "gz_args": " -v 4 -r empty.sdf " # Add physics_engine variable here if needed
        }.items()
    )

    # Gazebo Spawner (Creates the robot entity in Gazebo)
    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "/robot_description", # Use the description published by RSP
            "-name", LaunchConfiguration("robot_name"), # Use the configurable name
            "-allow_renaming", "true",
             # Spawning at origin for simplicity
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1', # Slightly above ground
            '-R', '0.0',
            '-P', '0.0',
            '-Y', '0.0'
        ],
         parameters=[{'use_sim_time': True}] # Pass use_sim_time
    )

    # ROS-Gazebo Bridge (Only bridging clock for this minimal test)
    # Removed camera topics from original example for simplicity
    gz_ros2_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock]"],
        parameters=[{'use_sim_time': True}] # Pass use_sim_time
    )

    # --- Assemble Launch Description ---
    return LaunchDescription([
        # Declare Arguments
        model_arg,
        robot_name_arg,
        use_gazebo_arg,

        # Set Environment Variable
        gazebo_resource_path,

        # Launch Nodes
        robot_state_publisher_node,
        gazebo,
        gz_spawn_entity,
        gz_ros2_bridge
    ])