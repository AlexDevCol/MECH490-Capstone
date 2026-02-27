#!/usr/bin/env python3
"""
Tkinter GUI for MoveIt Servo jog control.

Provides a graphical interface for real-time servo control of the robot
with joint jog, Cartesian twist, mode switching, speed control, and
servo pause/resume (to hand control back to MoveIt planning).

Usage:
    ros2 run rob_bringup servo_gui.py --ros-args -p planning_frame:=world -p use_sim_time:=true

    Or directly:
    python3 servo_gui.py --ros-args -p planning_frame:=world -p use_sim_time:=true

:author: MECH490-Capstone Team
:date: February 2026
"""

import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from control_msgs.msg import JointJog
from moveit_msgs.srv import ServoCommandType
from std_srvs.srv import SetBool

# ── Constants ────────────────────────────────────────────────────────────────
JOINT_NAMES = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
PUBLISH_RATE_HZ = 20          # How often to repeat a held command
PUBLISH_PERIOD_MS = int(1000 / PUBLISH_RATE_HZ)

# Servo command type constants (match moveit_msgs/srv/ServoCommandType)
MODE_JOINT_JOG = 0
MODE_TWIST = 1

# ── Colour palette ───────────────────────────────────────────────────────────
BG           = "#1e1e2e"
BG_SECTION   = "#2a2a3d"
FG           = "#cdd6f4"
ACCENT       = "#89b4fa"
ACCENT_HOVER = "#74c7ec"
GREEN        = "#a6e3a1"
RED          = "#f38ba8"
YELLOW       = "#f9e2af"
BTN_BG       = "#45475a"
BTN_ACTIVE   = "#585b70"


class ServoGuiNode(Node):
    """ROS 2 node that drives a tkinter GUI for MoveIt Servo jog control."""

    # ── Construction ─────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__("servo_gui_node")

        # Parameters
        self.declare_parameter("planning_frame", "world")
        self.declare_parameter("speed", 0.5)
        self.planning_frame = self.get_parameter("planning_frame").value

        # Publishers
        self.twist_pub = self.create_publisher(
            TwistStamped, "/servo_node/delta_twist_cmds", 10
        )
        self.joint_pub = self.create_publisher(
            JointJog, "/servo_node/delta_joint_cmds", 10
        )

        # Service clients
        self.switch_mode_cli = self.create_client(
            ServoCommandType, "/servo_node/switch_command_type"
        )
        self.pause_cli = self.create_client(
            SetBool, "/servo_node/pause_servo"
        )

        # State
        self.current_mode = MODE_JOINT_JOG
        self.servo_paused = False
        self.speed = self.get_parameter("speed").value

        # Active command (set by button press, cleared on release)
        self._active_cmd: dict | None = None
        self._timer_id: str | None = None

        self.get_logger().info("Servo GUI node initialised")

    # ── Service helpers ──────────────────────────────────────────────────────
    def call_switch_mode(self, mode: int):
        if not self.switch_mode_cli.service_is_ready():
            self.get_logger().warn("switch_command_type service not ready")
            return
        req = ServoCommandType.Request()
        req.command_type = mode
        future = self.switch_mode_cli.call_async(req)
        future.add_done_callback(self._on_switch_mode_done)

    def _on_switch_mode_done(self, future):
        try:
            resp = future.result()
            if resp.success:
                self.current_mode = MODE_JOINT_JOG if self.current_mode == MODE_TWIST else MODE_TWIST
        except Exception as e:
            self.get_logger().error(f"switch mode error: {e}")

    def call_pause(self, pause: bool):
        if not self.pause_cli.service_is_ready():
            self.get_logger().warn("pause_servo service not ready")
            return
        req = SetBool.Request()
        req.data = pause
        future = self.pause_cli.call_async(req)
        future.add_done_callback(
            lambda f: self._on_pause_done(f, pause)
        )

    def _on_pause_done(self, future, requested_pause: bool):
        try:
            future.result()
            self.servo_paused = requested_pause
        except Exception as e:
            self.get_logger().error(f"pause_servo error: {e}")

    # ── Publishing ───────────────────────────────────────────────────────────
    def publish_twist(self, lx=0.0, ly=0.0, lz=0.0, ax=0.0, ay=0.0, az=0.0):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.planning_frame
        s = self.speed
        msg.twist.linear.x = lx * s
        msg.twist.linear.y = ly * s
        msg.twist.linear.z = lz * s
        msg.twist.angular.x = ax * s
        msg.twist.angular.y = ay * s
        msg.twist.angular.z = az * s
        self.twist_pub.publish(msg)

    def publish_joint_jog(self, joint_idx: int, direction: float):
        if joint_idx < 0 or joint_idx >= len(JOINT_NAMES):
            return
        msg = JointJog()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.planning_frame
        msg.joint_names = [JOINT_NAMES[joint_idx]]
        msg.velocities = [direction * self.speed]
        self.joint_pub.publish(msg)


