# Usage Guide

This guide explains how to connect the ESP32 to ROS 2, launch the micro-ROS agent, and control motors (servo and stepper) manually.

## Connection Workflow

The connection process requires a specific order: **launch the micro-ROS agent BEFORE connecting the ESP32**. This order is critical for reliable connections.

### Step 1: Pre-connection Setup

#### Identify Serial Port

First, identify which serial port your ESP32 is connected to:

**Linux**:
```bash
# List all serial devices
ls /dev/tty*

# Common ESP32 ports:
# /dev/ttyUSB0  (USB-to-Serial adapters like CH340, CP2102)
# /dev/ttyACM0  (Some ESP32 boards)
# /dev/ttyUSB1  (If multiple USB devices)

# Check recent USB connections
dmesg | grep tty
```

**macOS**:
```bash
ls /dev/cu.*
# Common: /dev/cu.usbserial-* or /dev/cu.SLAB_USBtoUART
```

**Windows**:
- Check Device Manager → Ports (COM & LPT)
- Common: COM3, COM4, etc.

#### Set Port Permissions (Linux)

If you get permission errors:

```bash
# Option 1: Add user to dialout group (permanent)
sudo usermod -a -G dialout $USER
# Log out and log back in

# Option 2: Set permissions temporarily
sudo chmod 666 /dev/ttyUSB0
```

### Step 2: Launch micro-ROS Agent First (Critical)

**Important**: Launch the agent **BEFORE** connecting or powering on the ESP32. This ensures the agent is ready to accept connections.

1. **Open a terminal**

2. **Source ROS 2** (if not already sourced):
   ```bash
   source /opt/ros/humble/setup.bash
   # Or if using a workspace:
   source ~/microros_ws/install/setup.bash
   ```

3. **Launch the agent**:
   ```bash
   ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0
   ```
   
   Replace `/dev/ttyUSB0` with your actual port (e.g., `/dev/ttyACM0`, `/dev/cu.usbserial-*`).

4. **Expected output**:
   ```
   [INFO] [micro_ros_agent]: Waiting for the agent to be ready...
   [INFO] [micro_ros_agent]: Agent started
   [INFO] [micro_ros_agent]: Waiting for entities...
   ```

5. **Keep this terminal open** - the agent must remain running.

### Step 3: Connect ESP32

1. **Connect ESP32 via USB** (if not already connected)

2. **Power on ESP32** (if it has a power switch)

3. **Watch the agent terminal** - you should see connection messages:
   ```
   [INFO] [micro_ros_agent]: New entity connected
   [INFO] [micro_ros_agent]: Node /esp32_servo_node created
   ```
   Or for stepper:
   ```
   [INFO] [micro_ros_agent]: New entity connected
   [INFO] [micro_ros_agent]: Node /esp32_stepper_node created
   ```

4. **If connection fails**:
   - Check that the agent is running
   - Verify the port is correct
   - Try resetting the ESP32 (press RESET button)
   - Check Serial Monitor in Arduino IDE for error messages

### Step 4: Verify Connection

Open a **new terminal** and verify the connection:

1. **Source ROS 2**:
   ```bash
   source /opt/ros/humble/setup.bash
   ```

2. **List ROS 2 nodes**:
   ```bash
   ros2 node list
   ```
   
   **Expected output** (servo):
   ```
   /esp32_servo_node
   ```
   Or (stepper):
   ```
   /esp32_stepper_node
   ```

3. **List topics**:
   ```bash
   ros2 topic list
   ```
   
   **Expected output** (servo):
   ```
   /parameter_events
   /rosout
   /servo_angle
   ```
   Or (stepper):
   ```
   /parameter_events
   /rosout
   /stepper_angle
   ```

4. **Check topic info**:
   ```bash
   ros2 topic info /servo_angle  # For servo
   # or
   ros2 topic info /stepper_angle  # For stepper
   ```
   
   **Expected output**:
   ```
   Type: std_msgs/msg/Int32
   Publisher count: 0
   Subscription count: 1
   ```

   Note: Publisher count is 0 because nothing is publishing yet. Subscription count is 1 (the ESP32).

## Manual Motor Control

### Servo Motor Control

Once connected, you can control the servo by publishing messages to the `/servo_angle` topic.

### Single Command (Recommended)

Publish a single angle command:

```bash
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 40'
```

**Explanation**:
- `--once`: Publish once and exit
- `/servo_angle`: Topic name
- `std_msgs/msg/Int32`: Message type
- `'data: 40'`: Message data (angle in degrees, 0-180)

**Expected behavior**:
- Servo moves to 40 degrees
- LED on ESP32 flashes briefly
- Serial Monitor shows: `Received Angle: 40 -> Setting Servo to: 40`

### Stepper Motor Control

Once connected, you can control the stepper motor by publishing messages to the `/stepper_angle` topic.

