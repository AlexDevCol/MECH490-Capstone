# Setup Guide

This guide walks you through setting up the ESP32 servo control system with micro-ROS, from installing dependencies to uploading the code and connecting hardware.

## Prerequisites

Before starting, ensure you have:

- **Operating System**: Linux (Ubuntu 22.04 recommended) or macOS/Windows
- **ROS 2**: ROS 2 Humble installed and sourced
- **Arduino IDE**: Version 1.8.x or 2.x
- **Hardware**:
  - ESP32 development board (e.g., ESP32 DevKit V1)
  - Standard 180-degree servo motor (e.g., SG90)
  - USB cable (USB-A to Micro-USB or USB-C, depending on your ESP32)
  - Jumper wires for servo connection

## Step 1: Install Arduino IDE

### Ubuntu/Debian

```bash
# Download from Arduino website or install via snap
sudo snap install arduino

# Or download .tar.xz from https://www.arduino.cc/en/software
```

### macOS

```bash
# Using Homebrew
brew install --cask arduino

# Or download from https://www.arduino.cc/en/software
```

### Windows

Download and install from: https://www.arduino.cc/en/software

## Step 2: Install ESP32 Board Support

1. **Open Arduino IDE**

2. **Add ESP32 Board Manager URL**:
   - Go to `File` → `Preferences`
   - In "Additional Board Manager URLs", add:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Click "OK"

3. **Install ESP32 Board Package**:
   - Go to `Tools` → `Board` → `Boards Manager`
   - Search for "esp32"
   - Install "esp32" by Espressif Systems (latest version)

4. **Select Board**:
   - Go to `Tools` → `Board` → `ESP32 Arduino`
   - Select your board (e.g., "ESP32 Dev Module")

## Step 3: Install micro-ROS Arduino Library

### Method 1: Library Manager (Recommended)

1. **Open Arduino IDE**

2. **Install Library**:
   - Go to `Tools` → `Manage Libraries...`
   - Search for "micro_ros_arduino"
   - Install "micro_ros_arduino" by micro-ROS

### Method 2: Manual Installation

1. **Download Library**:
   ```bash
   cd ~/Arduino/libraries
   git clone https://github.com/micro-ROS/micro_ros_arduino.git
   ```

2. **Restart Arduino IDE**

## Step 4: Install Motor Control Libraries

### For Servo Motor

1. **Open Arduino IDE**

2. **Install Library**:
   - Go to `Tools` → `Manage Libraries...`
   - Search for "ESP32Servo"
   - Install "ESP32Servo" by Kevin Harrington

### For Stepper Motor

1. **Open Arduino IDE**

2. **Install Library**:
   - Go to `Tools` → `Manage Libraries...`
   - Search for "AccelStepper"
   - Install "AccelStepper" by Mike McCauley

## Step 5: Install micro-ROS Agent (Host Machine)

The micro-ROS agent must be installed on your host computer (where ROS 2 runs).

### Ubuntu (ROS 2 Humble)

```bash
# Source ROS 2
source /opt/ros/humble/setup.bash

# Install micro-ROS agent
sudo apt update
sudo apt install ros-humble-micro-ros-agent
```

### From Source (Alternative)

If the package is not available, build from source:

```bash
# Create workspace
mkdir -p ~/microros_ws/src
cd ~/microros_ws/src

# Clone micro-ROS agent
git clone https://github.com/micro-ROS/micro-ros_agent.git

# Install dependencies
cd ~/microros_ws
rosdep update
rosdep install --from-paths src --ignore-src -y

# Build
colcon build

# Source
source install/setup.bash
```

## Step 6: Configure Arduino IDE for ESP32

1. **Select Board**:
   - `Tools` → `Board` → `ESP32 Arduino` → `ESP32 Dev Module`

