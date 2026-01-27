# ESP32 micro-ROS Integration

This section contains documentation for the ESP32 microcontroller integration using micro-ROS (ROS 2 for microcontrollers). The ESP32 acts as ROS 2 nodes that control motors (servo and stepper) based on commands received over ROS 2 topics.

## Overview

The ESP32 motor control system enables remote control of motors through ROS 2. Two implementations are available:

### Servo Motor Control
- **Node**: `esp32_servo_node`
- **Topic**: `/servo_angle` (std_msgs/Int32)
- **Range**: 0-180 degrees
- **Control**: Direct PWM control

### Stepper Motor Control
- **Node**: `esp32_stepper_node`
- **Topic**: `/stepper_angle` (std_msgs/Int32)
- **Range**: Any integer angle (absolute positioning)
- **Control**: Step/direction with position tracking

| Component | Servo | Stepper |
|-----------|-------|---------|
| **Hardware** | ESP32 + Servo motor | ESP32 + Stepper motor + Driver |
| **Communication** | micro-ROS over Serial (USB) | micro-ROS over Serial (USB) |
| **ROS 2 Node** | `esp32_servo_node` | `esp32_stepper_node` |
| **Topic** | `/servo_angle` | `/stepper_angle` |
| **Control Pin** | GPIO 13 | GPIO 14-17 (4-wire) |
| **Status LED** | GPIO 2 | GPIO 2 |
| **Position Memory** | No | Yes (absolute) |
| **Serial Output** | Enabled | Disabled (for micro-ROS) |

## Quick Start

### Servo Motor

1. **Setup**: Follow the [Setup Guide](setup-guide.md) to install dependencies and flash the ESP32
2. **Connect**: Follow the [Usage Guide](usage-guide.md) to launch the micro-ROS agent and connect
3. **Control**: Publish servo commands:
   ```bash
   ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 90'
   ```

### Stepper Motor

1. **Setup**: Follow the [Setup Guide](setup-guide.md) to install dependencies (including AccelStepper library) and flash the ESP32
2. **Connect**: Follow the [Usage Guide](usage-guide.md) to launch the micro-ROS agent and connect
3. **Control**: Publish stepper commands:
   ```bash
   ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 45'
   ```

## Documentation Index

### Getting Started
- **[Setup Guide](setup-guide.md)** - Installation, configuration, and hardware setup
- **[Usage Guide](usage-guide.md)** - Connection workflow, launching, and manual control

### Technical Documentation
- **[micro-ROS Overview](micro-ros-overview.md)** - Architecture, concepts, and how micro-ROS works
- **[Servo Code Explanation](code-explanation.md)** - Detailed walkthrough of the servo Arduino sketch
- **[Stepper Code Explanation](stepper-code-explanation.md)** - Detailed walkthrough of the stepper Arduino sketch

## Prerequisites Checklist

Before getting started, ensure you have:

- [ ] Arduino IDE installed
- [ ] ESP32 board support package installed in Arduino IDE
- [ ] micro-ROS Arduino library installed
- [ ] ROS 2 Humble installed on host machine
- [ ] micro-ROS agent installed (`micro_ros_agent` package)
- [ ] ESP32 development board (e.g., ESP32 DevKit)
- [ ] Motor (servo motor OR stepper motor with driver)
- [ ] USB cable for ESP32 connection
- [ ] For stepper: AccelStepper library installed

## Architecture Overview

```
┌─────────┐      Serial/USB      ┌──────────────┐      ROS 2 DDS      ┌──────────┐
│  ESP32  │ ◄──────────────────► │ micro-ROS    │ ◄─────────────────► │ ROS 2    │
│  Node   │                      │ Agent        │                     │ Network  │
└─────────┘                      └──────────────┘                     └──────────┘
     │                                                                        │
     │ Servo Control                                                          │
     ▼                                                                        │
┌─────────┐                                                          ┌──────────┐
│ Servo   │                                                          │ Your     │
│ Motor   │                                                          │ Nodes    │
└─────────┘                                                          └──────────┘
```

## Key Features

### Servo Motor
- **ROS 2 Integration**: Full ROS 2 node with topic subscription
- **Servo Control**: Direct PWM control of standard servo motors
- **Safety Limits**: Automatic clamping of angle values to 0-180 degrees
- **Status Feedback**: LED indication and serial debug output
- **Error Handling**: Robust error detection with visual feedback

### Stepper Motor
- **ROS 2 Integration**: Full ROS 2 node with topic subscription
- **Position Control**: Absolute positioning with position memory
- **Acceleration Control**: Smooth acceleration/deceleration via AccelStepper
- **Status Feedback**: LED indication (no Serial to avoid micro-ROS conflicts)
- **Error Handling**: Robust error detection with visual feedback

## File Structure

```
src/robot_arm/robot_esp32/
├── Controller Code/
│   ├── ROS_Servo_Sweep/
│   │   └── ROS_Servo_Sweep.ino    # Servo control sketch
│   └── ROS_Stepper_Control/
│       └── ROS_Stepper_Control.ino    # Stepper control sketch
```

## Common Tasks

### Test Servo Control

```bash
# Terminal 1: Start micro-ROS agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0

# Terminal 2: Publish servo commands
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 45'
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 90'
ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 135'
```

### Test Stepper Control

```bash
# Terminal 1: Start micro-ROS agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0

# Terminal 2: Publish stepper commands
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 45'
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 90'
ros2 topic pub --once /stepper_angle std_msgs/msg/Int32 'data: 0'
```

### Monitor Connection

```bash
# List ROS 2 nodes
ros2 node list

# List topics
ros2 topic list

# Echo topic (if publishing)
ros2 topic echo /servo_angle
```

## Troubleshooting

See the [Usage Guide](usage-guide.md#troubleshooting) for detailed troubleshooting steps. Common issues include:

- **Connection problems**: Ensure agent is launched before connecting ESP32
- **Port detection**: Check `/dev/ttyUSB0` or `/dev/ttyACM0` permissions
- **No node visible**: Verify micro-ROS agent is running and ESP32 is connected

## Next Steps

1. Read the [micro-ROS Overview](micro-ros-overview.md) to understand the architecture
2. Follow the [Setup Guide](setup-guide.md) to get your hardware ready
3. Use the [Usage Guide](usage-guide.md) to connect and control motors
4. Review the code explanations:
   - [Servo Code Explanation](code-explanation.md) for servo implementation
   - [Stepper Code Explanation](stepper-code-explanation.md) for stepper implementation