#### Single Command (Recommended)

Publish a single angle command:

```bash
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 45'
```

**Explanation**:
- `--once`: Publish once and exit
- `/stepper_angle`: Topic name
- `std_msgs/msg/Int32`: Message type
- `'data: 45'`: Message data (angle in degrees, absolute position)

**Expected behavior**:
- Stepper moves to 45 degrees (from current position)
- LED on ESP32 turns on during movement, turns off when complete
- Position is remembered (absolute positioning)

#### Multiple Commands in Sequence

Test different angles:

```bash
# Move to 0 degrees
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 0'

# Wait a moment, then move to 45 degrees
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 45'

# Move to 90 degrees
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 90'

# Return to 0 degrees
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 0'
```

**Note**: The stepper remembers its position, so each command moves relative to the current position.

#### Continuous Publishing

Publish continuously (useful for testing):

```bash
ros2 topic pub /stepper_angle std_msgs/msg/Int32 'data: 90'
```

This publishes the same value repeatedly. Press `Ctrl+C` to stop.

**Note**: Continuous publishing sends messages at a high rate. For manual control, use `--once` instead.

### Multiple Commands in Sequence

Test different angles:

```bash
# Move to 0 degrees (minimum)
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 0'

# Wait a moment, then move to center
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 90'

# Move to maximum
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 180'

# Return to center
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 90'
```

### Continuous Publishing

Publish continuously (useful for testing):

```bash
ros2 topic pub /servo_angle std_msgs/msg/Int32 'data: 90'
```

This publishes the same value repeatedly. Press `Ctrl+C` to stop.

**Note**: Continuous publishing sends messages at a high rate. For manual control, use `--once` instead.

### Sweep Pattern Example

Create a simple sweep script:

```bash
#!/bin/bash
# Save as servo_sweep.sh

for angle in 0 45 90 135 180 135 90 45 0; do
    ros2 topic pub --once /servo_angle std_msgs/msg/Int32 "data: $angle"
    sleep 1
done
```

Make it executable and run:
```bash
chmod +x servo_sweep.sh
./servo_sweep.sh
```

## Test Interface GUI

For easier testing and control, a tkinter-based GUI is available that launches both the micro-ROS agent and provides a graphical interface for servo control.

### Launching the Test Interface

From the workspace root:

```bash
cd ~/Capstone/MECH490-Capstone

# Make script executable (first time only)
chmod +x src/robot_arm/robot_esp32/scripts/esp32_test.sh

# Run the test interface
./src/robot_arm/robot_esp32/scripts/esp32_test.sh
```

The script will:
1. Check for ROS 2 environment
2. Verify serial port availability
3. Start the micro-ROS agent on `/dev/ttyUSB0` (or specified port)
4. Wait for initialization
5. Launch the GUI interface

### Using the GUI

The GUI provides:

- **Angle Slider**: Drag to select angle (0-180 degrees)
- **Current Angle Display**: Shows the selected angle in real-time
- **Preset Buttons**: Quick access to common angles (0°, 45°, 90°, 135°, 180°)
- **Send Button**: Publishes the selected angle to the servo
- **Status Indicator**: Shows connection status

**Usage**:
1. Ensure ESP32 is connected and powered on before launching
2. Use the slider or preset buttons to select an angle
3. Click "Send Angle" to move the servo
4. Watch the servo move and check the status indicator

### Customizing Serial Port

To use a different serial port:

```bash
export ESP32_PORT=/dev/ttyACM0
./src/robot_arm/robot_esp32/scripts/esp32_test.sh
```

Or edit the script to change the default port.

### GUI Features

- **Real-time angle selection**: See the angle value as you adjust the slider
- **Visual feedback**: Status updates when commands are sent
- **Simple interface**: Easy to use for testing and demonstrations
- **Future extensible**: Designed to support additional test modes later

### Stopping the Interface

Press `Ctrl+C` in the terminal to stop both the agent and GUI. The script handles cleanup automatically.

## Monitoring and Debugging

### Monitor Topic Messages

Watch messages being published (if any):

```bash
ros2 topic echo /servo_angle  # For servo
# or
ros2 topic echo /stepper_angle  # For stepper
```

**Note**: The ESP32 subscribes to these topics, so you won't see messages here unless another node is publishing.

### Check Node Status

Get detailed node information:

```bash
ros2 node info /esp32_servo_node  # For servo
# or
ros2 node info /esp32_stepper_node  # For stepper
```

**Expected output** (servo):
```
/esp32_servo_node
  Subscribers:
    /servo_angle: std_msgs/msg/Int32
  Publishers:
    /rosout: rcl_interfaces/msg/Log
  Services:
    ...
```

