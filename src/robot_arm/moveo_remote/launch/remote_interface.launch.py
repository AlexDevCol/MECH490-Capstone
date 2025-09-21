import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from moveit_configs_utils import MoveItConfigsBuilder
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    is_sim_arg = DeclareLaunchArgument(
        "is_sim",
        default_value='True',
        description='Set to true for simulation mode'
    )

    is_sim = LaunchConfiguration("is_sim")
    
    # This is only used for the python API action server 
    '''
    moveit_config = (
        MoveItConfigsBuilder("moveo", package_name='moveo_moveit_config')
        .robot_description(file_path=os.path.join(
            get_package_share_directory('har_v_description'),
            'urdf_moveo', 
            'moveo.urdf.xacro'
            )
        )
        .robot_description_semantic(file_path=os.path.join(
            get_package_share_directory('moveo_moveit_config'),
            'config', 'moveo.srdf'
            )
        )
        .trajectory_execution(file_path=os.path.join(
            get_package_share_directory('moveo_moveit_config'),
            'config', 'moveit_controllers.yaml'
            )
        )
        .moveit_cpp(file_path=os.path.join(
            get_package_share_directory('moveo_moveit_config'),
            'config', 'planning_python_api.yaml'
            )
        )
        .to_moveit_configs()
    )

    '''

    task_server_node = Node(
        package='moveo_remote',
        executable='task_server_node',
        parameters=[{'use_sim_time': is_sim}]  # Ensure use_sim_time is passed
    )

    return LaunchDescription([
        is_sim_arg,
        task_server_node
    ])