# MoveIt Servo GUI Implementation

**Date:** February 2026  
**Status:** ✅ Complete and Tested

## Overview

This document describes the implementation of a Tkinter-based graphical user interface (GUI) for real-time MoveIt Servo jog control, along with the fix for MoveIt state synchronization issues when switching between servo control and motion planning.

## Problem Statement

### Issue 1: MoveIt State Sync
After using MoveIt Servo to move the robot via keyboard commands, MoveIt's `move_group` node would not see the updated joint positions, causing the RViz interface to appear "locked out" and preventing motion planning.

**Root Cause:** While servo is actively sending trajectory commands at 100 Hz, the `arm_controller` is "owned" by the servo node. The `FollowJointTrajectory` action server in the controller cannot accept new plans from `move_group` while it's executing servo trajectories.

**Solution:** Implement a **Pause/Resume Servo** feature that stops servo command publishing, freeing the controller for MoveIt planning. When paused, users can plan and execute motions in RViz. When resumed, servo control is restored.

### Issue 2: User Interface
The existing keyboard control (`keyboard_servo_node`) works but requires memorizing key bindings and provides no visual feedback. A graphical interface would improve usability.

**Solution:** Create a Tkinter GUI with clickable buttons, visual mode indicators, speed control, and status feedback.

---

## Architecture

### Data Flow

```
┌─────────────┐
│  Servo GUI  │
│  (Tkinter)  │
└──────┬──────┘
       │
       ├─► /servo_node/delta_twist_cmds (TwistStamped)
       ├─► /servo_node/delta_joint_cmds (JointJog)
       ├─► /servo_node/switch_command_type (Service)
       └─► /servo_node/pause_servo (Service)
              │
              ▼
       ┌──────────────┐
       │  Servo Node  │
       └──────┬───────┘
              │
              ├─► /arm_controller/joint_trajectory
              │
              ▼
       ┌──────────────┐
       │arm_controller│
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │    Gazebo    │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │joint_state_  │
       │ broadcaster │
       └──────┬───────┘
              │
              ├─► /joint_states ──► move_group
              └─► /joint_states ──► servo_node
```

### Key Components

1. **`servo_gui.py`** - Python ROS 2 node with Tkinter GUI
   - Publishes servo commands (twist/joint jog)
   - Calls servo services (mode switch, pause/resume)
   - Runs tkinter mainloop on main thread, ROS spinning on background thread

2. **`servo.sh`** - Launch script with GUI option
   - Supports `--gui` flag to launch GUI instead of keyboard node
   - Maintains backward compatibility with keyboard control

3. **MoveIt Servo Services** (provided by `moveit_servo` package):
   - `/servo_node/switch_command_type` - Switch between JOINT_JOG and TWIST modes
   - `/servo_node/pause_servo` - Pause/resume servo command publishing

---

## Implementation Details

### File: `src/robot_arm/rob_bringup/scripts/servo_gui.py`

**Key Features:**
- **Mode Switching**: Toggle between Joint Jog and Twist (Cartesian) modes
- **Joint Jog Controls**: 6 buttons (◀/▶) for each joint, continuous motion while held
- **Twist Controls**: 6 axes (Linear X/Y/Z, Roll/Pitch/Yaw) with ◀/▶ buttons
- **Pause/Resume**: Stops servo publishing to allow MoveIt planning
- **Speed Slider**: Adjustable velocity scale (0.05 → 1.0)
- **Status Bar**: Real-time mode, servo state, and frame display
- **Keyboard Shortcuts**: Same bindings as terminal keyboard node

**Technical Implementation:**
- **Threading Model**: Tkinter runs on main thread, ROS 2 spins in background daemon thread
- **Command Repeating**: Uses `tkinter.after()` to schedule repeated publishes at ~20 Hz while buttons are held
- **Service Calls**: Async service calls with callbacks to update UI state
- **Dark Theme**: Custom color palette for better visibility

**ROS 2 Topics:**
- Publishes to `/servo_node/delta_twist_cmds` (TwistStamped)
- Publishes to `/servo_node/delta_joint_cmds` (JointJog)
- Calls `/servo_node/switch_command_type` (ServoCommandType service)
- Calls `/servo_node/pause_servo` (SetBool service)

