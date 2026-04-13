# MECH490 Capstone - Documentation

Welcome to the documentation for the MECH490 Capstone robotic arm control project. This ROS 2 workspace provides simulation, motion planning, and control capabilities for multiple robotic arm platforms.

## Quick Start

### Prerequisites

- Ubuntu 22.04 (Jammy)
- ROS 2 Humble
- Gazebo Fortress (via ros-gz)
- MoveIt 2

### Build the Workspace

**If you have dependencies in a separate workspace:**

```bash
# Source dependencies workspace first (if applicable)
source ~/ros2_dependencies_ws/install/setup.bash

# Build main workspace
cd ~/Capstone/MECH490-Capstone
colcon build --symlink-install
source install/setup.bash
```

**If all packages are in this workspace:**

```bash
cd ~/Capstone/MECH490-Capstone
colcon build --symlink-install
source install/setup.bash
```

**Note:** For faster builds, consider moving vendored packages (`moveit_task_constructor`, `warehouse_ros_mongo`) to a separate workspace. See the main [README.md](../README.md) for setup instructions.

### Launch Simulation

**Option 1: Using the launcher script**
```bash
./run_script.sh
# Select from the menu (e.g., Rob Gazebo And Moveit)
```

**Option 2: Direct launch commands**

For any robot (Rob, Panda, or BB01):
```bash
# Terminal 1: Launch Gazebo simulation
ros2 launch robot_gazebo simulation.launch.py robot:=rob

# Terminal 2: Launch MoveIt (after Gazebo is ready, ~15s)
ros2 launch robot_moveit_config move_group.launch.py robot:=rob
```

Replace `robot:=rob` with `robot:=panda` or `robot:=bb01` for other robots.

### Visualize Robot Only (No Simulation)

```bash
# Any robot
ros2 launch robot_description display.launch.py robot:=rob
ros2 launch robot_description display.launch.py robot:=panda
ros2 launch robot_description display.launch.py robot:=bb01
```

---

## Package Overview

| Package | Description |
|---------|-------------|
| `robot_description` | Unified robot description package containing URDF, meshes, and visualization launch files for all robots (panda, rob, bb01) |
| `robot_moveit_config` | Unified MoveIt 2 configuration package for all robots (panda, rob, bb01) |
| `robot_gazebo` | Gazebo simulation worlds and unified launch files for all robots |
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
- [MoveIt Servo GUI](development/moveit-servo-gui.md) - Tkinter GUI for real-time servo jog control with pause/resume

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
ros2 launch robot_description display.launch.py robot:=rob
```

### Check Robot URDF

```bash
# Parse and check URDF for errors
ros2 run xacro xacro src/robot_arm/robot_description/robots/rob/urdf/rob.urdf.xacro
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

The project uses a unified parametric architecture where all robots share common launch files. See the [Parametrization Roadmap](development/parametrization-roadmap.md) for details on the architecture and [Adding a New Robot](development/adding-new-robot.md) for instructions on integrating new robots.
