# BB01 Controller Loading Debug Session

**Date:** January 2026  
**Issue:** BB01 robot fails to load `joint_state_broadcaster` controller in Gazebo simulation, preventing RViz transforms from working.

## Current Status

**Status:** IN PROGRESS - Controller loading mechanism implemented but error persists

**Current Error:**
```
[ERROR] [controller_manager]: Caught exception of type : N6rclcpp10exceptions22RCLInvalidROSArgsErrorE 
while initializing controller 'joint_state_broadcaster': failed to parse arguments: 
Couldn't parse params file: '--params-file --ros-args'. 
Error: Error opening YAML file, at ./src/parser.c:271, at ./src/rcl/arguments.c:415
[ros2-7] Failed loading controller joint_state_broadcaster check controller_manager logs
[ERROR] [ros2-7]: process has died [pid 36387, exit code 1, cmd 'ros2 control load_controller --set-state active joint_state_broadcaster'].
```

## Problem Description

When launching `bb01` robot in Gazebo simulation:
- ✅ Robot spawns correctly and stands upright in Gazebo
- ✅ URDF/XACRO files are correctly processed
- ✅ Gazebo plugin (`gz_ros2_control`) loads successfully
- ❌ `joint_state_broadcaster` controller fails to load
- ❌ RViz shows "failure to gather transform" errors
- ❌ No joint states published to `/joint_states` topic

**Working Robots for Comparison:**
- `panda` - Works correctly
- `rob` - Works correctly (used as primary reference)

## Root Cause Analysis

### Key Differences Between `rob` and `bb01`

1. **Controller Loading Mechanism:**
   - `rob`: Uses dedicated launch file `rob_moveit_config/launch/load_ros2_controllers.launch.py`
   - `bb01`: Initially had inline controller loading in `simulation.launch.py`

2. **MoveIt Configuration:**
   - `rob`: Has dedicated `rob_moveit_config` package
   - `bb01`: No MoveIt config (MoveIt package is `None`)

3. **YAML Configuration Structure:**
   - `rob`: `ros2_controllers.yaml` does NOT have `use_sim_time` in `controller_manager.ros__parameters`
   - `bb01`: Initially had `use_sim_time: true` in `controller_manager.ros__parameters` (removed)

4. **Gazebo Plugin Configuration:**
   - `rob`: Simple plugin config without `<controller_manager_prefix_node_name>` tag
   - `bb01`: Initially had extra `<controller_manager_prefix_node_name>` tag (removed)

## Hypotheses Tested

### Hypothesis A: Controller Loading Method
**Theory:** The `Node` spawner approach vs `ExecuteProcess` CLI command behaves differently.

**Tested:**
- ✅ Switched from `Node(package='controller_manager', executable='spawner')` to `ExecuteProcess` with `ros2 control load_controller --set-state active joint_state_broadcaster`
- ✅ Matched exact command format used by `rob`

**Result:** CONFIRMED - This was necessary but not sufficient. Error persists.

### Hypothesis B: Missing Dedicated Launch File
**Theory:** `bb01` needs its own `load_ros2_controllers.launch.py` file like `rob` has, rather than inline controller loading.

**Tested:**
- ✅ Created `robot_description/robots/bb01/launch/load_ros2_controllers.launch.py`
- ✅ Mirrored structure of `rob_moveit_config/launch/load_ros2_controllers.launch.py`
- ✅ Updated `simulation.launch.py` to use `IncludeLaunchDescription` for `bb01` (same pattern as `rob`)

**Result:** CONFIRMED - Architecture now matches `rob`, but error persists.

### Hypothesis C: YAML Configuration Issues
**Theory:** The `ros2_controllers.yaml` file structure or content is causing parsing errors.

**Tested:**
- ✅ Removed `use_sim_time: true` from `controller_manager.ros__parameters` (matching `rob`)
- ✅ Removed redundant root-level `joint_state_broadcaster` section that caused YAML parsing errors
- ✅ Matched YAML structure exactly to `rob`'s format
- ✅ Removed `velocity` from `state_interfaces` in `arm_controller` (matching `rob`)

**Result:** PARTIALLY CONFIRMED - YAML structure issues were fixed (Gazebo no longer crashes), but controller loading error persists.

### Hypothesis D: Gazebo Plugin Configuration
**Theory:** Extra tags or parameters in the Gazebo plugin configuration cause issues.

**Tested:**
- ✅ Removed `<controller_manager_prefix_node_name>controller_manager</controller_manager_prefix_node_name>` tag
- ✅ Simplified plugin config to match `rob` exactly

**Result:** CONFIRMED - Plugin config now matches `rob`, but error persists.

### Hypothesis E: File Installation Issues
**Theory:** Stale build artifacts or incorrect file installation paths.

**Tested:**
- ✅ Performed clean rebuilds: `rm -rf build/robot_description install/robot_description`
- ✅ Verified all files are correctly installed in `install/robot_description/share/robot_description/robots/bb01/`
- ✅ Confirmed launch file exists at correct path

**Result:** CONFIRMED - All files are correctly installed.

## Changes Made

