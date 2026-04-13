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
| **BB01** | 6 | New capstone robot | Fully Integrated |

## Quick Start

### Prerequisites

- Ubuntu 22.04 (Jammy)
- ROS 2 Humble
- Gazebo Fortress
- MoveIt 2

### Installation

#### 1. Clone the repository

```bash
cd ~/Capstone
git clone <repository-url> MECH490-Capstone
cd MECH490-Capstone
```

#### 2. Set up dependencies workspace (optional but recommended)

For faster builds, move vendored packages to a separate workspace:

```bash
# Create dependencies workspace
mkdir -p ~/ros2_dependencies_ws/src
cd ~/ros2_dependencies_ws/src

# Move vendored packages (if they exist in src/)
# mv ~/Capstone/MECH490-Capstone/src/moveit_task_constructor .
# mv ~/Capstone/MECH490-Capstone/src/warehouse_ros_mongo .

# Build dependencies workspace
cd ~/ros2_dependencies_ws
colcon build --symlink-install
source install/setup.bash
```

#### 3. Build the main workspace

```bash
cd ~/Capstone/MECH490-Capstone

# Install system dependencies
rosdep install --from-paths src --ignore-src -r -y

# Source dependencies workspace if you created one
# source ~/ros2_dependencies_ws/install/setup.bash

# Build
colcon build --symlink-install
source install/setup.bash
```

**Note:** If vendored packages (`moveit_task_constructor`, `warehouse_ros_mongo`) are in a separate workspace, source that workspace before building this one.

### Launch Simulation

**Using the interactive launcher:**
```bash
./run_script.sh
```

**Direct launch (any robot):**
```bash
# Terminal 1: Start Gazebo
ros2 launch robot_gazebo simulation.launch.py robot:=rob

# Terminal 2: Start MoveIt (after Gazebo loads, ~15s)
ros2 launch robot_moveit_config move_group.launch.py robot:=rob
```

Replace `robot:=rob` with `robot:=panda` or `robot:=bb01` for other robots.

### Visualize Robot Only

```bash
ros2 launch robot_description display.launch.py robot:=rob
ros2 launch robot_description display.launch.py robot:=panda
ros2 launch robot_description display.launch.py robot:=bb01
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
└── robot_arm/
    ├── robot_description/      # Unified robot descriptions (panda, rob, bb01)
    ├── robot_moveit_config/    # Unified MoveIt configs (panda, rob, bb01)
    ├── robot_gazebo/           # Unified Gazebo simulation
    ├── rob_bringup/            # Launch scripts
    ├── rob_mtc_demos/          # MoveIt Task Constructor demos
    └── ...
```

**Note:** Vendored packages (`moveit_task_constructor`, `warehouse_ros_mongo`) are typically kept in a separate dependencies workspace for faster builds. See installation instructions above.

## Running MTC Demos

After starting simulation with MoveIt:

```bash
ros2 launch rob_mtc_demos mtc_demos.launch.py exe:=cartesian
```

Available demos: `alternative_path_costs`, `cartesian`, `fallbacks_move_to`, `ik_clearance_cost`, `modular`

## Development

### Building Specific Packages

```bash
colcon build --packages-select robot_description robot_moveit_config
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