**Parameters:**
- `planning_frame` (default: "world") - Frame for command publishing
- `speed` (default: 0.5) - Velocity scale factor for all commands
- `use_sim_time` - Standard ROS 2 parameter (set via command line)

### File: `src/robot_arm/rob_bringup/scripts/servo.sh`

**Changes:**
- Added `--gui` flag support
- Updated usage documentation
- GUI launch uses direct Python execution (no `ros2 run` needed)
- Maintains full backward compatibility with keyboard control

**Usage:**
```bash
./servo.sh bb01         # Keyboard control (default)
./servo.sh bb01 --gui   # Tkinter GUI control
```

---

## Usage Guide

### Quick Start

**Option 1: Full Stack Launch (Recommended)**
```bash
cd ~/Capstone/MECH490-Capstone
source install/setup.bash
./src/robot_arm/rob_bringup/scripts/servo.sh bb01 --gui
```

This launches:
1. Gazebo simulation (15s delay)
2. MoveIt move_group (10s delay after Gazebo)
3. MoveIt Servo node (5s delay after MoveIt)
4. Servo GUI window

**Option 2: GUI Only (if stack already running)**
```bash
cd ~/Capstone/MECH490-Capstone
source install/setup.bash
python3 src/robot_arm/rob_bringup/scripts/servo_gui.py \
    --ros-args \
    -p planning_frame:=world \
    -p use_sim_time:=true \
    -p speed:=0.5
```

### GUI Controls

#### Mode Buttons
- **Joint Jog** - Switch to joint-by-joint control
- **Twist** - Switch to Cartesian (end-effector) control

#### Joint Jog Mode
- **◀ − / + ▶** buttons for each joint (joint_1 through joint_6)
- Hold button to move continuously
- Release to stop

#### Twist (Cartesian) Mode
- **Linear X/Y/Z** - Move end-effector in world frame
- **Roll/Pitch/Yaw** - Rotate end-effector about axes
- Hold button to move continuously
- Release to stop

#### Speed Control
- **Slider** - Adjust velocity scale (0.05 = slow, 1.0 = fast)
- Applies to both joint and Cartesian commands

#### Pause/Resume Servo
- **⏸ Pause Servo** (green) - Stops servo publishing, allows MoveIt planning
- **▶ Resume Servo** (red) - Resumes servo control
- **Use Case**: Pause servo → Plan motion in RViz → Execute → Resume servo

#### Keyboard Shortcuts
- `1`-`6` - Joint jog (positive) in Joint Jog mode
- `!` `@` `#` `$` `%` `^` - Joint jog (negative) in Joint Jog mode
- Arrow keys - Linear X/Y in Twist mode
- `u`/`o` - Linear Z +/- in Twist mode
- `j`/`l` - Roll (angular X) +/- in Twist mode
- `i`/`k` - Pitch (angular Y) +/- in Twist mode
- `n`/`m` - Yaw (angular Z) +/- in Twist mode
- `t` - Switch to Twist mode
- `g` - Switch to Joint Jog mode
- `p` - Toggle Pause/Resume

### Workflow: Switching Between Servo and MoveIt Planning

1. **Start with Servo Control**
   ```bash
   ./servo.sh bb01 --gui
   ```
   - Use GUI to jog robot to desired starting position

2. **Pause Servo**
   - Click **⏸ Pause Servo** button (turns red)
   - Servo stops publishing commands
   - Controller is now available for MoveIt

3. **Use MoveIt Planning in RViz**
   - Drag the interactive marker to desired pose
   - Click "Plan" → "Execute"
   - Robot moves via MoveIt trajectory execution

4. **Resume Servo**
   - Click **▶ Resume Servo** button (turns green)
   - Servo control is restored
   - Continue jogging as needed

---

## Technical Details

### Command Publishing

The GUI publishes commands at **20 Hz** while a button is held. This is implemented using `tkinter.after()`:

```python
def _send_active_cmd(self):
    cmd = self.node._active_cmd
    if cmd is None:
        return
    
    # Publish command
    if cmd["type"] == "joint":
        self.node.publish_joint_jog(cmd["axis"], cmd["direction"])
    elif cmd["type"] == "twist":
        kwargs = {cmd["axis"]: cmd["direction"]}
        self.node.publish_twist(**kwargs)
    
    # Schedule next repeat
    self.node._timer_id = self.root.after(PUBLISH_PERIOD_MS, self._send_active_cmd)
```