2. **Configure Settings**:
   - **Upload Speed**: `921600` (or `115200` if upload fails)
   - **CPU Frequency**: `240MHz (WiFi/BT)`
   - **Flash Frequency**: `80MHz`
   - **Flash Mode**: `QIO`
   - **Flash Size**: `4MB (32Mb)`
   - **Partition Scheme**: `Default 4MB with spiffs`
   - **Core Debug Level**: `None` (or `Info` for debugging)
   - **Port**: Select your ESP32 port (e.g., `/dev/ttyUSB0`)

3. **Note Your Port**: You'll need this for the micro-ROS agent later.

## Step 7: Open and Upload Code

1. **Open Sketch**:
   - `File` → `Open`
   - For servo: Navigate to `src/robot_arm/robot_esp32/Controller Code/ROS_Servo_Sweep/ROS_Servo_Sweep.ino`
   - For stepper: Navigate to `src/robot_arm/robot_esp32/Controller Code/ROS_Stepper_Control/ROS_Stepper_Control.ino`

2. **Verify Code**:
   - Click the checkmark (✓) or `Sketch` → `Verify/Compile`
   - Wait for compilation to complete

3. **Upload Code**:
   - Connect ESP32 via USB
   - Click the upload button (→) or `Sketch` → `Upload`
   - Wait for upload to complete
   - You may need to press the BOOT button on your ESP32 during upload

4. **Verify Upload**:
   - **For servo**: Open Serial Monitor (`Tools` → `Serial Monitor`)
     - Set baud rate to `115200`
     - You should see: `Subscribing to topic: servo_angle`
   - **For stepper**: Serial Monitor is disabled (micro-ROS uses serial port)
     - Check LED on GPIO 2 (should be off when idle)
     - Use ROS topic commands to test

## Step 8: Hardware Connections

### Servo Motor Wiring

Connect the servo motor to the ESP32:

| Servo Wire | ESP32 Pin | Description |
|------------|-----------|-------------|
| **Red (VCC)** | **5V** or **3.3V** | Power (check servo voltage requirements) |
| **Black/Brown (GND)** | **GND** | Ground |
| **Yellow/Orange (Signal)** | **GPIO 13** | PWM control signal |

**Important Notes**:
- Most servos require 5V, but ESP32 GPIO is 3.3V logic (signal wire is fine)
- For 5V servos, use external 5V power supply and connect grounds
- For 3.3V servos, can use ESP32 3.3V pin directly
- Always connect ground (GND) between ESP32 and servo

### Stepper Motor Wiring

Connect the stepper motor to the ESP32 (4-wire control):

| Stepper Wire | ESP32 Pin | Description |
|--------------|-----------|-------------|
| **Coil 1** | **GPIO 14** | Motor coil 1 (via driver if using driver board) |
| **Coil 2** | **GPIO 15** | Motor coil 2 |
| **Coil 3** | **GPIO 16** | Motor coil 3 |
| **Coil 4** | **GPIO 17** | Motor coil 4 |
| **GND** | **GND** | Ground (common) |
| **VCC** | **External Power** | Motor power (typically 5V or 12V, check motor specs) |

**Important Notes**:
- For direct control (ULN2003 driver): Connect coils directly to GPIO pins
- For driver boards (A4988, DRV8825, etc.): Connect STEP/DIR pins instead
- Stepper motors typically require external power supply (not from ESP32)
- Always connect ground (GND) between ESP32 and motor/driver
- Check motor voltage requirements (5V, 12V, etc.)

### LED (Optional)

The built-in LED on most ESP32 boards is on GPIO 2. If your board doesn't have a built-in LED:
- Connect an LED with resistor (220Ω) to GPIO 2

### Complete Wiring Diagrams

**Servo Motor**:
```
ESP32 DevKit
┌─────────────┐
│             │
│  GPIO 13 ───┼─── Servo Signal (Yellow/Orange)
│  GND     ───┼─── Servo GND (Black/Brown)
│  5V/3.3V ───┼─── Servo VCC (Red)
│             │
│  GPIO 2  ───┼─── LED (Built-in or external)
│             │
│  USB    ────┼─── USB Cable to Computer
└─────────────┘
```

