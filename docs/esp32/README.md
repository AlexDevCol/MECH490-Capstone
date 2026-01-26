# ESP32 micro-ROS Integration

This section contains documentation for the ESP32 microcontroller integration using micro-ROS (ROS 2 for microcontrollers). The ESP32 acts as a ROS 2 node that controls a servo motor based on commands received over ROS 2 topics.

## Overview

The ESP32 servo control system enables remote control of a servo motor through ROS 2. The ESP32 subscribes to the `/servo_angle` topic and adjusts the servo position based on received angle commands (0-180 degrees).

| Component | Description |
|-----------|-------------|
| **Hardware** | ESP32 microcontroller with servo motor |
| **Communication** | micro-ROS over Serial (USB) |
| **ROS 2 Node** | `esp32_servo_node` |
| **Topic** | `/servo_angle` (std_msgs/Int32) |
| **Servo Pin** | GPIO 13 |
| **Status LED** | GPIO 2 |

## Quick Start

1. **Setup**: Follow the [Setup Guide](setup-guide.md) to install dependencies and flash the ESP32
2. **Connect**: Follow the [Usage Guide](usage-guide.md) to launch the micro-ROS agent and connect
3. **Control**: Publish servo commands:
   ```bash
   ros2 topic pub --once /servo_angle std_msgs/msg/Int32 'data: 90'
   ```

## Documentation Index

### Getting Started
- **[Setup Guide](setup-guide.md)** - Installation, configuration, and hardware setup
- **[Usage Guide](usage-guide.md)** - Connection workflow, launching, and manual control

### Technical Documentation
- **[micro-ROS Overview](micro-ros-overview.md)** - Architecture, concepts, and how micro-ROS works
- **[Code Explanation](code-explanation.md)** - Detailed walkthrough of the Arduino sketch

## Prerequisites Checklist

Before getting started, ensure you have:

- [ ] Arduino IDE installed
- [ ] ESP32 board support package installed in Arduino IDE
- [ ] micro-ROS Arduino library installed
- [ ] ROS 2 Humble installed on host machine
- [ ] micro-ROS agent installed (`micro_ros_agent` package)
- [ ] ESP32 development board (e.g., ESP32 DevKit)
- [ ] Servo motor (standard 180-degree servo)
- [ ] USB cable for ESP32 connection

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

- **ROS 2 Integration**: Full ROS 2 node with topic subscription
- **Servo Control**: Direct PWM control of standard servo motors
- **Safety Limits**: Automatic clamping of angle values to 0-180 degrees
- **Status Feedback**: LED indication and serial debug output
- **Error Handling**: Robust error detection with visual feedback

## File Structure

```
src/robot_arm/robot_esp32/
└── ROS_Servo_Sweep/
    └── ROS_Servo_Sweep.ino    # Main Arduino sketch
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
3. Use the [Usage Guide](usage-guide.md) to connect and control the servo
4. Review the [Code Explanation](code-explanation.md) to understand the implementation