### Service Calls

Mode switching and pause/resume use async service calls:

```python
def call_switch_mode(self, mode: int):
    req = ServoCommandType.Request()
    req.command_type = mode
    future = self.switch_mode_cli.call_async(req)
    future.add_done_callback(self._on_switch_mode_done)
```

### Threading

ROS 2 spinning runs in a background daemon thread to avoid blocking the tkinter mainloop:

```python
def main():
    rclpy.init()
    node = ServoGuiNode()
    
    # Spin ROS 2 in background thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()
    
    # Run tkinter on main thread
    gui = ServoGui(node)
    gui.run()
```

---

## Troubleshooting

### GUI Doesn't Appear
- **Check ROS 2 is sourced**: `source install/setup.bash`
- **Verify servo node is running**: `ros2 node list | grep servo`
- **Check for errors**: Look at terminal output for Python tracebacks

### Buttons Don't Move Robot
- **Verify servo node is active**: Check `/servo_node/status` topic
- **Check controller state**: `ros2 control list_controllers`
- **Ensure servo is not paused**: Status bar should show "Active" (green)

### MoveIt Still Locked After Pausing
- **Wait 1-2 seconds** after pausing for controller to release
- **Check controller state**: `ros2 control list_controllers` should show `arm_controller` as `active` and `inactive` (not executing)
- **Restart move_group** if needed: `ros2 launch robot_moveit_config move_group.launch.py robot:=bb01`

### Service Calls Fail
- **Wait for services**: GUI waits up to 10 seconds for services on startup
- **Check service availability**: `ros2 service list | grep servo`
- **Verify servo node name**: Default is `servo_node`, check with `ros2 node list`

### Keyboard Shortcuts Don't Work
- **Focus the GUI window**: Click on the window to give it keyboard focus
- **Check mode**: Some keys only work in specific modes (e.g., `1`-`6` only in Joint Jog mode)

---

## Testing

### Manual Test Checklist

- [ ] **Joint Jog**: Click and hold joint buttons, verify robot moves in Gazebo
- [ ] **Mode Switch**: Click "Twist", verify Cartesian buttons work
- [ ] **Speed Slider**: Adjust slider, verify motion speed changes
- [ ] **Keyboard Shortcuts**: Press `1`-`6`, arrows, verify commands work
- [ ] **Pause/Resume**: 
  - [ ] Pause servo → Plan in RViz → Execute → Resume servo
  - [ ] Verify MoveIt can plan while paused
  - [ ] Verify servo resumes correctly
- [ ] **Close Window**: Close GUI, verify clean shutdown

### Integration Test

```bash
# Terminal 1: Launch full stack
./servo.sh bb01 --gui

# Terminal 2: Monitor topics
ros2 topic echo /servo_node/status
ros2 topic echo /joint_states

# Terminal 3: Test MoveIt planning (after pausing servo)
ros2 run moveit_commander moveit_commander_cmdline.py
```

---

## Future Enhancements

Potential improvements:
1. **Joint State Display** - Show current joint angles in GUI
2. **End-Effector Pose Display** - Show current Cartesian pose
3. **Preset Positions** - Save/load common poses
4. **Collision Warnings** - Visual feedback when near collision
5. **Trajectory Recording** - Record and replay servo motions
6. **Multi-Robot Support** - Select robot from GUI dropdown

---

## References

- [MoveIt Servo Documentation](https://moveit.picknik.ai/main/doc/examples/realtime_servo/realtime_servo_tutorial.html)
- [ROS 2 Python Client Library (rclpy)](https://docs.ros2.org/latest/api/rclpy/index.html)
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)

---

## Files Modified/Created

### Created
- `src/robot_arm/rob_bringup/scripts/servo_gui.py` - Main GUI node
- `docs/development/moveit-servo-gui.md` - This documentation

### Modified
- `src/robot_arm/rob_bringup/scripts/servo.sh` - Added `--gui` flag support

---

## Authors

MECH490-Capstone Team  
February 2026