**Stepper Motor (4-wire direct)**:
```
ESP32 DevKit
┌─────────────┐
│             │
│  GPIO 14 ───┼─── Coil 1
│  GPIO 15 ───┼─── Coil 2
│  GPIO 16 ───┼─── Coil 3
│  GPIO 17 ───┼─── Coil 4
│  GND     ───┼─── Motor GND
│             │
│  GPIO 2  ───┼─── LED (Built-in or external)
│             │
│  USB    ────┼─── USB Cable to Computer
└─────────────┘
     │
     └─── External Power Supply (5V/12V) to Motor VCC
```

## Step 9: Verify Installation

### Test Serial Communication

**For Servo**:
1. **Open Serial Monitor** in Arduino IDE
2. **Set baud rate**: 115200
3. **Reset ESP32** (press RESET button)
4. **Expected output**: `Subscribing to topic: servo_angle`

**For Stepper**:
- Serial Monitor is disabled (micro-ROS uses serial port exclusively)
- Check LED on GPIO 2 (should be off when idle)
- Use ROS topic commands to verify connection

### Test micro-ROS Agent

See the [Usage Guide](usage-guide.md) for detailed connection and testing instructions.

## Troubleshooting

### Arduino IDE Issues

**Problem**: ESP32 board not found in Board Manager
- **Solution**: Check the board manager URL is correct and try again

**Problem**: Upload fails with "Failed to connect to ESP32"
- **Solution**: 
  - Hold BOOT button while clicking upload
  - Try different USB cable
  - Check port permissions: `sudo chmod 666 /dev/ttyUSB0`

**Problem**: Compilation errors
- **Solution**: 
  - Ensure all libraries are installed
  - Check Arduino IDE version compatibility
  - Try restarting Arduino IDE

### Library Issues

**Problem**: `micro_ros_arduino.h` not found
- **Solution**: Reinstall micro-ROS Arduino library via Library Manager

**Problem**: `ESP32Servo.h` not found
- **Solution**: Install ESP32Servo library via Library Manager

**Problem**: `AccelStepper.h` not found
- **Solution**: Install AccelStepper library via Library Manager

### Hardware Issues

**Problem**: Motor doesn't move
- **Servo Solutions**: 
  - Check wiring connections
  - Verify servo power supply (5V vs 3.3V)
  - Test servo with simple Arduino sketch first
  - Check if servo is working (may be damaged)
- **Stepper Solutions**:
  - Check wiring connections (4-wire to GPIO 14-17)
  - Verify stepper driver power supply
  - Check if stepper motor is working (may be damaged)
  - Verify stepper is not stalled (too much load)
  - Check LED feedback (should turn on during movement)

**Problem**: ESP32 not detected
- **Solution**: 
  - Check USB cable (data cable, not charge-only)
  - Try different USB port
  - Install USB drivers if needed (CH340, CP2102, etc.)
  - Check `ls /dev/tty*` to see if port appears

### Port Permission Issues (Linux)

**Problem**: Permission denied when accessing `/dev/ttyUSB0`
- **Solution**:
  ```bash
  # Add user to dialout group
  sudo usermod -a -G dialout $USER
  
  # Log out and log back in, or:
  newgrp dialout
  
  # Or set permissions temporarily
  sudo chmod 666 /dev/ttyUSB0
  ```

## Next Steps

Once setup is complete:

1. Follow the [Usage Guide](usage-guide.md) to connect and test the system
2. Read the [Code Explanation](code-explanation.md) to understand the implementation
3. Review the [micro-ROS Overview](micro-ros-overview.md) for architecture details

## Additional Resources

- [ESP32 Arduino Core Documentation](https://github.com/espressif/arduino-esp32)
- [micro-ROS Arduino Library](https://github.com/micro-ROS/micro_ros_arduino)
- [ESP32Servo Library](https://github.com/madhephaestus/ESP32Servo)
- [AccelStepper Library](https://www.airspayce.com/mikem/arduino/AccelStepper/)