# Rob Robot (BCN3D Moveo-based)

Rob is a custom robotic arm based on the BCN3D Moveo open-source design, modified for the MECH490 Capstone project.

## Overview

| Property | Value |
|----------|-------|
| **Base Design** | BCN3D Moveo |
| **DOF** | 5 physical + 1 virtual |
| **Construction** | 3D printed |
| **Gripper** | Custom gear-driven parallel gripper |
| **Status in Project** | Current capstone robot (to be replaced by BB01) |

## BCN3D Moveo Background

The BCN3D Moveo is an open-source robotic arm designed for education and prototyping:
- Designed by BCN3D Technologies
- Fully 3D printable
- Stepper motor driven
- Arduino-based control

Our "Rob" implementation extends the base design with:
- ros2_control integration
- MoveIt 2 motion planning
- Gazebo simulation
- Custom gripper mechanism

## Package Structure

```
src/robot_arm/rob_description/
├── urdf/
│   ├── rob.urdf.xacro              # Main robot description
│   ├── rob.urdf                    # Generated static URDF
│   ├── rob_gazebo.xacro            # Gazebo-specific configuration
│   ├── rob_ros2_control.xacro      # ros2_control interface
│   ├── control/
│   │   ├── gazebo_sim_ros2_control.urdf.xacro
│   │   └── rob_ros2_control.urdf.xacro
│   └── sensors/
│       └── intel_rgbd_cam_d435.urdf.xacro  # Optional camera
├── meshes/                         # STL mesh files
├── launch/
│   ├── display.launch.py
│   └── robot_state_publisher.launch.py
└── rviz/
    ├── display.rviz
    └── display2.rviz
```

## URDF Structure

### Joint Configuration

| Joint | Type | Axis | Limits (rad) | Effort (Nm) | Velocity (rad/s) |
|-------|------|------|--------------|-------------|------------------|
| joint1 | revolute | Z | [-1.57, 1.57] | 10 | 10 |
| joint2 | revolute | X | [-1.57, 1.57] | 10 | 10 |
| joint3 | revolute | -X | [-1.57, 1.57] | 10 | 10 |
| joint4 | revolute | -Z | [-1.57, 1.57] | 10 | 10 |
| joint5 | revolute | -X | [-1.57, 1.57] | 10 | 10 |
| virtual_joint6 | revolute | Z | [-3.14, 3.14] | 100 | 10 |

### Gripper Joints (Mimic)

| Joint | Type | Mimic | Multiplier |
|-------|------|-------|------------|
| joint_L_gear | revolute | joint_R_gear | -1 |
| joint_L_arm | revolute | joint_R_gear | 1 |
| joint_R_gear | revolute | (actuated) | - |
| joint_R_arm | revolute | joint_R_gear | -1 |
| joint_L_pivot | revolute | joint_R_gear | -1 |
| joint_R_pivot | revolute | joint_R_gear | 1 |

### Link Hierarchy

```
world
└── base_link
    └── link1
        └── link2
            └── link3
                └── link4
                    └── link5
                        ├── virtual_link6_tip
                        ├── link_L_gear → link_L_arm
                        ├── link_R_gear → link_R_arm
                        ├── link_L_pivot
                        └── link_R_pivot
```

### Virtual 6th Joint

The Rob robot has only 5 physical DOF, but many motion planning algorithms (particularly IK solvers) work better with 6 DOF. A **virtual 6th joint** is added:

```xml
<link name="virtual_link6_tip">
  <inertial>
    <mass value="1e-6" />
    <inertia ixx="1e-9" ixy="0" ixz="0" iyy="1e-9" iyz="0" izz="1e-9" />
  </inertial>
</link>

<joint name="virtual_joint6" type="revolute">
  <parent link="link5"/>
  <child link="virtual_link6_tip"/>
  <axis xyz="0 0 1"/>
  <limit lower="-3.14159" upper="3.14159" effort="100" velocity="10"/>
</joint>
```

This virtual joint:
- Has negligible mass and inertia
- Rotates around link5's Z-axis
- Allows IK solvers to find valid solutions more easily
- Is not physically actuated on real hardware

### Xacro Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `robot_name` | `rob` | Robot name prefix |
| `use_gazebo` | `true` | Include Gazebo plugins |
| `use_camera` | `false` | Include Intel D435 camera |
| `add_world` | `true` | Add world link as root |
| `virtual_joint` | `true` | Include virtual 6th joint |

