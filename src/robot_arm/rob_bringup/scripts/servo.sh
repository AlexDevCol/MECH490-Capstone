#!/bin/bash
# Launch Gazebo + MoveIt + MoveIt Servo for any robot, then run keyboard control.
#
# Usage: ./servo.sh [robot]
#   robot: panda, rob (default: bb01), or bb01
#
# This script:
#   1. Launches Gazebo simulation in the background
#   2. Launches MoveIt move_group in the background (after delay)
#   3. Launches MoveIt Servo node in the background (after delay)
#   4. Runs keyboard_servo_node in the FOREGROUND so it captures stdin
#
# The keyboard node starts in JOINT JOG mode so you can jog the arm
# away from any singular position before switching to Twist mode (press 't').

ROBOT=${1:-bb01}

# Validate robot selection
if [[ ! "$ROBOT" =~ ^(panda|rob|bb01)$ ]]; then
    echo "Error: Invalid robot '$ROBOT'. Must be one of: panda, rob, bb01"
    exit 1
fi

cleanup() {
    echo ""
    echo "Cleaning up..."
    sleep 2.0
    pkill -9 -f "ros2|gazebo|gz|rviz2|robot_state_publisher|joint_state_publisher|moveit|move_group|servo_node|keyboard_servo_node|joy_to_servo_node|joy_node"
}

# Set up cleanup trap
trap 'cleanup' SIGINT SIGTERM

echo "============================================"
echo " MoveIt Servo Launch for: $ROBOT"
echo "============================================"

# Step 1: Launch Gazebo simulation
echo "[1/4] Launching Gazebo simulation..."
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

# Step 2: Wait for Gazebo, then launch MoveIt
sleep 15
echo "[2/4] Launching MoveIt move_group..."
ros2 launch robot_moveit_config move_group.launch.py \
    robot:=$ROBOT \
    use_rviz:=true &

# Adjust camera position in Gazebo
echo "Adjusting camera position..."
gz service -s /gui/move_to/pose \
    --reqtype gz.msgs.GUICamera \
    --reptype gz.msgs.Boolean \
    --timeout 2000 \
    --req "pose: {position: {x: 1.36, y: -0.58, z: 0.95} orientation: {x: -0.26, y: 0.1, z: 0.89, w: 0.35}}" &

# Step 3: Wait for MoveIt, then launch Servo
sleep 10
echo "[3/4] Launching MoveIt Servo node..."
ros2 launch robot_moveit_config servo.launch.py \
    robot:=$ROBOT \
    use_keyboard:=false \
    use_xbox:=false &

# Step 4: Wait for Servo, then launch keyboard control in foreground
sleep 5
echo "[4/4] Launching keyboard control (foreground)..."
echo ""
echo "============================================"
echo " Keyboard control is active!"
echo " Start with Joint Jog mode (1-6 keys)"
echo " Press 't' to switch to Twist mode"
echo " Press 'q' to quit"
echo "============================================"
echo ""

ros2 run rob_cpp_pkg keyboard_servo_node \
    --ros-args \
    -p planning_frame:=world \
    -p use_sim_time:=true \
    -p cartesian_speed_scale:=0.5 \
    -p joint_speed_scale:=0.5

# If keyboard node exits, clean up everything
cleanup
