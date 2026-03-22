#!/bin/bash
# Simple test script to launch micro-ROS agent and test GUI interface
#
# Usage: ./test_run.sh [port]
#   port: Serial port for micro-ROS agent (default: /dev/ttyUSB0)
#
# This script:
#   1. Launches micro-ROS agent in the background
#   2. Waits for agent initialization
#   3. Launches test_gui.py Python GUI
#   4. Handles cleanup on exit (Ctrl+C)

# ── Parse arguments ──────────────────────────────────────────────────────────
# Default port if no argument provided
if [ -z "$1" ]; then
    PORT="/dev/ttyUSB0"
else
    PORT="$1"
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Validate port exists
if [[ ! -e "$PORT" ]]; then
    echo "Warning: Port '$PORT' does not exist. Make sure ESP32 is connected."
    echo "Continuing anyway..."
fi

cleanup() {
    echo ""
    echo "Cleaning up..."
    sleep 1.0
    pkill -9 -f "micro_ros_agent|test_gui"
}

# Set up cleanup trap
trap 'cleanup' SIGINT SIGTERM

echo "============================================"
echo " Test Run Script"
echo " Serial Port: $PORT"
echo "============================================"

# Step 1: Launch micro-ROS agent
echo "[1/2] Launching micro-ROS agent..."
ros2 run micro_ros_agent micro_ros_agent serial --dev "$PORT" --baudrate 115200 &
AGENT_PID=$!

# Wait for agent to initialize
echo "[2/2] Waiting for agent to initialize..."
sleep 3

# Check if agent is still running
if ! kill -0 $AGENT_PID 2>/dev/null; then
    echo "Error: micro-ROS agent failed to start."
    echo "Check the port and permissions:"
    echo "  ls -l $PORT"
    echo "  sudo chmod 666 $PORT  # if needed"
    exit 1
fi

echo "micro-ROS agent started (PID: $AGENT_PID)"
echo ""

# Step 2: Launch GUI
echo "============================================"
echo " GUI is launching."
echo " Use the interface to send joint commands"
echo " and control the gripper."
echo " Close the window or press Ctrl+C to quit."
echo "============================================"
echo ""

# Change to workspace directory to ensure proper ROS 2 context
cd "$SCRIPT_DIR"

# Source workspace if install directory exists
if [ -f "$SCRIPT_DIR/install/setup.bash" ]; then
    source "$SCRIPT_DIR/install/setup.bash"
fi

# Launch GUI
python3 "$SCRIPT_DIR/scripts/test_gui.py"

# If GUI exits, clean up everything
cleanup
