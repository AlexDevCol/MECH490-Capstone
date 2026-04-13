# BB01 ESP32 Controller Usage Guide

## Quick Start

This guide covers setup, flashing, and operation of the BB01 ESP32 controller firmware.

**Firmware Location:** [`src/robot_arm/robot_esp32/Controller Code/BB01_Controller/BB01_Controller.ino`](../../../../src/robot_arm/robot_esp32/Controller%20Code/BB01_Controller/BB01_Controller.ino)

## Prerequisites

### Hardware

- ESP32-S3 development board (tested with ESP32-S3-DevKitC-1)
- USB cable for programming and micro-ROS communication
- BB01 robot arm with:
  - 6x NEMA23 stepper motors
  - CL42T drivers (joints 1-3)
  - CL57T drivers (joints 4-6)
  - 2x ULN2803A signal buffers
  - Wiring configured for common anode

### Software

- **Arduino IDE** (1.8.19 or later) or **PlatformIO**
- **ESP32 Arduino Core** (2.0.0 or later)
- **micro-ROS Arduino library** (installed via Arduino Library Manager)
- **ESP32Servo library** (for gripper control)
- **ROS 2 Humble** (or compatible) on host computer
- **micro-ROS Agent** (`ros-humble-micro-ros-agent`)

## Installation

### 1. Install Arduino IDE

