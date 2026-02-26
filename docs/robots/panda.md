# Panda Robot

The Franka Emika Panda is a 7 DOF collaborative robot arm used as a reference implementation in this project.

## Overview

| Property | Value |
|----------|-------|
| **Manufacturer** | Franka Emika |
| **DOF** | 7 (arm) + 2 (gripper) |
| **Payload** | 3 kg |
| **Reach** | 855 mm |
| **Status in Project** | Reference implementation |

The Panda robot serves as the reference implementation for testing new features before applying them to custom robots (Rob, BB01).

## Package Structure

The Panda robot is part of the unified `robot_description` package:

```
src/robot_arm/robot_description/
└── robots/
    └── panda/
        ├── urdf/
        │   ├── panda.urdf.xacro           # Main robot description
        │   ├── panda.urdf                 # Generated static URDF
        │   ├── panda_gazebo.xacro         # Gazebo-specific configuration
        │   ├── panda.ros2_control.xacro   # ros2_control interface
        │   └── control/
        │       ├── gazebo_sim_ros2_control.urdf.xacro
        │       ├── panda_ros2_control.urdf.xacro
        │       └── panda_hand.ros2_control.xacro
        └── meshes/
            ├── visual/                    # DAE files for visualization
            └── collision/                 # STL files for collision
```

MoveIt configuration is in the unified `robot_moveit_config` package:

```
src/robot_arm/robot_moveit_config/
└── robots/
    └── panda/
        └── config/
            ├── panda.srdf
            ├── kinematics.yaml
            ├── joint_limits.yaml
            └── ...
```

## URDF Structure

### Joint Configuration

| Joint | Type | Axis | Limits (rad) | Effort (Nm) | Velocity (rad/s) |
|-------|------|------|--------------|-------------|------------------|
| panda_joint1 | revolute | Z | [-2.97, 2.97] | 87 | 2.39 |
| panda_joint2 | revolute | Z | [-1.83, 1.83] | 87 | 2.39 |
| panda_joint3 | revolute | Z | [-2.97, 2.97] | 87 | 2.39 |
| panda_joint4 | revolute | Z | [-3.14, 0.09] | 87 | 2.39 |
| panda_joint5 | revolute | Z | [-2.97, 2.97] | 12 | 2.87 |
| panda_joint6 | revolute | Z | [-0.09, 3.82] | 12 | 2.87 |
| panda_joint7 | revolute | Z | [-2.97, 2.97] | 12 | 2.87 |
| panda_finger_joint1 | prismatic | Y | [0, 0.04] | 20 | 0.2 |
| panda_finger_joint2 | prismatic | -Y | [0, 0.04] | 20 | 0.2 |

### Link Hierarchy

```
world
└── panda_link0 (base)
    └── panda_link1
        └── panda_link2
            └── panda_link3
                └── panda_link4
                    └── panda_link5
                        └── panda_link6
                            └── panda_link7
                                └── panda_link8
                                    └── panda_hand
                                        ├── panda_leftfinger
                                        └── panda_rightfinger
```

### Xacro Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `robot_name` | `panda` | Robot name prefix |
| `use_gazebo` | `true` | Include Gazebo plugins |
| `use_camera` | `false` | Include RGBD camera |
| `add_world` | `true` | Add world link as root |

## MoveIt Configuration

Located in `src/robot_arm/robot_moveit_config/robots/panda/config/`

### Planning Groups

| Group | Joints | Purpose |
|-------|--------|---------|
| `panda_arm` | joints 1-7 | Arm motion planning |
| `panda_hand` | finger joints | Gripper control |
| `panda_arm_hand` | all joints | Combined planning |

### End Effector

- **Name:** `panda_hand`
- **Parent Link:** `panda_link8`
- **Parent Group:** `panda_arm`

### Planning Pipelines

| Pipeline | Description |
|----------|-------------|
| OMPL | Sampling-based planners (RRT, PRM, etc.) |
| Pilz | Industrial motion planner (PTP, LIN, CIRC) |
| STOMP | Stochastic trajectory optimization |

### Kinematics

- **Solver:** KDLKinematicsPlugin
- **Tip Link:** `panda_link8`
- **Search Resolution:** 0.005
- **Timeout:** 0.05s

## ros2_control Configuration

### Hardware Interface (Simulation)

```xml
<ros2_control name="PandaSystem" type="system">
  <hardware>
    <plugin>gz_ros2_control/GazeboSimSystem</plugin>
  </hardware>
  <!-- Joint interfaces -->
</ros2_control>
```

### Controllers

| Controller | Type | Joints |
|------------|------|--------|
| `joint_state_broadcaster` | Broadcaster | All |
| `panda_arm_controller` | JointTrajectoryController | joints 1-7 |
| `panda_hand_controller` | JointTrajectoryController | finger joints |

## Usage

### Visualize Robot Only

```bash
ros2 launch robot_description display.launch.py robot:=panda
```

### Launch in Gazebo

```bash
ros2 launch robot_gazebo simulation.launch.py robot:=panda
```

### Launch with MoveIt

```bash
# Terminal 1
ros2 launch robot_gazebo simulation.launch.py robot:=panda use_rviz:=false

# Terminal 2 (after ~15 seconds)
ros2 launch robot_moveit_config move_group.launch.py robot:=panda
```

### Using Bringup Script

```bash
./run_script.sh
# Select robot: panda
# Select script: Gazebo And Moveit
```

## Key Differences from Rob

| Aspect | Panda | Rob |
|--------|-------|-----|
| DOF | 7 | 5 + virtual 6th |
| Gripper | Parallel jaw | Custom gear-driven |
| Mesh Format | DAE (visual), STL (collision) | STL only |
| Inertia Data | Accurate | Approximated |
| Hardware | Commercial (Franka) | 3D printed (Moveo) |

## Files Reference

### URDF Files

| File | Purpose |
|------|---------|
| `panda.urdf.xacro` | Main robot description with all links and joints |
| `panda.ros2_control.xacro` | ros2_control interface definitions |
| `control/gazebo_sim_ros2_control.urdf.xacro` | Gazebo simulation plugin |

### MoveIt Config Files

Located in `robot_moveit_config/robots/panda/config/`:

| File | Purpose |
|------|---------|
| `panda.srdf` | Semantic robot description (groups, poses) |
| `kinematics.yaml` | Kinematics solver configuration |
| `joint_limits.yaml` | Planning joint limits |
| `moveit_controllers.yaml` | MoveIt controller configuration |
| `ros2_controllers.yaml` | ros2_control controller definitions |

## Notes

- The Panda robot is well-documented by Franka Emika and MoveIt community
- Inertia values are accurate from manufacturer data
- This implementation is based on `moveit_resources_panda_description`
- Used as a baseline for testing MoveIt Task Constructor demos
