#!/bin/bash
# Launch real robot + MoveIt + MoveIt Servo, then run tkinter GUI control interface.
#
# Usage: ./real_robot_servo.sh [robot] [port] [--no-servo]
#   robot: bb01 (default: bb01)
#   port: Serial port for micro-ROS agent (default: /dev/ttyUSB0)
#   --no-servo: Launch without servo (GUI will not launch)
#
# This script:
#   1. Launches real robot bringup with or without servo in the background
#   2. If servo enabled: Waits for servo to be ready, then runs servo_gui.py
#   3. If servo disabled: Just launches robot bringup (no GUI)
#
# The GUI provides clickable buttons for joint jog, Cartesian twist,
# mode switching, speed control, and pause/resume functionality.

# ── Parse arguments ──────────────────────────────────────────────────────────
ROBOT=""
PORT=""
USE_SERVO=true

for arg in "$@"; do
    if [[ "$arg" == "--no-servo" ]]; then
        USE_SERVO=false
    elif [[ "$arg" =~ ^/dev/ ]]; then
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
    pkill -9 -f "ros2|rviz2|robot_state_publisher|moveit|move_group|servo_node|servo_gui|micro_ros_agent"
}

# Set up cleanup trap
trap 'cleanup' SIGINT SIGTERM

echo "============================================"
echo " Real Robot Launch for: $ROBOT"
echo " Serial Port: $PORT"
if $USE_SERVO; then
    echo " Servo: Enabled"
    echo " Control: Tkinter GUI"
else
    echo " Servo: Disabled"
    echo " Control: MoveIt Planning (RViz)"
fi
echo "============================================"

if $USE_SERVO; then
    # Step 1: Launch real robot with servo
    echo "[1/2] Launching real robot with servo..."
    ros2 launch rob_bringup real_robot_with_servo.launch.py \
        robot:=$ROBOT \
        use_rviz:=true \
        port:=$PORT \
        use_servo:=true &

    # Step 2: Wait for servo to be ready, then launch GUI
    echo "[2/2] Waiting for servo to be ready..."
    sleep 10

    echo ""
    echo "============================================"
    echo " GUI is launching."
    echo " Use buttons to jog, switch modes, and"
    echo " pause/resume servo (to use MoveIt planning)."
    echo " Close the window to quit."
    echo "============================================"
    echo ""

    # Find the script relative to this script's location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    python3 "$SCRIPT_DIR/servo_gui.py" \
        --ros-args \
        -p planning_frame:=world \
        -p use_sim_time:=false \
        -p speed:=0.5

    # If GUI exits, clean up everything
    cleanup
else
    # Launch real robot without servo
    echo "Launching real robot without servo..."
    echo "Use MoveIt planning in RViz to control the robot."
    echo "Press Ctrl+C to stop."
    echo ""
    
    ros2 launch rob_bringup real_robot.launch.py \
        robot:=$ROBOT \
        use_rviz:=true \
        port:=$PORT \
        use_servo:=false
fi
