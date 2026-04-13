# BB01 MoveIt Debugging Session

**Date:** February 2026  
**Status:** ✅ Resolved  
**Issue:** MoveIt motion planner not loading for `bb01` robot  
**Root Cause:** High-poly collision meshes (61MB) causing `move_group` startup timeout

---

## Problem Summary

After implementing the `bb01` MoveIt configuration (Phase 1 of parametrization), the following symptoms were observed:

- ❌ RViz MotionPlanning panel showed "no motion planning library loaded"
- ❌ Planning requests failed silently
- ❌ Named states (home, hello, critical) could not be set
- ❌ Interactive marker required manual resizing to appear
- ❌ `get_planning_scene` service calls failed

The `rob` robot's MoveIt configuration worked correctly, indicating the issue was specific to `bb01`.

---

## Debugging Process

### Initial Hypotheses Tested

1. **H-A: Dual world→base_link conflict** - URDF and SRDF using different joint names
   - **Status:** ✅ Fixed (renamed `world_to_base_link` → `virtual_joint` in URDF)

2. **H-B: MoveItConfigsBuilder loading wrong URDF** - Mock components instead of GazeboSim
   - **Status:** ✅ Fixed (removed duplicate URDF from `config/`, updated `.setup_assistant`)

3. **H-E: Integer vs float in initial_positions.yaml**
   - **Status:** ✅ Fixed (changed `0` → `0.0` for all joints)

4. **H-F: move_group node crashes at startup**
   - **Status:** ⚠️ Partially confirmed (node alive but unresponsive)

5. **H-H: to_dict() not producing correct planning parameters**
   - **Status:** ❌ Rejected (logs showed correct planning pipeline structure)

6. **H-K: High-poly collision meshes causing startup timeout** ⭐ **ROOT CAUSE**
   - **Status:** ✅ Confirmed and fixed

### Diagnostic Evidence

**Runtime diagnostics revealed:**
- `ros2 node list` command **timed out** (>10 seconds)
- `ros2 service list` command **timed out** (>10 seconds)
- `/monitored_planning_scene` topic **missing** (not published)
- `get_planning_scene` service **unavailable**

**File analysis revealed:**
- `bb01` collision meshes: **61MB total** (largest: `link_5.STL` = 16MB)
- `rob` collision meshes: **8.7MB total** (largest: `link5.stl` = 3.1MB)
- **7x larger** mesh files in `bb01` compared to `rob`

**Log analysis:**
- `move_group` node started but became unresponsive during collision world initialization
- Planning scene monitor failed to initialize due to mesh processing blocking the main thread
- System latency so severe that basic ROS2 commands timed out

---

## Root Cause

The `bb01` robot's collision meshes were **extremely high-resolution** (61MB total), causing MoveIt's collision checking system to:

1. **Block the main thread** during mesh loading and convex hull generation
2. **Timeout** during planning scene initialization
3. **Prevent** the planning scene monitor from starting
4. **Make** `move_group` unresponsive to service calls

This is a **performance issue**, not a configuration issue. The MoveIt configuration was correct, but the system couldn't initialize due to computational overload.

---

## Solution

### Immediate Fix

Replaced all collision mesh geometry in `bb01.urdf.xacro` with simplified box primitives:

```xml
<!-- Before: High-poly mesh (16MB for link_5) -->
<collision>
  <geometry>
    <mesh filename="package://robot_description/robots/bb01/meshes/link_5.STL" />
  </geometry>
</collision>

<!-- After: Simplified box -->
<collision>
  <geometry>
    <box size="0.1 0.1 0.1" />
  </geometry>
</collision>
```

**Result:** MoveIt startup time reduced from **>60 seconds (timeout)** to **<5 seconds**.

### Files Modified

1. **`src/robot_arm/robot_description/robots/bb01/urdf/bb01.urdf.xacro`**
   - Replaced all `<mesh>` tags in `<collision>` blocks with `<box size="0.1 0.1 0.1"/>`
   - Added comment explaining the performance optimization

2. **`src/robot_arm/bb01_moveit_config/launch/move_group.launch.py`**
   - Removed all debug instrumentation
   - Cleaned up imports (removed `json`, `time`, `ExecuteProcess`, `TimerAction`)

### Verification

After the fix:
- ✅ Motion planning library loads correctly
- ✅ Planning requests succeed
- ✅ Named states work (home, hello, critical)
- ✅ Interactive marker appears automatically
- ✅ `get_planning_scene` service available
- ✅ All planning pipelines (OMPL, Pilz, STOMP) functional

---

## Recommendations

### Short Term (Current State)

The simplified box collision geometry is **functional for simulation** but **not accurate** for real-world collision checking. This is acceptable for:
- ✅ Development and testing
- ✅ Motion planning algorithm validation
- ✅ Trajectory execution in simulation

### Long Term (Production)

For production use, generate **low-poly convex hull meshes**:

1. **Use mesh simplification tools** (e.g., Blender, MeshLab) to reduce polygon count
2. **Target:** <500KB per mesh file (vs current 2-16MB)
3. **Generate convex hulls** for collision geometry (MoveIt can do this automatically)
4. **Keep high-poly meshes** for visual representation only

**Example workflow:**
```bash
# In Blender or MeshLab:
# 1. Import original STL
# 2. Decimate mesh (reduce to ~1000-5000 faces)
# 3. Export as collision_STL
# 4. Update URDF to use collision_STL for <collision>, original for <visual>
```

---

## Key Learnings

1. **Mesh size matters:** High-poly collision meshes can completely block MoveIt initialization
2. **Performance vs accuracy trade-off:** Simplified collision geometry is acceptable for simulation
3. **Systematic debugging:** Runtime diagnostics (node/topic/service checks) revealed the true issue
4. **Configuration was correct:** The problem wasn't in MoveIt config files, but in the robot model itself
5. **Comparison is powerful:** Comparing `bb01` (broken) with `rob` (working) quickly identified the difference

---

## Related Documentation

- [Phase 1 Summary](./phase1-summary.md) - Initial MoveIt setup for bb01
- [BB01 MoveIt Plan](./bb01_moveit_+_parametric_config_a1576f44.plan.md) - Original implementation plan
- [Architecture Guide](./architecture-guide.md) - System architecture details

---

**Last Updated:** February 2026 (Issue Resolved)