## MoveIt Configuration

Located in `src/robot_arm/rob_moveit_config/`

### Planning Groups

| Group | Joints | Purpose |
|-------|--------|---------|
| `rob_arm` | joints 1-5 + virtual_joint6 | Arm motion planning |
| `rob_hand` | joint_R_gear | Gripper control |

### End Effector

- **Name:** `rob_hand`
- **Parent Link:** `link5`
- **Parent Group:** `rob_arm`

### Planning Pipelines

| Pipeline | Description |
|----------|-------------|
| OMPL | Sampling-based planners |
| Pilz | Industrial motion planner |
| STOMP | Stochastic trajectory optimization |

### Kinematics

- **Solver:** KDLKinematicsPlugin
- **Tip Link:** `virtual_link6_tip`
- **Search Resolution:** 0.005

## ros2_control Configuration

### Hardware Interface (Simulation)

```xml
<ros2_control name="RobSystem" type="system">
  <hardware>
    <plugin>gz_ros2_control/GazeboSimSystem</plugin>
  </hardware>
</ros2_control>
```

### Controllers

| Controller | Type | Joints |
|------------|------|--------|
| `joint_state_broadcaster` | Broadcaster | All |
| `joint_trajectory_controller` | JointTrajectoryController | arm joints |

## Hardware Interface (Real Robot)

The real Rob robot uses Arduino-based control:

### Arduino Package

Located in `src/robot_arm/rob_arduino/`

- **Communication:** Serial over USB
- **Protocol:** Custom commands for joint positions
- **Motors:** Stepper motors with drivers

### Physical Setup

1. Arduino Mega 2560
2. Stepper motor drivers (A4988/DRV8825)
3. NEMA 17 stepper motors (base, shoulder, elbow)
4. Smaller steppers for wrist and gripper

## Usage

### Visualize Robot Only

```bash
ros2 launch rob_description display.launch.py
```

### Launch in Gazebo

```bash
ros2 launch rob_gazebo rob.gazebo.launch.py
```

### Launch with MoveIt

```bash
# Terminal 1
ros2 launch rob_gazebo rob.gazebo.launch.py use_rviz:=false

# Terminal 2 (after ~15 seconds)
ros2 launch rob_moveit_config move_group.launch.py
```

### Using Bringup Script

```bash
./run_script.sh
# Select "Rob Gazebo And Moveit"
```

### Run MTC Demos

```bash
# After simulation is running
ros2 launch rob_mtc_demos mtc_demos.launch.py exe:=cartesian
```

## Gripper Mechanism

The Rob gripper uses a gear-driven parallel mechanism:

```
link5
├── link_L_gear ─────┬──── link_L_arm
│   (mimic: -1)     │     (mimic: +1)
├── joint_R_gear ───┴──── link_R_arm
│   (ACTUATED)            (mimic: -1)
├── link_L_pivot (mimic: -1)
└── link_R_pivot (mimic: +1)
```

- **Actuated Joint:** `joint_R_gear`
- **Gear Ratio:** 1:1 (mimic multiplier)
- **Motion:** Symmetric open/close

When `joint_R_gear` opens (positive rotation):
- `joint_L_gear` closes (negative)
- Arms extend outward
- Pivots rotate symmetrically

## Known Limitations

1. **5 DOF limitation:** Cannot achieve arbitrary 6D poses
2. **Virtual joint:** Not physically actuated, causes slight IK/execution mismatch
3. **Inertia approximation:** Values derived from mesh, not measured
4. **Gripper mimic joints:** Gazebo may not perfectly simulate mimic behavior

## Files Reference

### URDF Files

| File | Purpose |
|------|---------|
| `rob.urdf.xacro` | Main robot with all links, joints, and gripper |
| `rob_ros2_control.xacro` | Hardware interface definitions |
| `sensors/intel_rgbd_cam_d435.urdf.xacro` | Optional depth camera |

### MoveIt Config Files

| File | Purpose |
|------|---------|
| `config/rob.srdf` | Planning groups and end effector |
| `config/kinematics.yaml` | KDL solver configuration |
| `config/joint_limits.yaml` | Planning limits |
| `config/moveit_controllers.yaml` | MoveIt controller config |

## Migration to BB01

Rob is being replaced by BB01 as the main capstone robot. See [BB01 documentation](bb01.md) for the new robot and [Parametrization Roadmap](../development/parametrization-roadmap.md) for the transition plan.
