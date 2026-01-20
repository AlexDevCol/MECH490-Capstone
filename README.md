# MECH490 Capstone - Robotic Arm Control

A ROS 2 workspace for simulation, motion planning, and control of multiple robotic arm platforms.

## Overview

This project provides a complete robotics software stack including:
- Robot descriptions (URDF/Xacro) for multiple robots
- Gazebo simulation environment
- MoveIt 2 motion planning
- MoveIt Task Constructor (MTC) for complex manipulation tasks
- Hardware interface for real robot control

## Supported Robots

| Robot | DOF | Description | Status |
|-------|-----|-------------|--------|
| **Panda** | 7 | Franka Emika Panda | Stable (Reference) |
| **Rob** | 5+1 | BCN3D Moveo-based custom robot | Stable |
| **BB01** | 6 | New capstone robot | Under Construction |

## Quick Start

### Prerequisites

- Ubuntu 22.04 (Jammy)
- ROS 2 Humble
- Gazebo Fortress
- MoveIt 2

### Installation

```bash
# Clone the repository
cd ~/Capstone
git clone <repository-url> MECH490-Capstone
cd MECH490-Capstone

# Install dependencies
rosdep install --from-paths src --ignore-src -r -y

# Build
colcon build --symlink-install
source install/setup.bash
```

### Launch Simulation

**Using the interactive launcher:**
```bash
./run_script.sh
```

**Direct launch (Rob robot):**
```bash
# Terminal 1: Start Gazebo
ros2 launch rob_gazebo rob.gazebo.launch.py

# Terminal 2: Start MoveIt (after Gazebo loads)
ros2 launch rob_moveit_config move_group.launch.py
```

**Direct launch (Panda robot):**
```bash
# Terminal 1
ros2 launch rob_gazebo panda.gazebo.launch.py

# Terminal 2
ros2 launch panda_moveit_config move_group.launch.py
```

### Visualize Robot Only

```bash
ros2 launch rob_description display.launch.py
ros2 launch panda_description display.launch.py
```

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Documentation Index](docs/README.md)** - Start here

### Architecture
- [Project Overview](docs/architecture/project-overview.md) - Repository structure and packages
- [Package Relationships](docs/architecture/package-relationships.md) - Dependencies and data flow
- [Launch Flow](docs/architecture/launch-flow.md) - Launch file hierarchy

### Robots
- [Panda Robot](docs/robots/panda.md) - Franka Emika Panda (7 DOF)
- [Rob Robot](docs/robots/rob-moveo.md) - BCN3D Moveo-based (5+1 DOF)
- [BB01 Robot](docs/robots/bb01.md) - New capstone robot (WIP)

### Development
- [Adding a New Robot](docs/development/adding-new-robot.md) - Integration guide
- [Parametrization Roadmap](docs/development/parametrization-roadmap.md) - Future architecture

### Reference
- [Launch Arguments](docs/reference/launch-arguments.md) - Quick reference

## Package Structure

```
src/
├── robot_arm/
│   ├── panda_description/      # Panda URDF and meshes
│   ├── rob_description/        # Rob URDF and meshes
│   ├── bb01_description/       # BB01 URDF and meshes (WIP)
│   ├── panda_moveit_config/    # Panda MoveIt configuration
│   ├── rob_moveit_config/      # Rob MoveIt configuration
│   ├── rob_gazebo/             # Gazebo simulation
│   ├── rob_bringup/            # Launch scripts
│   ├── rob_mtc_demos/          # MoveIt Task Constructor demos
│   └── ...
├── moveit_task_constructor/    # MTC library (vendored)
└── warehouse_ros_mongo/        # Motion plan storage (vendored)
```

## Running MTC Demos

After starting simulation with MoveIt:

```bash
ros2 launch rob_mtc_demos mtc_demos.launch.py exe:=cartesian
```

Available demos: `alternative_path_costs`, `cartesian`, `fallbacks_move_to`, `ik_clearance_cost`, `modular`

## Development

### Building Specific Packages

```bash
colcon build --packages-select rob_description rob_moveit_config
```

### Clean Build

```bash
rm -rf build install log
colcon build --symlink-install
```

## Roadmap

See [Parametrization Roadmap](docs/development/parametrization-roadmap.md) for planned improvements:
- Consolidate duplicate description packages
- Create robot-agnostic launch files
- Unified MoveIt configuration

## License

See individual package licenses in `src/robot_arm/*/LICENSE`.

## Acknowledgments

- BCN3D Technologies for the Moveo robot design
- MoveIt community for motion planning framework
- ROS 2 community for robotics middleware
