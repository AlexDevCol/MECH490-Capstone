#!/usr/bin/env python3
"""
Launch Gazebo simulation with any robot.

This launch file sets up a complete ROS 2 simulation environment with Gazebo for
any robot in the robot_description package. The robot is selected via the 'robot' argument:
    robot:=panda  # Load panda robot
    robot:=rob    # Load rob robot
    robot:=bb01   # Load bb01 robot

:author: MECH490-Capstone Team
:date: January 20, 2026
"""

import os
from launch import LaunchDescription
from launch.actions import (
    SetEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    ExecuteProcess,
    TimerAction
)
from pathlib import Path

from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


# Robot configuration dictionary
ROBOT_CONFIGS = {
    'panda': {
        'description_package': 'robot_description',
        'moveit_package': 'panda_moveit_config',
        'default_z': '0.1',
    },
    'rob': {
        'description_package': 'robot_description',
        'moveit_package': 'rob_moveit_config',
        'default_z': '0.1',
    },
    'bb01': {
        'description_package': 'robot_description',
        'moveit_package': 'bb01_moveit_config',
        'default_z': '0.0',  # Spawn on ground level
    },
}


def generate_launch_description():
    """
    Generate a launch description for the Gazebo simulation.

    This function sets up all necessary parameters, paths, and nodes required to launch
    the Gazebo simulation with any robot. It handles:
    1. Setting up package paths and constants
    2. Declaring launch arguments for robot configuration
    3. Setting up the Gazebo environment
    4. Spawning the robot in simulation

    Returns:
        LaunchDescription: A complete launch description for the simulation
    """
    # Declare robot argument
    robot_arg = DeclareLaunchArgument(
        'robot',
        default_value='rob',
        choices=['panda', 'rob', 'bb01'],
        description='Robot to simulate (panda, rob, or bb01)'
    )

    # Declare all other launch arguments (these don't depend on robot selection)
    declare_jsp_gui_cmd = DeclareLaunchArgument(
        name='jsp_gui',
        default_value='false',
        description='Flag to enable joint_state_publisher_gui'
    )

    declare_load_controllers_cmd = DeclareLaunchArgument(
        name='load_controllers',
        default_value='true',
        description='Flag to enable loading of ROS 2 controllers'
    )

    declare_use_robot_state_pub_cmd = DeclareLaunchArgument(
        name='use_robot_state_pub',
        default_value='true',
        description='Flag to enable robot state publisher'
    )

    declare_use_camera_cmd = DeclareLaunchArgument(
        name='use_camera',
        default_value='false',
        description='Flag to enable the RGBD camera for Gazebo point cloud simulation'
    )

    declare_use_gazebo_cmd = DeclareLaunchArgument(
        name='use_gazebo',
        default_value='true',
        description='Flag to enable Gazebo'
    )

    declare_use_rviz_cmd = DeclareLaunchArgument(
        name='use_rviz',
        default_value='true',
        description='Flag to enable RViz'
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_world_cmd = DeclareLaunchArgument(
        name='world_file',
        default_value='empty.world',
        description='World file name (e.g., empty.world, house.world, pick_and_place_demo.world)'
    )

    # Pose arguments
    declare_x_cmd = DeclareLaunchArgument(
        name='x',
        default_value='0.0',
        description='x component of initial position, meters'
    )

    declare_y_cmd = DeclareLaunchArgument(
        name='y',
        default_value='0.0',
        description='y component of initial position, meters'
    )

    declare_z_cmd = DeclareLaunchArgument(
        name='z',
        default_value='0.1',
        description='z component of initial position, meters'
    )

    declare_roll_cmd = DeclareLaunchArgument(
        name='roll',
        default_value='0.0',
        description='roll angle of initial orientation, radians'
    )

    declare_pitch_cmd = DeclareLaunchArgument(
        name='pitch',
        default_value='0.0',
        description='pitch angle of initial orientation, radians'
    )

    declare_yaw_cmd = DeclareLaunchArgument(
        name='yaw',
        default_value='0.0',
        description='yaw angle of initial orientation, radians'
    )

    # Create the launch description with all static arguments
    ld = LaunchDescription()

    # Add all launch arguments
    ld.add_action(robot_arg)
    ld.add_action(declare_jsp_gui_cmd)
    ld.add_action(declare_load_controllers_cmd)
    ld.add_action(declare_use_camera_cmd)
    ld.add_action(declare_use_gazebo_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_use_robot_state_pub_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_x_cmd)
    ld.add_action(declare_y_cmd)
    ld.add_action(declare_z_cmd)
    ld.add_action(declare_roll_cmd)
    ld.add_action(declare_pitch_cmd)
    ld.add_action(declare_yaw_cmd)

    # Use OpaqueFunction to configure launch based on robot selection
    ld.add_action(OpaqueFunction(function=configure_launch))

    return ld


def configure_launch(context):
    """
    Configure launch description based on robot selection.

    This function is called at runtime to resolve robot-specific configurations
    and build the appropriate launch actions.

    Args:
        context: Launch context containing configuration values

    Returns:
        list: List of launch actions to add to the launch description
    """
    # Get robot selection
    robot = LaunchConfiguration('robot').perform(context)
    
    # Validate robot selection
    if robot not in ROBOT_CONFIGS:
        raise ValueError(f"Unknown robot: {robot}. Must be one of {list(ROBOT_CONFIGS.keys())}")
    
    # Get robot configuration
    config = ROBOT_CONFIGS[robot]
    
    # Constants for paths to different files and folders
    package_name_gazebo = 'rob_gazebo'
    package_name_description = config['description_package']
    package_name_moveit = config['moveit_package']
    
    default_robot_name = robot
    gazebo_models_path = 'models'
    gazebo_worlds_path = 'worlds'
    ros_gz_bridge_config_file_path = 'config/ros_gz_bridge.yaml'

    # Set the path to different files and folders
    pkg_ros_gz_sim = FindPackageShare(package='ros_gz_sim').find('ros_gz_sim')
    pkg_share_gazebo = FindPackageShare(package=package_name_gazebo).find(package_name_gazebo)
    pkg_share_description = get_package_share_directory(package_name_description)
    
    # Only get MoveIt package share if MoveIt config exists
    pkg_share_moveit = None
    if package_name_moveit:
        pkg_share_moveit = get_package_share_directory(package_name_moveit)

    default_ros_gz_bridge_config_file_path = os.path.join(
        pkg_share_gazebo, ros_gz_bridge_config_file_path)

    # Launch configuration variables
    jsp_gui = LaunchConfiguration('jsp_gui')
    load_controllers = LaunchConfiguration('load_controllers')
    robot_name = LaunchConfiguration('robot_name')
    use_rviz = LaunchConfiguration('use_rviz')
    use_camera = LaunchConfiguration('use_camera')
    use_gazebo = LaunchConfiguration('use_gazebo')
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_sim_time = LaunchConfiguration('use_sim_time')
    world_file = LaunchConfiguration('world_file')

    world_path = PathJoinSubstitution([
        pkg_share_gazebo,
        gazebo_worlds_path,
        world_file
    ])

    # Set the pose configuration variables
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    z = LaunchConfiguration('z')
    roll = LaunchConfiguration('roll')
    pitch = LaunchConfiguration('pitch')
    yaw = LaunchConfiguration('yaw')

    # Declare robot_name argument (defaults to robot value)
    declare_robot_name_cmd = DeclareLaunchArgument(
        name='robot_name',
        default_value=default_robot_name,
        description='The name for the robot'
    )

    # Include Robot State Publisher launch file if enabled
    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share_description, 'launch', 'robot_state_publisher.launch.py')
        ]),
        launch_arguments={
            'robot': robot,  # Pass robot selection to robot_description
            'jsp_gui': jsp_gui,
            'use_camera': use_camera,
            'use_gazebo': use_gazebo,
            'use_rviz': use_rviz,
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(use_robot_state_pub)
    )

    # Include ROS 2 Controllers launch file if enabled and MoveIt config exists
    load_controllers_cmd = None
    if package_name_moveit and pkg_share_moveit:
        load_controllers_cmd = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(pkg_share_moveit, 'launch', 'load_ros2_controllers.launch.py')
            ]),
            launch_arguments={
                'use_sim_time': use_sim_time
            }.items(),
            condition=IfCondition(load_controllers)
        )

    # Set Gazebo model path
    set_description_share_path = SetEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        value=[str(Path(pkg_share_description).parent.resolve())]
    )

    # Start Gazebo
    start_gazebo_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments=[('gz_args', [' -r -v 4 ', world_path])]
    )

    # Bridge ROS topics and Gazebo messages for establishing communication
    start_gazebo_ros_bridge_cmd = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={default_ros_gz_bridge_config_file_path}'
        ]
    )

    # Includes optimizations to minimize latency and bandwidth when streaming image data
    start_gazebo_ros_image_bridge_cmd = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=[
            '/camera_head/depth_image',
            '/camera_head/image',
        ],
        remappings=[
            ('/camera_head/depth_image', '/camera_head/depth/image_rect_raw'),
            ('/camera_head/image', '/camera_head/color/image_raw'),
        ],
    )

    # Spawn the robot
    start_gazebo_ros_spawner_cmd = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', '/robot_description',
            '-name', robot_name,
            '-allow_renaming', 'true',
            '-x', x,
            '-y', y,
            '-z', z,
            '-R', roll,
            '-P', pitch,
            '-Y', yaw
        ]
    )

    # Build list of actions to return
    actions = [
        declare_robot_name_cmd,
        set_description_share_path,
        robot_state_publisher_cmd,
        start_gazebo_cmd,
        start_gazebo_ros_bridge_cmd,
        start_gazebo_ros_spawner_cmd,
        start_gazebo_ros_image_bridge_cmd,
    ]

    # Add controller loading (either from MoveIt config or fallback for robots without MoveIt)
    if load_controllers_cmd is not None:
        actions.insert(3, load_controllers_cmd)  # Insert after robot_state_publisher_cmd

    return actions
