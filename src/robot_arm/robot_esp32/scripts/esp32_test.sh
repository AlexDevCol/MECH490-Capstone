#!/bin/bash
# Launch script for ESP32 servo control test interface
# Starts micro-ROS agent and servo control GUI

# Default serial port (can be overridden with environment variable)
SERIAL_PORT=${ESP32_PORT:-/dev/ttyUSB0}

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go up 4 levels: scripts -> robot_esp32 -> robot_arm -> src -> workspace root
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/../../../.." && pwd )"

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    pkill -f "micro_ros_agent" 2>/dev/null
    pkill -f "servo_gui.py" 2>/dev/null
    sleep 2.0
    echo "Cleanup complete."
    exit 0
}

# Set up cleanup trap
trap 'cleanup' SIGINT SIGTERM

# Check if ROS 2 is sourced
if ! command -v ros2 &> /dev/null; then
    echo "Error: ROS 2 is not sourced. Please run:"
    echo "  source /opt/ros/humble/setup.bash"
    echo "  # Or source your workspace:"
    echo "  source $WORKSPACE_DIR/install/setup.bash"
    exit 1
fi

# Check if serial port exists (informational only, don't block)
if [ ! -e "$SERIAL_PORT" ]; then
    echo "Note: Serial port $SERIAL_PORT not found."
    echo "Available ports:"
    ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  (none found)"
    echo ""
    echo "The micro-ROS agent will attempt to connect when the port becomes available."
    echo "You can set a different port with: export ESP32_PORT=/dev/ttyUSB0"
    echo ""
fi

# Check if micro-ROS agent is available
if ! ros2 pkg list | grep -q "micro_ros_agent"; then
    echo "Error: micro-ROS agent package not found."
    echo "Please install it with:"
    echo "  sudo apt install ros-humble-micro-ros-agent"
    exit 1
fi

echo "=========================================="
echo "ESP32 Servo Control Test Interface"
echo "=========================================="
echo "Serial Port: $SERIAL_PORT"
echo ""

# Step 1: Start micro-ROS agent
echo "Starting micro-ROS agent..."
ros2 run micro_ros_agent micro_ros_agent serial --dev "$SERIAL_PORT" &
AGENT_PID=$!

# Wait for agent to initialize
echo "Waiting for agent to initialize..."
sleep 3

# Check if agent is still running
if ! kill -0 $AGENT_PID 2>/dev/null; then
    echo "Error: micro-ROS agent failed to start."
    echo "Check the port and permissions:"
    echo "  ls -l $SERIAL_PORT"
    echo "  sudo chmod 666 $SERIAL_PORT  # if needed"
    exit 1
fi

echo "micro-ROS agent started (PID: $AGENT_PID)"
echo ""

# Step 2: Wait a bit more for ESP32 connection
echo "Waiting for ESP32 connection..."
echo "Please ensure ESP32 is connected and powered on."
sleep 2

# Step 3: Launch GUI
echo "Launching servo control GUI..."
echo ""

# Change to workspace directory to ensure proper ROS 2 context
cd "$WORKSPACE_DIR"

# Source workspace if install directory exists
if [ -f "$WORKSPACE_DIR/install/setup.bash" ]; then
    source "$WORKSPACE_DIR/install/setup.bash"
fi

# Launch GUI
python3 "$SCRIPT_DIR/servo_gui.py" &
GUI_PID=$!

echo "GUI started (PID: $GUI_PID)"
echo ""
echo "=========================================="
echo "Test interface is running!"
echo "=========================================="
echo "Press Ctrl+C to stop both agent and GUI"
echo ""

# Wait for processes
wait $GUI_PID
GUI_EXIT_CODE=$?

# Cleanup
cleanup
