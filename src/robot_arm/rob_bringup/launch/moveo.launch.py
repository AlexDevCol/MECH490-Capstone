import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Launch Gazebo simulation
    gazebo = IncludeLaunchDescription(
        os.path.join(
            get_package_share_directory("rob_description"),
            "launch",
            "gazebo.launch.py"
        )
    )
        
    # Launch MoveIt for motion planning
    moveit = IncludeLaunchDescription(
        os.path.join(
            get_package_share_directory("rob_moveit_config"),
            "launch",
            "demo.launch.py"
        ),
        launch_arguments={"is_sim": "True"}.items()
    )
    
    # Add a remapping to ensure /joint_states is correctly mapped
    moveit_with_remap = Node(
        package="rob_moveit_config",
        executable="move_group",
        output="screen",
        remappings=[
            ("/joint_states", "/joint_states")  # Explicitly map /joint_states to itself
        ]
    )
    
    # Add a delay before launching MoveIt
    moveit_with_delay = TimerAction(
        period=4.0,  # Delay in seconds
        actions=[moveit, moveit_with_remap]
    )
    
    # Return the launch description with Gazebo and MoveIt (with delay and remapping)
    return LaunchDescription([
        gazebo,
        moveit_with_delay
    ])