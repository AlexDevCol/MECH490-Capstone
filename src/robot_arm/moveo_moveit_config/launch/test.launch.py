#!/usr/bin/env python3
"""
Launch MoveIt 2 for the myCobot robotic arm. (FIXED VERSION - Corrected Import)

:author: Addison Sears-Collins
:date: December 13, 2024 / Modified April 6, 2025
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler, OpaqueFunction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
# Correct Core Launch Imports:
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.actions import Node
# Correct ROS Launch Imports:
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    """
    Generate a launch description for MoveIt 2 with myCobot robot. (FIXED VERSION - Corrected Import)
    Manually generates robot_description to avoid builder issue.
    """
    # Constants for paths
    package_name_moveit_config = 'moveo_moveit_config'
    description_package_name = 'moveo_description' # *** ADJUST IF NEEDED ***
    urdf_relative_path = 'urdf/moveo.urdf.xacro' # *** ADJUST IF NEEDED ***

    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config_file = LaunchConfiguration('rviz_config_file')
    rviz_config_package = LaunchConfiguration('rviz_config_package')
    robot_name_config = LaunchConfiguration('robot_name') # Use LaunchConfiguration object

    # Get the package share directory objects
    pkg_share_moveit_config = FindPackageShare(package=package_name_moveit_config)
    pkg_share_description = FindPackageShare(package=description_package_name)


    # Declare the launch arguments
    declare_robot_name_cmd = DeclareLaunchArgument(
        name='robot_name',
        default_value='moveo',
        description='Name of the robot to use')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true', # Keep true as move_group needs sim time from Gazebo
        description='Use simulation (Gazebo) clock if true')

    declare_use_rviz_cmd = DeclareLaunchArgument(
        name='use_rviz',
        default_value='true',
        description='Whether to start RViz')

    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        name='rviz_config_file',
        default_value='move_group.rviz',
        description='RViz configuration file')

    declare_rviz_config_package_cmd = DeclareLaunchArgument(
        name='rviz_config_package',
        default_value=package_name_moveit_config,
        description='Package containing the RViz configuration file')


    # --- MANUALLY GENERATE ROBOT DESCRIPTION ---
    # Prepare the xacro command, passing ALL required arguments
    robot_description_content = ParameterValue(
        Command([
            'xacro ',
            PathJoinSubstitution([pkg_share_description, urdf_relative_path]),
            # *** PASS ALL NEEDED XACRO ARGS HERE ***
            f' robot_name:={robot_name_config}',
            ' use_gazebo:=true',  # Essential for ros2_control plugin loading
            ' add_world:=false', # Set appropriately for MoveIt context (usually false)
        ]),
        value_type=str
    )
    # Prepare parameter dictionary for nodes
    robot_description_param = {'robot_description': robot_description_content}
    # --- END MANUAL GENERATION ---


    def configure_moveit(context):
        """Configure MoveIt and create nodes with proper string conversions."""
        # Get the robot name as a string
        robot_name_str = robot_name_config.perform(context)

        # Get package path string
        pkg_share_moveit_config_str = pkg_share_moveit_config.perform(context)

        # Construct file paths using robot name string
        config_path = os.path.join(pkg_share_moveit_config_str, 'config')

        # Define all config file paths
        initial_positions_file_path = os.path.join(config_path, 'initial_positions.yaml')
        joint_limits_file_path = os.path.join(config_path, 'joint_limits.yaml')
        kinematics_file_path = os.path.join(config_path, 'kinematics.yaml')
        moveit_controllers_file_path = os.path.join(config_path, 'moveit_controllers.yaml')
        srdf_model_path = os.path.join(config_path, f'{robot_name_str}.srdf')
        pilz_cartesian_limits_file_path = os.path.join(config_path, 'pilz_cartesian_limits.yaml')

        # Create MoveIt configuration using the builder
        # We load everything *except* the main robot_description from the builder
        moveit_config_builder = MoveItConfigsBuilder(robot_name_str, package_name=package_name_moveit_config)
        moveit_config_builder.trajectory_execution(file_path=moveit_controllers_file_path)
        moveit_config_builder.robot_description_semantic(file_path=srdf_model_path) # Keep semantic
        moveit_config_builder.joint_limits(file_path=joint_limits_file_path)
        moveit_config_builder.robot_description_kinematics(file_path=kinematics_file_path)
        moveit_config_builder.planning_pipelines(
            pipelines=["ompl", "pilz_industrial_motion_planner", "stomp"],
            default_planning_pipeline="ompl"
        )
        moveit_config_builder.planning_scene_monitor(
            publish_robot_description=False, # Let move_group/RViz use our manual param
            publish_robot_description_semantic=True,
            publish_planning_scene=True,
        )
        moveit_config_builder.pilz_cartesian_limits(file_path=pilz_cartesian_limits_file_path)

        # Finalize the builder to get parameters *other than* robot_description
        moveit_configs = moveit_config_builder.to_moveit_configs()


        # MoveIt capabilities
        move_group_capabilities = {"capabilities": "move_group/ExecuteTaskSolutionCapability"}

        # Create move_group node
        start_move_group_node_cmd = Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[
                moveit_configs.to_dict(), # Get params from builder
                robot_description_param, # Add our manually generated robot_description
                {'use_sim_time': use_sim_time},
                # Use the initial positions file parameter name from your original file
                {'initial_positions_file': initial_positions_file_path}, # Or {'start_state': ...}
                move_group_capabilities,
            ],
        )

        # Construct RViz path using substitutions
        rviz_path = PathJoinSubstitution([
            FindPackageShare(rviz_config_package), # Use substitution directly here
            "rviz", # Assuming config is in 'rviz' subfolder
            rviz_config_file
        ])

        # Create RViz node
        start_rviz_node_cmd = Node(
            condition=IfCondition(use_rviz),
            package="rviz2",
            executable="rviz2",
            name="rviz2_moveit",
            arguments=["-d", rviz_path],
            output="screen",
            parameters=[
                moveit_configs.robot_description_semantic,
                moveit_configs.planning_pipelines,
                moveit_configs.robot_description_kinematics,
                moveit_configs.joint_limits,
                robot_description_param, # Add our manually generated robot_description
                {'use_sim_time': use_sim_time}
            ],
        )

        # RViz exit handler
        exit_event_handler = RegisterEventHandler(
            condition=IfCondition(use_rviz),
            event_handler=OnProcessExit(
                target_action=start_rviz_node_cmd,
                on_exit=EmitEvent(event=Shutdown(reason='rviz exited')),
            ),
        )

        # Return the list of nodes and handlers
        return [start_move_group_node_cmd, start_rviz_node_cmd, exit_event_handler]

    # Create the launch description
    ld = LaunchDescription()

    # Add the launch arguments
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_rviz_config_package_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_use_rviz_cmd)

    # Add the OpaqueFunction that will generate the nodes
    ld.add_action(OpaqueFunction(function=configure_moveit))

    return ld