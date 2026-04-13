#!/bin/bash
# Single script to launch any robot with Gazebo and ROS 2 Controllers
# Usage: ./gazebo.sh [robot]
#   robot: panda, rob (default), or bb01

ROBOT=${1:-rob}

# Validate robot selection
if [[ ! "$ROBOT" =~ ^(panda|rob|bb01)$ ]]; then
    echo "Error: Invalid robot '$ROBOT'. Must be one of: panda, rob, bb01"
    exit 1
fi

cleanup() {
    echo "Cleaning up..."
    sleep 5.0
    pkill -9 -f "ros2|gazebo|gz|nav2|amcl|bt_navigator|nav_to_pose|rviz2|assisted_teleop|cmd_vel_relay|robot_state_publisher|joint_state_publisher|move_to_free|mqtt|autodock|cliff_detection|moveit|move_group|basic_navigator"
}

# Set up cleanup trap
trap 'cleanup' SIGINT SIGTERM

echo "Launching Gazebo simulation for robot: $ROBOT"
ros2 launch robot_gazebo simulation.launch.py \
    robot:=$ROBOT \
    load_controllers:=true \
    world_file:=empty.world \
    use_camera:=true \
    use_rviz:=true \
    use_robot_state_pub:=true \
    use_sim_time:=true \
    x:=0.0 \
    y:=0.0 \
    z:=0.0 \
    roll:=0.0 \
    pitch:=0.0 \
    yaw:=0.0