**Expected output** (stepper):
```
/esp32_stepper_node
  Subscribers:
    /stepper_angle: std_msgs/msg/Int32
  Publishers:
    /rosout: rcl_interfaces/msg/Log
  Services:
    ...
```

### Serial Monitor

**Note**: Serial Monitor is only available for the servo code. The stepper code disables Serial to allow micro-ROS exclusive access to the serial port.

For servo debugging:

1. Open Arduino IDE
2. `Tools` → `Serial Monitor`
3. Set baud rate to `115200`
4. Watch for:
   - `Subscribing to topic: servo_angle`
   - `Received Angle: X -> Setting Servo to: Y`

For stepper debugging, use LED feedback (LED on = moving, LED off = idle) or ROS topic monitoring.

## Complete Example Session

Here's a complete example of connecting and using the system:

**Terminal 1 - Agent**:
```bash
source /opt/ros/humble/setup.bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0
```

**Terminal 2 - Control**:
```bash
source /opt/ros/humble/setup.bash

# Wait for agent to start, then connect ESP32

# Verify connection
ros2 node list
ros2 topic list

# Control servo
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 0'
sleep 1
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 90'
sleep 1
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 180'

# Or control stepper
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 0'
sleep 2
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 45'
sleep 2
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 90'
```

## Troubleshooting

### Agent Not Starting

**Problem**: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0` fails

**Solutions**:
- Check port exists: `ls /dev/ttyUSB0`
- Check permissions: `sudo chmod 666 /dev/ttyUSB0`
- Try different port: `/dev/ttyACM0`
- Verify micro-ROS agent is installed: `ros2 pkg list | grep micro_ros`

### ESP32 Not Connecting

**Problem**: Agent shows "Waiting for entities..." but ESP32 never connects

**Solutions**:
- **Check agent is running first** (most common issue)
- Verify ESP32 is powered on
- Check USB cable (data cable, not charge-only)
- Try resetting ESP32 (press RESET button)
- Check Serial Monitor for error messages
- Verify code was uploaded correctly
- Try different USB port

### Node Not Visible

**Problem**: `ros2 node list` doesn't show `/esp32_servo_node` or `/esp32_stepper_node`

**Solutions**:
- Verify agent is running and shows connection messages
- Check agent terminal for errors
- Reset ESP32
- Re-upload code to ESP32
- For servo: Check Serial Monitor for initialization errors
- For stepper: Check LED (flashing = error state)

### Motor Not Moving

**Problem**: Commands are sent but motor doesn't move

**Servo Solutions**:
- Check wiring (signal, power, ground)
- Verify servo power supply (5V vs 3.3V)
- Test servo with simple Arduino sketch
- Check Serial Monitor for received messages
- Verify angle values are valid (0-180)
- Check if servo is damaged

**Stepper Solutions**:
- Check wiring (4-wire connection to GPIO 14-17)
- Verify stepper driver power supply
- Check LED feedback (should turn on during movement)
- Verify stepper driver is working
- Check if stepper motor is damaged
- Ensure stepper is not stalled (too much load)

### Permission Denied

**Problem**: `Permission denied` when accessing `/dev/ttyUSB0`

**Solutions**:
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log back in

# Or set permissions
sudo chmod 666 /dev/ttyUSB0
```

### Port Not Found

**Problem**: `/dev/ttyUSB0` doesn't exist

**Solutions**:
- Check `ls /dev/tty*` for available ports
- Try `/dev/ttyACM0` or `/dev/ttyUSB1`
- Unplug and replug USB cable
- Check `dmesg | grep tty` for new devices
- Verify USB drivers are installed (CH340, CP2102, etc.)

### Agent Crashes

**Problem**: Agent crashes or becomes unresponsive

**Solutions**:
- Restart the agent
- Disconnect and reconnect ESP32
- Check for multiple agent instances: `ps aux | grep micro_ros_agent`
- Kill old instances: `pkill micro_ros_agent`

## Best Practices

1. **Always launch agent first**: Start agent before connecting ESP32
2. **Use `--once` for manual control**: Prevents flooding the topic
3. **Monitor output**: 
   - Servo: Use Serial Monitor for debugging
   - Stepper: Use LED feedback (no Serial available)
4. **Check connections**: Verify wiring before troubleshooting software
5. **Keep agent terminal visible**: Watch for connection messages
6. **Use valid angles**: 
   - Servo: Stick to 0-180 degrees to avoid clamping
   - Stepper: Any integer angle (absolute positioning)
7. **For stepper**: Wait for movement to complete before sending next command (LED off = idle)

## Next Steps

- Read the code explanations:
  - [Servo Code Explanation](code-explanation.md) for servo implementation
  - [Stepper Code Explanation](stepper-code-explanation.md) for stepper implementation
- Review the [micro-ROS Overview](micro-ros-overview.md) for architecture details
- Integrate with other ROS 2 nodes for automated control