# ═════════════════════════════════════════════════════════════════════════════
#  Tkinter GUI
# ═════════════════════════════════════════════════════════════════════════════
class ServoGui:
    """Tkinter window for jog control."""

    def __init__(self, node: ServoGuiNode):
        self.node = node

        # ── Root window ──────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("Servo Jog Control")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Style
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TScale", background=BG, troughcolor=BTN_BG)
        style.configure("TLabel", background=BG, foreground=FG)

        self._build_ui()

        # Initial mode switch request
        self.node.call_switch_mode(MODE_JOINT_JOG)
        self.node.current_mode = MODE_JOINT_JOG
        self._update_mode_buttons()
        self._update_status()

    # ── UI construction ──────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=6, pady=3)

        # ── Title ────────────────────────────────────────────────────────
        tk.Label(
            self.root, text="Servo Jog Control", font=("Helvetica", 16, "bold"),
            bg=BG, fg=ACCENT,
        ).pack(fill="x", pady=(10, 4))

        # ── Mode / Pause row ─────────────────────────────────────────────
        mode_frame = tk.Frame(self.root, bg=BG)
        mode_frame.pack(fill="x", **pad)

        self.btn_joint = tk.Button(
            mode_frame, text="Joint Jog", width=12,
            command=self._on_joint_mode,
            bg=ACCENT, fg=BG, activebackground=ACCENT_HOVER,
            font=("Helvetica", 11, "bold"), relief="flat",
        )
        self.btn_joint.pack(side="left", padx=4)

        self.btn_twist = tk.Button(
            mode_frame, text="Twist", width=12,
            command=self._on_twist_mode,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
            font=("Helvetica", 11, "bold"), relief="flat",
        )
        self.btn_twist.pack(side="left", padx=4)

        self.btn_pause = tk.Button(
            mode_frame, text="⏸  Pause Servo", width=18,
            command=self._on_pause_toggle,
            bg=GREEN, fg=BG, activebackground=YELLOW,
            font=("Helvetica", 11, "bold"), relief="flat",
        )
        self.btn_pause.pack(side="right", padx=4)

        # ── Joint jog section ────────────────────────────────────────────
        self.joint_frame = tk.LabelFrame(
            self.root, text="  Joint Jog  ", bg=BG_SECTION, fg=ACCENT,
            font=("Helvetica", 11, "bold"), relief="groove", bd=1,
        )
        self.joint_frame.pack(fill="x", padx=10, pady=4)

        self.joint_btns: list[tuple[tk.Button, tk.Button]] = []
        for i, name in enumerate(JOINT_NAMES):
            row = tk.Frame(self.joint_frame, bg=BG_SECTION)
            row.pack(fill="x", padx=6, pady=2)

            tk.Label(
                row, text=f"{name}:", width=10, anchor="w",
                bg=BG_SECTION, fg=FG, font=("Helvetica", 11),
            ).pack(side="left")

            btn_neg = tk.Button(
                row, text="◀  −", width=8,
                bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
                font=("Helvetica", 10, "bold"), relief="flat",
            )
            btn_neg.pack(side="left", padx=3)

            btn_pos = tk.Button(
                row, text="+  ▶", width=8,
                bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
                font=("Helvetica", 10, "bold"), relief="flat",
            )
            btn_pos.pack(side="left", padx=3)

            # Bind press / release
            self._bind_hold(btn_neg, "joint", i, -1.0)
            self._bind_hold(btn_pos, "joint", i, 1.0)
            self.joint_btns.append((btn_neg, btn_pos))

        # ── Twist (Cartesian) section ────────────────────────────────────
        self.twist_frame = tk.LabelFrame(
            self.root, text="  Twist (Cartesian)  ", bg=BG_SECTION, fg=ACCENT,
            font=("Helvetica", 11, "bold"), relief="groove", bd=1,
        )
        self.twist_frame.pack(fill="x", padx=10, pady=4)

        twist_axes = [
            ("Linear  X", "lx"),
            ("Linear  Y", "ly"),
            ("Linear  Z", "lz"),
            ("Roll    (X)", "ax"),
            ("Pitch   (Y)", "ay"),
            ("Yaw     (Z)", "az"),
        ]

        self.twist_btns: list[tuple[tk.Button, tk.Button]] = []
        for label_text, axis_key in twist_axes:
            row = tk.Frame(self.twist_frame, bg=BG_SECTION)
            row.pack(fill="x", padx=6, pady=2)

            tk.Label(
                row, text=f"{label_text}:", width=12, anchor="w",
                bg=BG_SECTION, fg=FG, font=("Helvetica", 11),
            ).pack(side="left")

            btn_neg = tk.Button(
                row, text="◀  −", width=8,
                bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
                font=("Helvetica", 10, "bold"), relief="flat",
            )
            btn_neg.pack(side="left", padx=3)

            btn_pos = tk.Button(
                row, text="+  ▶", width=8,
                bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
                font=("Helvetica", 10, "bold"), relief="flat",
            )
            btn_pos.pack(side="left", padx=3)

            self._bind_hold(btn_neg, "twist", axis_key, -1.0)
            self._bind_hold(btn_pos, "twist", axis_key, 1.0)
            self.twist_btns.append((btn_neg, btn_pos))

        # ── Speed slider ─────────────────────────────────────────────────
        speed_frame = tk.Frame(self.root, bg=BG)
        speed_frame.pack(fill="x", padx=10, pady=6)

        tk.Label(
            speed_frame, text="Speed:", bg=BG, fg=FG,
            font=("Helvetica", 11),
        ).pack(side="left")

        self.speed_var = tk.DoubleVar(value=self.node.speed)
        self.speed_slider = ttk.Scale(
            speed_frame, from_=0.05, to=1.0, orient="horizontal",
            variable=self.speed_var, command=self._on_speed_change,
        )
        self.speed_slider.pack(side="left", fill="x", expand=True, padx=6)

        self.speed_label = tk.Label(
            speed_frame, text=f"{self.node.speed:.2f}", width=5,
            bg=BG, fg=YELLOW, font=("Helvetica", 11, "bold"),
        )
        self.speed_label.pack(side="left")

        # ── Status bar ───────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="")
        self.status_bar = tk.Label(
            self.root, textvariable=self.status_var, anchor="w",
            bg=BG_SECTION, fg=FG, font=("Helvetica", 10),
            relief="sunken", bd=1, padx=6, pady=4,
        )
        self.status_bar.pack(fill="x", side="bottom", padx=0, pady=0)

        # Keyboard bindings (when window focused)
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Hold-button logic ────────────────────────────────────────────────
    def _bind_hold(self, btn: tk.Button, cmd_type: str, axis, direction: float):
        """Bind press/release so command repeats while held."""
        cmd = {"type": cmd_type, "axis": axis, "direction": direction}
        btn.bind("<ButtonPress-1>", lambda e: self._start_cmd(cmd))
        btn.bind("<ButtonRelease-1>", lambda e: self._stop_cmd())

    def _start_cmd(self, cmd: dict):
        self.node._active_cmd = cmd
        self._send_active_cmd()

    def _stop_cmd(self):
        self.node._active_cmd = None
        if self.node._timer_id is not None:
            self.root.after_cancel(self.node._timer_id)
            self.node._timer_id = None

    def _send_active_cmd(self):
        cmd = self.node._active_cmd
        if cmd is None:
            return

        if cmd["type"] == "joint":
            self.node.publish_joint_jog(cmd["axis"], cmd["direction"])
        elif cmd["type"] == "twist":
            kwargs = {cmd["axis"]: cmd["direction"]}
            self.node.publish_twist(**kwargs)

        # Schedule next repeat
        self.node._timer_id = self.root.after(PUBLISH_PERIOD_MS, self._send_active_cmd)

    # ── Keyboard shortcuts ───────────────────────────────────────────────
    _KEY_MAP_TWIST = {
        "Up":    dict(lx=1.0),
        "Down":  dict(lx=-1.0),
        "Right": dict(ly=-1.0),
        "Left":  dict(ly=1.0),
        "u":     dict(lz=1.0),
        "o":     dict(lz=-1.0),
        "j":     dict(ax=1.0),
        "l":     dict(ax=-1.0),
        "i":     dict(ay=1.0),
        "k":     dict(ay=-1.0),
        "n":     dict(az=1.0),
        "m":     dict(az=-1.0),
    }

    def _on_key_press(self, event):
        key = event.keysym

        # Mode switching
        if key == "t":
            self._on_twist_mode()
            return
        if key == "g":
            self._on_joint_mode()
            return
        if key == "p":
            self._on_pause_toggle()
            return

        # If already sending a command, ignore repeated key events
        if self.node._active_cmd is not None:
            return

        # Joint jog: keys 1-6
        if self.node.current_mode == MODE_JOINT_JOG and key in "123456":
            idx = int(key) - 1
            self._start_cmd({"type": "joint", "axis": idx, "direction": 1.0})
            return

        # Joint jog negative: Shift + 1-6 (!, @, #, $, %, ^)
        shift_map = {"exclam": 0, "at": 1, "numbersign": 2,
                     "dollar": 3, "percent": 4, "asciicircum": 5}
        if self.node.current_mode == MODE_JOINT_JOG and key in shift_map:
            self._start_cmd({"type": "joint", "axis": shift_map[key], "direction": -1.0})
            return

        # Twist
        if self.node.current_mode == MODE_TWIST and key in self._KEY_MAP_TWIST:
            kwargs = self._KEY_MAP_TWIST[key]
            axis_key = list(kwargs.keys())[0]
            direction = list(kwargs.values())[0]
            self._start_cmd({"type": "twist", "axis": axis_key, "direction": direction})
            return

    def _on_key_release(self, event):
        self._stop_cmd()

    # ── Mode callbacks ───────────────────────────────────────────────────
    def _on_joint_mode(self):
        self.node.call_switch_mode(MODE_JOINT_JOG)
        self.node.current_mode = MODE_JOINT_JOG
        self._update_mode_buttons()
        self._update_status()

    def _on_twist_mode(self):
        self.node.call_switch_mode(MODE_TWIST)
        self.node.current_mode = MODE_TWIST
        self._update_mode_buttons()
        self._update_status()

    def _update_mode_buttons(self):
        if self.node.current_mode == MODE_JOINT_JOG:
            self.btn_joint.configure(bg=ACCENT, fg=BG)
            self.btn_twist.configure(bg=BTN_BG, fg=FG)
        else:
            self.btn_joint.configure(bg=BTN_BG, fg=FG)
            self.btn_twist.configure(bg=ACCENT, fg=BG)

    # ── Pause / Resume ───────────────────────────────────────────────────
    def _on_pause_toggle(self):
        new_state = not self.node.servo_paused
        self.node.call_pause(new_state)
        self.node.servo_paused = new_state
        self._update_pause_button()
        self._update_status()

    def _update_pause_button(self):
        if self.node.servo_paused:
            self.btn_pause.configure(
                text="▶  Resume Servo", bg=RED, fg=BG
            )
        else:
            self.btn_pause.configure(
                text="⏸  Pause Servo", bg=GREEN, fg=BG
            )

    # ── Speed slider ─────────────────────────────────────────────────────
    def _on_speed_change(self, val):
        self.node.speed = float(val)
        self.speed_label.configure(text=f"{self.node.speed:.2f}")

    # ── Status bar ───────────────────────────────────────────────────────
    def _update_status(self):
        mode_str = "Joint Jog" if self.node.current_mode == MODE_JOINT_JOG else "Twist"
        servo_str = "PAUSED" if self.node.servo_paused else "Active"
        servo_colour = RED if self.node.servo_paused else GREEN
        self.status_var.set(f"  Mode: {mode_str}   |   Servo: {servo_str}   |   Frame: {self.node.planning_frame}")
        self.status_bar.configure(fg=servo_colour)

    # ── Close ────────────────────────────────────────────────────────────
    def _on_close(self):
        self._stop_cmd()
        self.root.destroy()

    # ── Main loop (call from main thread) ────────────────────────────────
    def run(self):
        self.root.mainloop()


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════
def main():
    rclpy.init()
    node = ServoGuiNode()

    # Spin ROS 2 in a background thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # Run tkinter on the main thread
    gui = ServoGui(node)
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
