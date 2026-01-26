# MECH490 Capstone - Documentation

Welcome to the documentation for the MECH490 Capstone robotic arm control project. This ROS 2 workspace provides simulation, motion planning, and control capabilities for multiple robotic arm platforms.

## Quick Start

### Prerequisites

- Ubuntu 22.04 (Jammy)
- ROS 2 Humble
- Gazebo Fortress (via ros-gz)
- MoveIt 2

### Build the Workspace

```bash
cd ~/Capstone/MECH490-Capstone
colcon build --symlink-install
source install/setup.bash
```

### Launch Simulation

**Option 1: Using the launcher script**
```bash
./run_script.sh
# Select from the menu (e.g., Rob Gazebo And Moveit)
```

**Option 2: Direct launch commands**

For the Rob (Moveo) robot:
```bash
# Terminal 1: Launch Gazebo simulation
ros2 launch rob_gazebo rob.gazebo.launch.py

# Terminal 2: Launch MoveIt (after Gazebo is ready, ~15s)
ros2 launch rob_moveit_config move_group.launch.py
```

For the Panda robot:
```bash
# Terminal 1: Launch Gazebo simulation
ros2 launch rob_gazebo panda.gazebo.launch.py

# Terminal 2: Launch MoveIt (after Gazebo is ready, ~15s)
ros2 launch panda_moveit_config move_group.launch.py
```

### Visualize Robot Only (No Simulation)

```bash
# Rob robot
ros2 launch rob_description display.launch.py

# Panda robot
ros2 launch panda_description display.launch.py
```

---

## Package Overview

| Package | Description |
|---------|-------------|
| `panda_description` | Franka Emika Panda URDF, meshes, and visualization launch files |
| `rob_description` | Rob (Moveo-based) URDF, meshes, and visualization launch files |
| `bb01_description` | BB01 robot URDF (under construction) |
| `panda_moveit_config` | MoveIt 2 configuration for the Panda robot |
| `rob_moveit_config` | MoveIt 2 configuration for the Rob robot |
| `rob_gazebo` | Gazebo simulation worlds and launch files for all robots |
| `rob_bringup` | Convenience scripts for launching complete systems |
| `rob_arduino` | Arduino interface for real hardware control |
| `rob_interfaces` | Custom ROS 2 messages, services, and actions |
| `rob_mtc_demos` | MoveIt Task Constructor demonstration nodes |
| `rob_mtc_pick_place_demo` | Pick and place demo using MTC |
| `rob_moveit_demos` | Basic MoveIt motion planning demos |
| `rob_cpp_pkg` | C++ utility nodes |
| `rob_system_tests` | System integration tests |
| `moveit_task_constructor` | MTC library (vendored) |
| `warehouse_ros_mongo` | MongoDB warehouse for motion planning (vendored) |

---

## Documentation Index

### Architecture
- [Project Overview](architecture/project-overview.md) - Repository structure and package roles
- [Package Relationships](architecture/package-relationships.md) - Dependencies and data flow diagrams
- [Launch Flow](architecture/launch-flow.md) - Launch file hierarchy and connections

### Robots
- [Panda](robots/panda.md) - Franka Emika Panda (7 DOF) reference implementation
- [Rob (Moveo)](robots/rob-moveo.md) - BCN3D Moveo-based robot (5 DOF + virtual joint)
- [BB01](robots/bb01.md) - New 6 DOF robot (under construction)

### Development
- [Adding a New Robot](development/adding-new-robot.md) - Step-by-step guide for integrating new robots
- [Parametrization Roadmap](development/parametrization-roadmap.md) - Plan for consolidating duplicate packages

### ESP32
- [ESP32 micro-ROS Integration](esp32/README.md) - ESP32 servo control with micro-ROS

### Reference
- [Launch Arguments](reference/launch-arguments.md) - Quick reference for all launch file arguments

---

## Supported Robots

| Robot | DOF | Status | Description |
|-------|-----|--------|-------------|
| Panda | 7 | Stable | Franka Emika Panda - reference implementation |
| Rob | 5+1 | Stable | BCN3D Moveo-based with virtual 6th joint |
| BB01 | 6 | WIP | New capstone robot (will replace Rob) |

---

## Common Tasks

### Run MTC Demos

```bash
# Start simulation first
./run_script.sh  # Select "Rob Gazebo And Moveit"

# In another terminal, run MTC demo
ros2 launch rob_mtc_demos mtc_demos.launch.py exe:=cartesian
```

Available MTC demos: `alternative_path_costs`, `cartesian`, `fallbacks_move_to`, `ik_clearance_cost`, `modular`

### View Robot in RViz Only

```bash
ros2 launch rob_description display.launch.py
```

### Check Robot URDF

```bash
# Parse and check URDF for errors
ros2 run xacro xacro src/robot_arm/rob_description/urdf/rob.urdf.xacro
```

---

## Troubleshooting

### Gazebo not finding meshes
Ensure `GZ_SIM_RESOURCE_PATH` includes the install directory:
```bash
source install/setup.bash
```

### MoveIt "No motion plan found"
- Check that controllers are loaded: `ros2 control list_controllers`
- Verify robot state: `ros2 topic echo /joint_states`

### RViz not showing robot
- Ensure `robot_state_publisher` is running
- Check TF tree: `ros2 run tf2_tools view_frames`

---

## Contributing

See the [Parametrization Roadmap](development/parametrization-roadmap.md) for the planned refactoring to eliminate code duplication between robot packages.