### Files Created
1. **`src/robot_arm/robot_description/robots/bb01/launch/load_ros2_controllers.launch.py`**
   - Dedicated controller loading launch file for `bb01`
   - Mirrors `rob_moveit_config/launch/load_ros2_controllers.launch.py` structure
   - Uses `ExecuteProcess` with `ros2 control load_controller --set-state active`
   - Includes 10-second `TimerAction` delay (matching `rob`)

### Files Modified

1. **`src/robot_arm/robot_gazebo/launch/simulation.launch.py`**
   - Updated `else` block to use `IncludeLaunchDescription` for `bb01`'s dedicated launch file
   - Removed inline controller loading code
   - Now matches `rob`'s controller loading pattern exactly

2. **`src/robot_arm/robot_description/robots/bb01/config/ros2_controllers.yaml`**
   - Removed `use_sim_time: true` from `controller_manager.ros__parameters`
   - Removed redundant root-level `joint_state_broadcaster` section
   - Removed `velocity` from `arm_controller.state_interfaces`
   - Matched structure exactly to `rob`'s `ros2_controllers.yaml`

3. **`src/robot_arm/robot_description/robots/bb01/urdf/control/gazebo_sim_ros2_control.urdf.xacro`**
   - Removed `<controller_manager_prefix_node_name>` tag
   - Simplified to match `rob`'s plugin configuration exactly

4. **`src/robot_arm/robot_description/robots/bb01/urdf/control/bb01_ros2_control.urdf.xacro`**
   - Added `<state_interface name="velocity"/>` to all joints (for consistency)

## Current Architecture

### Controller Loading Flow (Now Matches `rob`)

```
simulation.launch.py
  └─> configure_launch()
      └─> For bb01 (no MoveIt):
          └─> IncludeLaunchDescription(
              robots/bb01/launch/load_ros2_controllers.launch.py
          )
              └─> TimerAction(10.0s delay)
                  └─> ExecuteProcess('ros2 control load_controller --set-state active joint_state_broadcaster')
                      └─> OnProcessExit
                          └─> ExecuteProcess('ros2 control load_controller --set-state active arm_controller')
```

### File Structure

```
robot_description/
└── robots/
    └── bb01/
        ├── config/
        │   └── ros2_controllers.yaml          # Controller definitions
        ├── launch/
        │   └── load_ros2_controllers.launch.py # Controller loading (NEW)
        └── urdf/
            └── control/
                ├── bb01_ros2_control.urdf.xacro
                └── gazebo_sim_ros2_control.urdf.xacro
```

## Remaining Issue

Despite matching `rob`'s architecture exactly, the `controller_manager` is still receiving malformed arguments when trying to load `joint_state_broadcaster`. The error suggests that the `gz_ros2_control` plugin or `controller_manager` is trying to pass `--params-file --ros-args` as a single argument, which fails.

### Potential Root Causes (Not Yet Tested)

1. **Gazebo Plugin Parameter Resolution:**
   - The `$(find robot_description)` path in the plugin's `<parameters>` tag may not be resolving correctly at runtime
   - The plugin may be passing the YAML file path incorrectly to `controller_manager`

2. **Controller Manager Initialization Timing:**
   - The `controller_manager` may not be fully initialized when `ros2 control load_controller` is called
   - The 10-second delay may not be sufficient for `bb01`

3. **YAML File Path Resolution:**
   - The path `$(find robot_description)/robots/bb01/config/ros2_controllers.yaml` may not resolve correctly in the Gazebo plugin context
   - May need absolute path or different path resolution method

4. **Missing Controller Manager Node:**
   - The `gz_ros2_control` plugin should create a `controller_manager` node, but it may not be starting correctly for `bb01`

## Next Steps

1. **Verify Controller Manager Node:**
   - Check if `/controller_manager` node exists: `ros2 node list`
   - Check controller manager services: `ros2 service list | grep controller_manager`

2. **Test YAML Path Resolution:**
   - Verify the YAML file path resolves correctly in Gazebo context
   - Consider using absolute path or different path resolution

3. **Compare Runtime Behavior:**
   - Compare `ros2 node list` and `ros2 service list` outputs between `rob` and `bb01`
   - Check if `controller_manager` node appears at different times

4. **Gazebo Plugin Debugging:**
   - Enable verbose Gazebo logging to see plugin initialization
   - Check if plugin parameters are being parsed correctly

5. **Alternative Approach:**
   - Consider loading controllers via `controller_manager/spawner` node instead of CLI command
   - Or use `ros2 run controller_manager spawner` directly

## Files to Review

- `src/robot_arm/robot_description/robots/bb01/urdf/control/gazebo_sim_ros2_control.urdf.xacro` - Plugin configuration
- `src/robot_arm/robot_description/robots/bb01/config/ros2_controllers.yaml` - Controller definitions
- `src/robot_arm/robot_description/robots/bb01/launch/load_ros2_controllers.launch.py` - Controller loading
- `src/robot_arm/robot_gazebo/launch/simulation.launch.py` - Main simulation launch file

## References

- Working robot configuration: `rob_moveit_config/launch/load_ros2_controllers.launch.py`
- Working YAML: `rob_moveit_config/config/ros2_controllers.yaml`
- Working plugin: `robot_description/robots/rob/urdf/control/gazebo_sim_ros2_control.urdf.xacro`