Download and install Arduino IDE from [arduino.cc](https://www.arduino.cc/en/software).

### 2. Install ESP32 Board Support

1. Open Arduino IDE
2. Go to **File → Preferences**
3. Add to **Additional Board Manager URLs:**
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Go to **Tools → Board → Boards Manager**
5. Search for "ESP32" and install **esp32 by Espressif Systems**

### 3. Install Required Libraries

Go to **Sketch → Include Library → Manage Libraries** and install:

- **micro_ros_arduino** (by micro-ROS team)
- **ESP32Servo** (by Kevin Harrington)

### 4. Install micro-ROS Agent (Host Computer)

```bash
# Ubuntu/Debian
sudo apt install ros-humble-micro-ros-agent

# Or build from source
mkdir -p ~/microros_ws/src
cd ~/microros_ws/src
git clone -b humble https://github.com/micro-ROS/micro_ros_setup.git
cd ~/microros_ws
rosdep update && rosdep install --from-paths src --ignore-src -y
colcon build
source install/setup.bash
```

## Configuration

### 1. Select Board

In Arduino IDE:
- **Tools → Board → ESP32 Arduino → ESP32S3 Dev Module**
- **Tools → USB Mode → Hardware CDC and JTAG**
- **Tools → Partition Scheme → Default** (or as needed)

### 2. Configure Serial Port

- **Tools → Port → /dev/ttyUSB0** (or your ESP32 port)
- On Linux, you may need to add your user to the `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Log out and back in for changes to take effect
  ```

### 3. Verify Pin Mapping

Open `BB01_Controller.ino` and verify pin assignments match your hardware:

```cpp
// Motors 1-3 (should match ULN2803A #1 wiring)
#define J1_STEP_PIN 12
#define J1_DIR_PIN  13
// ... etc

// Motors 4-6 (ESP32-S3 compatible pins)
#define J5_STEP_PIN 35  // Must be 35-38 for ESP32-S3
#define J5_DIR_PIN  36
#define J6_STEP_PIN 37
#define J6_DIR_PIN  38
```

**Important:** If using original ESP32 (not S3), motors 5-6 can use GPIO 22-26 instead.

### 4. Adjust Motion Parameters (Optional)

Edit these constants if your robot has different characteristics:

```cpp
// Steps per motor revolution (driver microstep setting)
static const float steps_per_rev[NUM_JOINTS] = {
  800.0, 800.0, 800.0, 800.0, 800.0, 800.0
};

// Gear ratio
static const float gear_ratio[NUM_JOINTS] = {
  19.0, 19.0, 19.0, 19.0, 19.0, 19.0
};

// Maximum velocity (rad/s)
static const float max_velocity_rad[NUM_JOINTS] = {
  0.3, 0.3, 0.3, 0.3, 0.3, 0.3
};

// Maximum acceleration (rad/s²)
static const float max_accel_rad[NUM_JOINTS] = {
  2.4, 2.4, 2.4, 2.4, 2.4, 2.4
};
```

## Flashing Firmware

### Method 1: Arduino IDE

1. Open `BB01_Controller.ino` in Arduino IDE
2. Select correct board and port (see Configuration above)
3. Click **Upload** (or press `Ctrl+U`)
4. Wait for "Done uploading" message

### Method 2: PlatformIO

```bash
cd src/robot_arm/robot_esp32/Controller\ Code/BB01_Controller
pio run --target upload
```

### Verify Upload

After flashing, open Serial Monitor (115200 baud). You should see:
- No errors
- LED on ESP32 board should be off initially

## Running micro-ROS Agent

The ESP32 firmware communicates with ROS 2 via the micro-ROS agent, which bridges serial communication to ROS 2 topics.

### Start Agent

```bash
# Find your ESP32 port
ls /dev/ttyUSB* /dev/ttyACM*

# Start micro-ROS agent (replace /dev/ttyUSB0 with your port)
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0
```

**Expected output:**
```
[INFO] [micro_ros_agent]: Waiting for agent...
[INFO] [micro_ros_agent]: Agent started
```

### Verify Connection

In a new terminal:

```bash
# List ROS 2 nodes (should see esp32_bb01_node)
ros2 node list

# List topics (should see /joint_position_commands and /joint_position_feedback)
ros2 topic list

# Check node info
ros2 node info /esp32_bb01_node
```

## Testing

### 1. Manual Command Test

Send a test command to move all joints to 0 radians:

```bash
ros2 topic pub --once /joint_position_commands std_msgs/msg/Float64MultiArray \
  "{data: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"
```

**Expected behavior:**
- LED on ESP32 turns on (command received)
- Motors move to target positions
- LED turns off when all motors arrive

### 2. Monitor Feedback

Watch current joint positions:

```bash
ros2 topic echo /joint_position_feedback
```

You should see messages every 200ms with current positions in radians.

### 3. Monitor Velocities

Watch approximate joint velocities:

```bash
ros2 topic echo /joint_velocity_debug
```

You should see messages every 1000ms with velocities in rad/s.

### 4. Continuous Command Test

Move joints in a pattern:

```bash
# Move joint 1 to 90 degrees (π/2 radians)
ros2 topic pub --once /joint_position_commands std_msgs/msg/Float64MultiArray \
  "{data: [1.571, 0.0, 0.0, 0.0, 0.0, 0.0]}"

# Move all joints to 45 degrees
ros2 topic pub --once /joint_position_commands std_msgs/msg/Float64MultiArray \
  "{data: [0.785, 0.785, 0.785, 0.785, 0.785, 0.785]}"
```

## Integration with ROS 2 Control

The firmware is designed to work with `ros2_control` via a `TopicBasedSystem` hardware interface plugin.

### Architecture

```
MoveIt → arm_controller → TopicBasedSystem → micro-ROS Agent → ESP32
```

### Required Hardware Interface

The `robot_hardware` package should:
- Subscribe to `/joint_position_feedback` (read current positions)
- Publish to `/joint_position_commands` (write target positions)
- Implement `hardware_interface::SystemInterface`

See [Hardware Integration Plan](arduino_hardware_integration_ea3c5f2e.plan.md) for details.

## Standalone Testing (Without micro-ROS)

For hardware debugging, use the standalone test sketch:

**Location:** [`src/robot_arm/robot_esp32/Controller Code/BB01_StepperTest/BB01_StepperTest.ino`](../../../../src/robot_arm/robot_esp32/Controller%20Code/BB01_StepperTest/BB01_StepperTest.ino)

### Usage

1. Flash `BB01_StepperTest.ino` instead of `BB01_Controller.ino`
2. Open Serial Monitor (115200 baud)
3. Send commands via Serial:
   - `1 90` - Move motor 1 to 90 degrees
   - `4 90` - Move motor 4 to 90 degrees
   - `1,4 90` - Move motors 1 and 4 together
   - `all 90` - Move all 6 motors to 90 degrees
   - `r` - Reset all motors to position 0

The test sketch provides detailed diagnostics:
- Loop timing statistics
- Per-motor speed measurements
- Position feedback

## Troubleshooting

### Motors Not Moving

1. **Check enable pin:**
   - ENA_PIN (GPIO 16) should be HIGH (drivers enabled)
   - Verify ULN2803A wiring

2. **Check micro-ROS connection:**
   ```bash
   ros2 node list  # Should show /esp32_bb01_node
   ros2 topic echo /joint_position_commands  # Should see your commands
   ```

3. **Check serial port:**
   - Verify ESP32 is connected: `ls /dev/ttyUSB*`
   - Check permissions: `ls -l /dev/ttyUSB0`
   - Add user to dialout group if needed

4. **Check wiring:**
   - Verify step/dir pins match firmware
   - Check ULN2803A connections
   - Verify driver power supply

### Motors Moving Wrong Direction

**Option 1:** Swap DIR+ and DIR- wires on the driver

**Option 2:** Invert direction logic in firmware:
```cpp
// In updateStepper(), change:
digitalWrite(m.dir_pin, (m.dir > 0) ? HIGH : LOW);
// To:
digitalWrite(m.dir_pin, (m.dir > 0) ? LOW : HIGH);
```

### GPIO Errors (ESP32-S3)

If you see errors like:
```
E (xxxxx) gpio: gpio_set_level(227): GPIO output gpio_num error
```

**Cause:** Using GPIO 22-26 on ESP32-S3 (reserved for flash/PSRAM)

**Solution:** Ensure motors 5-6 use GPIO 35-38:
```cpp
#define J5_STEP_PIN 35  // Not 22
#define J5_DIR_PIN  36  // Not 23
#define J6_STEP_PIN 37  // Not 25
#define J6_DIR_PIN  38  // Not 26
```

### Slow or Jerky Motion

1. **Check feedback publishing rate:**
   - Reduce `FEEDBACK_PERIOD_MS` from 200 to 500ms if needed
   - Or eliminate debug velocity publisher

2. **Check acceleration:**
   - Reduce `max_accel_rad` if motors are skipping steps
   - Increase if motion is too slow

3. **Check serial communication:**
   - Ensure micro-ROS agent is running smoothly
   - Check for serial buffer overflows

### micro-ROS Agent Not Connecting

1. **Check port:**
   ```bash
   # List available ports
   ls /dev/ttyUSB* /dev/ttyACM*
   
   # Try different port
   ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0
   ```

2. **Check baud rate:**
   - Default is auto-detect, but you can specify:
   ```bash
   ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 --baudrate 115200
   ```

3. **Reset ESP32:**
   - Press reset button on ESP32 board
   - Agent should reconnect automatically

### Serial Monitor Shows Garbage

- **Wrong baud rate:** Set Serial Monitor to 115200 baud
- **Wrong board selected:** Ensure ESP32S3 Dev Module is selected
- **USB driver issues:** Try different USB cable or port

## Performance Tuning

### Adjust Motion Speed

Edit `max_velocity_rad` array:
```cpp
static const float max_velocity_rad[NUM_JOINTS] = {
  0.3, 0.3, 0.3, 0.3, 0.3, 0.3  // Increase for faster motion
};
```

**Typical range:** 0.1 - 0.5 rad/s (higher may cause step skipping)

### Adjust Acceleration

Edit `max_accel_rad` array:
```cpp
static const float max_accel_rad[NUM_JOINTS] = {
  2.4, 2.4, 2.4, 2.4, 2.4, 2.4  // Increase for faster accel/decel
};
```

**Typical range:** 1.0 - 5.0 rad/s² (higher may cause step skipping on loaded joints)

### Adjust Feedback Rate

Edit `FEEDBACK_PERIOD_MS`:
```cpp
#define FEEDBACK_PERIOD_MS 200  // Reduce for faster feedback (50-500ms)
```

**Trade-off:** Faster feedback = more serial traffic = potential blocking

## Safety Considerations

1. **Emergency stop:** Disconnect power or set ENA_PIN LOW to disable all drivers
2. **Position limits:** Add software limits in firmware if needed (not currently implemented)
3. **Step skipping:** Monitor for missed steps; reduce acceleration if occurring
4. **Overheating:** Ensure drivers have adequate cooling during extended operation

## Maintenance

### Regular Checks

- Verify all motors reach target positions accurately
- Check for step skipping (monitor `/joint_velocity_debug`)
- Inspect wiring for loose connections
- Verify driver power supply voltage

### Firmware Updates

1. Backup current working firmware
2. Test changes in standalone test sketch first
3. Verify with micro-ROS before deploying to production

## References

- [Implementation Documentation](esp32_bb01_controller_implementation.md)
- [Hardware Integration Plan](arduino_hardware_integration_ea3c5f2e.plan.md)
- [micro-ROS Documentation](https://micro.ros.org/)
- [ESP32-S3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
