#!/bin/bash
# Single script to launch any robot with Gazebo, RViz, and MoveIt 2
# Usage: ./gazebo_and_moveit.sh [robot]
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
    use_camera:=false \
    use_rviz:=false \
    use_robot_state_pub:=true \
    use_sim_time:=true \
    x:=0.0 \
    y:=0.0 \
    z:=0.0 \
    roll:=0.0 \
    pitch:=0.0 \
    yaw:=0.0 &

sleep 15
ros2 launch ${ROBOT}_moveit_config move_group.launch.py &

echo "Adjusting camera position..."
gz service -s /gui/move_to/pose --reqtype gz.msgs.GUICamera --reptype gz.msgs.Boolean --timeout 2000 --req "pose: {position: {x: 1.36, y: -0.58, z: 0.95} orientation: {x: -0.26, y: 0.1, z: 0.89, w: 0.35}}"

# Keep the script running until Ctrl+C
wait
