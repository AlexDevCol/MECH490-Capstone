import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Launch Gazebo simulation
    gazebo = IncludeLaunchDescription(
        os.path.join(
            get_package_share_directory("robot_gazebo"),
            "launch",
            "simulation.launch.py"
        ),
        launch_arguments={"robot": "rob"}.items()
    )
        
    # Launch MoveIt for motion planning
    moveit = IncludeLaunchDescription(
        os.path.join(
            get_package_share_directory("robot_moveit_config"),
            "launch",
            "move_group.launch.py"
        ),
        launch_arguments={"robot": "rob"}.items()
    )
    
    # Add a delay before launching MoveIt
    moveit_with_delay = TimerAction(
        period=4.0,  # Delay in seconds
        actions=[moveit]
    )
    
    # Return the launch description with Gazebo and MoveIt (with delay)
    return LaunchDescription([
        gazebo,
        moveit_with_delay
    ])