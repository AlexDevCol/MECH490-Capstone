# Robot Description Architecture Guide

**Date:** January 20, 2026  
**Version:** 1.0  
**Package:** `robot_description`

This document provides detailed technical information about the unified `robot_description` package architecture, launch file structure, and usage guidelines.

---

## Table of Contents

1. [Package Structure](#package-structure)
2. [Launch File Architecture](#launch-file-architecture)
3. [Robot File Organization](#robot-file-organization)
4. [Path Resolution](#path-resolution)
5. [Usage Examples](#usage-examples)
6. [Adding a New Robot](#adding-a-new-robot)
7. [Troubleshooting](#troubleshooting)

---

## Package Structure

### Directory Layout

```
robot_description/
├── package.xml                    # Package manifest
├── CMakeLists.txt                 # Build configuration
│
├── robots/                        # Robot-specific files
│   ├── panda/
│   │   ├── urdf/
│   │   │   ├── panda.urdf.xacro  # Main URDF file
│   │   │   ├── panda.urdf        # Compiled URDF (optional)
│   │   │   └── control/          # ROS2 control configs
│   │   │       ├── gazebo_sim_ros2_control.urdf.xacro
│   │   │       └── panda_ros2_control.urdf.xacro
│   │   └── meshes/
│   │       ├── visual/            # Visual mesh files (.dae)
│   │       └── collision/        # Collision mesh files (.stl)
│   │
│   ├── rob/
│   │   ├── urdf/
│   │   │   ├── rob.urdf.xacro
│   │   │   ├── control/
│   │   │   └── sensors/          # Sensor definitions
│   │   │       └── intel_rgbd_cam_d435.urdf.xacro
│   │   └── meshes/
│   │       ├── *.stl             # Robot meshes
│   │       └── d435/              # Camera sensor meshes
│   │
│   └── bb01/
│       ├── urdf/
│       │   └── bb01.urdf.xacro
│       └── meshes/
│           └── *.STL              # Robot meshes
│
├── launch/
│   ├── robot_state_publisher.launch.py  # Full parametric launch file
│   └── display.launch.py                  # Quick display with joint GUI
│
└── rviz/
    └── display.rviz               # Default RViz configuration
```

### Naming Conventions

- **Robot directories:** Lowercase (e.g., `panda`, `rob`, `bb01`)
- **URDF files:** `<robot_name>.urdf.xacro` (e.g., `panda.urdf.xacro`)
- **Mesh paths:** Use `package://robot_description/robots/<robot>/meshes/...`

---

## Launch File Architecture

### Overview

The package provides two parametric launch files that dynamically load any robot based on the `robot:=` argument:

1. **`robot_state_publisher.launch.py`** - Full-featured launch file with all options
2. **`display.launch.py`** - Simplified launch file for quick visualization with joint GUI

Both use ROS 2 launch system features to resolve paths at runtime.

### Key Components

#### 1. Launch Arguments

```python
ARGUMENTS = [
    DeclareLaunchArgument(
        'robot',
        default_value='rob',
        choices=['panda', 'rob', 'bb01'],
        description='Robot to load (panda, rob, or bb01)'
    ),
    DeclareLaunchArgument('add_world', default_value='true', ...),
    DeclareLaunchArgument('use_camera', default_value='false', ...),
    DeclareLaunchArgument('use_gazebo', default_value='false', ...),
]
```

#### 2. OpaqueFunction for Runtime Configuration

The launch file uses `OpaqueFunction` to resolve robot-specific paths at runtime:

```python
def configure_launch(context):
    """Configure launch description based on robot selection."""
    robot_val = LaunchConfiguration('robot').perform(context)
    
    # Build URDF path dynamically
    urdf_file = os.path.join(
        pkg_share_description,
        'robots',
        robot_val,
        'urdf',
        f'{robot_val}.urdf.xacro'
    )
    
    # ... configure nodes based on robot
    return [node1, node2, ...]
```

**Why OpaqueFunction?**
- Allows runtime evaluation of `LaunchConfiguration` values
- Enables dynamic path construction based on robot selection
- Provides flexibility for robot-specific configurations

#### 3. Path Resolution Flow

```
User Input: robot:=panda
    ↓
LaunchConfiguration('robot').perform(context)
    ↓
robot_val = 'panda'
    ↓
Path Construction:
    robots/panda/urdf/panda.urdf.xacro
    ↓
URDF Loaded with xacro
    ↓
Robot State Publisher Node
```

#### 4. Robot Description Generation

```python
robot_description_content = ParameterValue(Command([
    'xacro', ' ', urdf_model, ' ',
    'robot_name:=', robot_name, ' ',
    'add_world:=', LaunchConfiguration('add_world'), ' ',
    'use_camera:=', LaunchConfiguration('use_camera'), ' ',
    'use_gazebo:=', LaunchConfiguration('use_gazebo'), ' ',
]), value_type=str)
```

This command:
1. Runs `xacro` to process the URDF file
2. Passes robot-specific arguments
3. Generates the robot description XML
4. Passes it to `robot_state_publisher` node

---

## Robot File Organization

### URDF File Structure

Each robot's URDF file should follow this pattern:

```xml
<?xml version="1.0"?>
<robot name="<robot_name>" xmlns:xacro="http://www.ros.org/wiki/xacro">
  
  <xacro:arg name="robot_name" default="<robot_name>"/>
  <xacro:arg name="use_gazebo" default="true"/>
  <xacro:arg name="use_camera" default="false"/>
  <xacro:arg name="add_world" default="true"/>
  
  <!-- Robot links and joints -->
  
  <!-- Mesh references use new path structure -->
  <mesh filename="package://robot_description/robots/<robot>/meshes/..."/>
  
  <!-- Control plugins -->
  <xacro:include filename="$(find robot_description)/robots/<robot>/urdf/control/..."/>
  
</robot>
```

### Mesh Path Format

**Standard Format:**
```xml
<mesh filename="package://robot_description/robots/<robot>/meshes/<path_to_mesh>"/>
```

**Examples:**
- Panda visual: `package://robot_description/robots/panda/meshes/visual/link0.dae`
- Panda collision: `package://robot_description/robots/panda/meshes/collision/link0.stl`
- Rob mesh: `package://robot_description/robots/rob/meshes/base_link.stl`
- Rob sensor: `package://robot_description/robots/rob/meshes/d435/visual/d435.stl`

### Xacro Include Paths

**Control Plugins:**
```xml
<xacro:include filename="$(find robot_description)/robots/<robot>/urdf/control/gazebo_sim_ros2_control.urdf.xacro"/>
```

**Sensors:**
```xml
<xacro:include filename="$(find robot_description)/robots/<robot>/urdf/sensors/<sensor>.urdf.xacro"/>
```

---

## Path Resolution

### How Paths Are Resolved

1. **Package Share Directory:**
   ```python
   pkg_share_description = FindPackageShare('robot_description').find('robot_description')
   ```
   Returns: `/opt/ros/humble/share/robot_description` (after install)

2. **URDF Path Construction:**
   ```python
   urdf_file = os.path.join(
       pkg_share_description,      # /.../share/robot_description
       'robots',                    # /.../robots
       robot_val,                   # /.../panda
       'urdf',                      # /.../urdf
       f'{robot_val}.urdf.xacro'    # /.../panda.urdf.xacro
   )
   ```

3. **Final Path:**
   ```
   /opt/ros/humble/share/robot_description/robots/panda/urdf/panda.urdf.xacro
   ```

### Package URI Resolution

When URDF files use `package://robot_description/...`, ROS 2 resolves this to:
- **Source:** `src/robot_arm/robot_description/...`
- **Install:** `install/robot_description/share/robot_description/...`

---

## Usage Examples

### Basic Usage

**Full-featured launch (robot_state_publisher.launch.py):**
```bash
# Launch with default robot (rob)
ros2 launch robot_description robot_state_publisher.launch.py

# Launch specific robot
ros2 launch robot_description robot_state_publisher.launch.py robot:=panda
ros2 launch robot_description robot_state_publisher.launch.py robot:=bb01
```

**Quick display with joint GUI (display.launch.py):**
```bash
# Launch any robot with simplified interface
ros2 launch robot_description display.launch.py robot:=panda
ros2 launch robot_description display.launch.py robot:=rob
ros2 launch robot_description display.launch.py robot:=bb01
```

### With Options

```bash
# Launch without RViz
ros2 launch robot_description robot_state_publisher.launch.py robot:=panda use_rviz:=false

# Launch with Gazebo simulation mode
ros2 launch robot_description robot_state_publisher.launch.py robot:=rob use_gazebo:=true use_sim_time:=true

# Launch with camera enabled
ros2 launch robot_description robot_state_publisher.launch.py robot:=rob use_camera:=true

# Launch without world link
ros2 launch robot_description robot_state_publisher.launch.py robot:=panda add_world:=false
```

### Available Arguments

| Argument | Default | Choices | Description |
|----------|---------|---------|-------------|
| `robot` | `rob` | `panda`, `rob`, `bb01` | Robot to load |
| `robot_name` | `robot` value | Any string | Robot name (defaults to robot) |
| `add_world` | `true` | `true`, `false` | Add world link |
| `use_camera` | `false` | `true`, `false` | Enable RGBD camera |
| `use_gazebo` | `false` | `true`, `false` | Gazebo simulation mode |
| `use_rviz` | `true` | `true`, `false` | Launch RViz |
| `use_sim_time` | `false` | `true`, `false` | Use simulation time |
| `jsp_gui` | `true` | `true`, `false` | Use joint state publisher GUI |
| `urdf_model` | Auto | File path | Override URDF path |
| `rviz_config_file` | Auto | File path | Override RViz config |

---

## Adding a New Robot

### Step-by-Step Guide

#### 1. Create Robot Directory

```bash
mkdir -p src/robot_arm/robot_description/robots/new_robot/{urdf,meshes}
```

#### 2. Add URDF File

Create `robots/new_robot/urdf/new_robot.urdf.xacro`:

```xml
<?xml version="1.0"?>
<robot name="new_robot" xmlns:xacro="http://www.ros.org/wiki/xacro">
  
  <xacro:arg name="robot_name" default="new_robot"/>
  <xacro:arg name="use_gazebo" default="true"/>
  <xacro:arg name="use_camera" default="false"/>
  <xacro:arg name="add_world" default="true"/>
  
  <!-- Your robot definition -->
  <link name="base_link">
    <visual>
      <geometry>
        <mesh filename="package://robot_description/robots/new_robot/meshes/base.stl"/>
      </geometry>
    </visual>
  </link>
  
</robot>
```

#### 3. Add Meshes

Place mesh files in `robots/new_robot/meshes/` and reference them using:
```xml
<mesh filename="package://robot_description/robots/new_robot/meshes/<mesh_file>"/>
```

#### 4. Update Launch File

Add `'new_robot'` to the choices list:

```python
DeclareLaunchArgument(
    'robot',
    default_value='rob',
    choices=['panda', 'rob', 'bb01', 'new_robot'],  # Add here
    description='Robot to load'
)
```

#### 5. Test

```bash
colcon build --packages-select robot_description
ros2 launch robot_description robot_state_publisher.launch.py robot:=new_robot
```

---

## Troubleshooting

### Common Issues

#### 1. "Package 'robot_description' not found"

**Solution:**
```bash
# Build the package
colcon build --packages-select robot_description

# Source the workspace
source install/setup.bash
```

#### 2. "URDF file not found"

**Check:**
- URDF file exists at `robots/<robot>/urdf/<robot>.urdf.xacro`
- File naming matches robot name exactly
- Package is built and installed

#### 3. "Mesh file not found"

**Check:**
- Mesh path in URDF uses `package://robot_description/robots/<robot>/meshes/...`
- Mesh file exists at the specified path
- File extension matches (.stl, .dae, etc.)

#### 4. "Robot name mismatch"

**Solution:**
- Ensure `robot_name` argument matches robot name in URDF
- Default behavior: `robot_name` = `robot` argument value

#### 5. "Failed to convert... using yaml rules: yaml.safe_load() failed"

**Cause:** Missing `value_type=str` in `ParameterValue` when using `Command` substitution.

**Solution:**
```python
# Incorrect (causes YAML parsing error)
robot_description = ParameterValue(
    Command(['xacro ', LaunchConfiguration('model')])
)

# Correct
robot_description = ParameterValue(
    Command(['xacro ', LaunchConfiguration('model')]),
    value_type=str
)
```

#### 6. "Xacro file not processing correctly"

**Cause:** URDF file is plain XML, not proper xacro format.

**Solution:** Ensure xacro files have:
- `xmlns:xacro` namespace: `<robot name="robot" xmlns:xacro="http://www.ros.org/wiki/xacro">`
- Xacro arguments: `<xacro:arg name="add_world" default="true"/>`
- Conditional blocks: `<xacro:if value="$(arg add_world)">...</xacro:if>`

#### 7. "Duplicate package names not supported"

**Cause:** Multiple packages with the same name in `package.xml`.

**Solution:** Ensure each package has a unique name in its `package.xml` file. Check for copy-paste errors where package names weren't updated.

### Debug Commands

```bash
# Check package installation
ros2 pkg prefix robot_description

# List available robots
ls src/robot_arm/robot_description/robots/

# Verify URDF file
xacro src/robot_arm/robot_description/robots/panda/urdf/panda.urdf.xacro

# Check launch file syntax
python3 src/robot_arm/robot_description/launch/robot_state_publisher.launch.py
```

---

## Architecture Benefits

### Before (Duplicated Packages)

- 3 separate packages
- 3 nearly identical launch files
- Code duplication
- Maintenance burden

### After (Unified Package)

- 1 unified package
- 1 parametric launch file
- No code duplication
- Easy to add new robots

### Metrics

- **Code Reduction:** ~66% reduction in launch file code
- **Maintenance:** Single point of update for all robots
- **Extensibility:** Adding robot = adding directory + updating choices list

---

## Related Documentation

- [Phase 1 Summary](./phase1-summary.md)
- [Parametrization Roadmap](../parametrization-roadmap.md)
- [Sprint Plan](../Plan.md)

---

**Last Updated:** January 20, 2026 (Phase 1.5 Testing Complete)  
**Maintainer:** MECH490-Capstone Team
