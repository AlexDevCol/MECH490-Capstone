#!/bin/bash
# Launch real robot + MoveIt (without servo).
#
# Usage: ./real_robot.sh [robot] [port]
#   robot: bb01 (default: bb01)
#   port: Serial port for micro-ROS agent (default: /dev/ttyUSB0)
#
# This script:
#   1. Launches real robot bringup without servo
#   2. Use MoveIt planning in RViz to control the robot
#
# Control the robot using MoveIt planning interface in RViz.

# ── Parse arguments ──────────────────────────────────────────────────────────
ROBOT=""
PORT=""

for arg in "$@"; do
    if [[ "$arg" =~ ^/dev/ ]]; then
        PORT="$arg"
    elif [[ "$arg" =~ ^(bb01)$ ]]; then
        ROBOT="$arg"
    fi
done

ROBOT=${ROBOT:-bb01}
PORT=${PORT:-/dev/ttyUSB0}

# Validate robot selection
if [[ ! "$ROBOT" =~ ^(bb01)$ ]]; then
    echo "Error: Invalid robot '$ROBOT'. Must be: bb01"
    exit 1
fi

# Validate port exists
if [[ ! -e "$PORT" ]]; then
    echo "Warning: Port '$PORT' does not exist. Make sure ESP32 is connected."
    echo "Continuing anyway..."
fi

cleanup() {
    echo ""
    echo "Cleaning up..."
    sleep 2.0
    pkill -9 -f "ros2|rviz2|robot_state_publisher|moveit|move_group|micro_ros_agent|gripper_control"
}

# Set up cleanup trap
trap 'cleanup' SIGINT SIGTERM

echo "============================================"
echo " Real Robot Launch for: $ROBOT"
echo " Serial Port: $PORT"
echo " Servo: Disabled"
echo " Control: MoveIt Planning (RViz) + Gripper Control"
echo "============================================"

# Launch real robot without servo in background
echo "Launching real robot without servo..."
echo "Use MoveIt planning in RViz to control the robot."
echo "Gripper control window will appear shortly."
echo "Press Ctrl+C to stop."
echo ""

ros2 launch rob_bringup real_robot.launch.py \
    robot:=$ROBOT \
    use_rviz:=true \
    port:=$PORT \
    use_servo:=false &

# Wait for ROS to initialize, then launch gripper control window
sleep 8
echo ""
echo "Launching gripper control window..."
echo ""

# Find the script relative to this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/gripper_control.py" &

# Wait for background processes
wait
