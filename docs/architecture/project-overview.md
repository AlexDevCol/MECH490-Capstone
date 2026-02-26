# Project Overview

This document describes the repository structure, package organization, and overall architecture of the MECH490 Capstone robotic arm control project.

## Repository Structure

```
MECH490-Capstone/
├── assets/                          # CAD files and URDF exports
│   ├── BB01_URDF_V1/               # BB01 robot URDF from SolidWorks
│   └── CAD/                        # SolidWorks CAD files
├── build/                          # Colcon build artifacts (git-ignored)
├── install/                        # Colcon install space (git-ignored)
├── log/                            # Colcon log files (git-ignored)
├── docs/                           # Project documentation
├── src/                            # ROS 2 packages
│   ├── robot_arm/                  # Main robot packages
│   ├── moveit_task_constructor/    # MTC library (vendored)
│   └── warehouse_ros_mongo/        # MongoDB warehouse (vendored)
├── README.md                       # Project README
└── run_script.sh                   # Convenience launcher
```

## Package Categories

### Robot Description Package

The unified `robot_description` package contains robot models (URDF/Xacro), meshes, and visualization launch files for all robots.

| Package | Robots | Status |
|---------|--------|--------|
| `robot_description` | Panda, Rob, BB01 | Stable |

**Structure:**
```
robot_description/
├── robots/
│   ├── panda/     # Panda robot files
│   ├── rob/        # Rob robot files
│   └── bb01/       # BB01 robot files
├── launch/         # Parametric launch files (robot:= argument)
└── rviz/           # RViz configuration files
```

**Contents per robot:**
- `urdf/` - URDF and Xacro files
- `meshes/` - Visual and collision meshes (STL, DAE)
- `control/` - ros2_control configuration files

### MoveIt Configuration Package

The unified `robot_moveit_config` package contains motion planning configuration for all robots.

| Package | Robots |
|---------|--------|
| `robot_moveit_config` | Panda, Rob, BB01 |

**Contents:**
- `config/` - YAML configuration files (kinematics, controllers, joint limits, SRDF)
- `launch/` - MoveIt launch files (move_group, RViz, controller loading)
- `rviz/` - MoveIt-specific RViz configs

### Simulation Package

| Package | Description |
|---------|-------------|
| `robot_gazebo` | Gazebo simulation for all robots |

**Contents:**
- `launch/` - Gazebo launch files for each robot
- `worlds/` - Gazebo world files (empty, house, pick_and_place_demo, fruits)
- `models/` - Gazebo model assets
- `config/` - ROS-Gazebo bridge configuration

### Application Packages

| Package | Description |
|---------|-------------|
| `rob_mtc_demos` | MoveIt Task Constructor demonstrations |
| `rob_mtc_pick_place_demo` | Pick and place demo using MTC |
| `rob_moveit_demos` | Basic MoveIt motion planning demos |
| `rob_cpp_pkg` | C++ utility nodes |

### Infrastructure Packages

| Package | Description |
|---------|-------------|
| `rob_bringup` | Convenience scripts and system launch |
| `rob_interfaces` | Custom messages, services, and actions |
| `rob_arduino` | Arduino hardware interface |
| `rob_system_tests` | System integration tests |

### External Dependencies

**Vendored Packages (typically in separate workspace):**

| Package | Description | Location |
|---------|-------------|----------|
| `moveit_task_constructor` | MTC library for complex task planning | Separate workspace (recommended) or `src/` |
| `warehouse_ros_mongo` | MongoDB integration for motion plan storage | Separate workspace (recommended) or `src/` |

**Workspace Overlay Pattern:**

For faster builds, these packages are typically kept in a separate workspace (`~/ros2_dependencies_ws/`) and sourced as an underlay before building the main workspace. This allows you to build only your project code while still having access to the dependencies.

**Setup:**
```bash
# Create dependencies workspace
mkdir -p ~/ros2_dependencies_ws/src
# Move vendored packages there
# Build dependencies workspace
cd ~/ros2_dependencies_ws
colcon build --symlink-install
source install/setup.bash

# Then build main workspace
cd ~/Capstone/MECH490-Capstone
source ~/ros2_dependencies_ws/install/setup.bash  # Underlay first
colcon build --symlink-install
source install/setup.bash
```

---

## Build System

The project uses the standard ROS 2 Colcon build system.

### Building

**With dependencies workspace (recommended):**

```bash
# Source dependencies workspace first
source ~/ros2_dependencies_ws/install/setup.bash

# Build main workspace
cd ~/Capstone/MECH490-Capstone
colcon build --symlink-install
source install/setup.bash
```

**Without dependencies workspace:**

```bash
cd ~/Capstone/MECH490-Capstone
colcon build --symlink-install
source install/setup.bash
```

**Note:** If vendored packages are in a separate workspace, you must source that workspace before building this one.

### Building Specific Packages

```bash
colcon build --packages-select robot_description robot_moveit_config
```

### Clean Build

```bash
rm -rf build install log
colcon build --symlink-install
```

---

## External Dependencies

### ROS 2 Dependencies

- `ros2_control` - Hardware abstraction and controller manager
- `gz_ros2_control` - Gazebo-ROS 2 control integration
- `moveit` - Motion planning framework
- `ros_gz` - ROS 2 - Gazebo bridge

### System Dependencies

- Gazebo Fortress (via `ros-humble-ros-gz`)
- MongoDB (for warehouse_ros_mongo)

### Install Dependencies

```bash
cd ~/Capstone/MECH490-Capstone
rosdep install --from-paths src --ignore-src -r -y
```

---

## Key Concepts

### Robot State Publisher

Each robot description package provides a launch file that starts the `robot_state_publisher` node, which:
1. Parses the URDF/Xacro
2. Publishes the robot model to `/robot_description`
3. Publishes TF transforms based on joint states

### ros2_control Integration

The robots use `ros2_control` for hardware abstraction:
- **Gazebo**: Uses `gz_ros2_control/GazeboSimSystem` hardware interface
- **Real Hardware**: Uses custom Arduino-based interface

### MoveIt 2 Architecture

MoveIt provides:
- **move_group** node - Central motion planning server
- **Planning pipelines** - OMPL, Pilz, STOMP
- **Controller interfaces** - Trajectory execution

### MoveIt Task Constructor (MTC)

MTC enables complex, multi-stage manipulation tasks:
- Pick and place operations
- Cartesian path planning
- Fallback strategies

---

## File Naming Conventions

| Pattern | Description |
|---------|-------------|
| `*.urdf.xacro` | Main robot URDF with Xacro macros |
| `*.ros2_control.xacro` | ros2_control hardware interface definitions |
| `*_gazebo.xacro` | Gazebo-specific plugins and sensors |
| `*.launch.py` | ROS 2 launch files (Python) |
| `*.srdf` | MoveIt Semantic Robot Description |
| `*.yaml` | Configuration files |

---

## Next Steps

- [Package Relationships](package-relationships.md) - Understand package dependencies
- [Launch Flow](launch-flow.md) - Understand how launch files connect
