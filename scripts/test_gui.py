#!/usr/bin/env python3
"""
Test GUI for ESP32 Robot Arm Control

A simple tkinter-based GUI for testing joint position commands and receiving feedback.
Provides interface to send joint angles (in degrees) and control gripper servo.

Usage:
    python3 test_gui.py

:author: MECH490-Capstone Team
:date: February 2026
"""

import threading
import tkinter as tk
from tkinter import ttk
import math
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray, Int32

# ── Constants ────────────────────────────────────────────────────────────────
NUM_JOINTS = 6
JOINT_NAMES = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]

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


class TestGuiNode(Node):
    """ROS 2 node for test GUI."""

    def __init__(self):
        super().__init__("test_gui_node")

        # Publishers
        self.joint_cmd_pub = self.create_publisher(
            Float64MultiArray, "/joint_position_commands", 10
        )
        self.gripper_pub = self.create_publisher(
            Int32, "/gripper_angle", 10
        )

        # Subscriber
        self.feedback_sub = self.create_subscription(
            Float64MultiArray, "/joint_position_feedback",
            self.feedback_callback, 10
        )

        # State
        self.latest_feedback = [0.0] * NUM_JOINTS
        self.feedback_received = False
        self.last_feedback_time = None
        self.last_command_time = None

        self.get_logger().info("Test GUI node initialized")

    def feedback_callback(self, msg):
        """Callback for joint position feedback."""
        if len(msg.data) == NUM_JOINTS:
            self.latest_feedback = list(msg.data)
            self.feedback_received = True
            self.last_feedback_time = datetime.now()

    def publish_joint_commands(self, angles_rad):
        """Publish joint position commands (in radians)."""
        msg = Float64MultiArray()
        msg.data = angles_rad
        self.joint_cmd_pub.publish(msg)
        self.last_command_time = datetime.now()
        self.get_logger().info(f"Published joint commands: {[f'{a:.3f}' for a in angles_rad]} rad")

    def publish_gripper_angle(self, angle):
        """Publish gripper angle command (0-180 degrees)."""
        msg = Int32()
        msg.data = max(0, min(180, angle))  # Clamp to valid range
        self.gripper_pub.publish(msg)
        self.get_logger().info(f"Published gripper angle: {angle}°")


# ═════════════════════════════════════════════════════════════════════════════
#  Tkinter GUI
# ═════════════════════════════════════════════════════════════════════════════
class TestGui:
    """Tkinter window for test interface."""

    def __init__(self, node: TestGuiNode):
        self.node = node

        # ── Root window ──────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("Robot Arm Test Interface")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Style
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TScale", background=BG, troughcolor=BTN_BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TEntry", fieldbackground=BTN_BG, foreground=FG)

        self._build_ui()

        # Start periodic updates
        self._update_display()

    # ── UI construction ──────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=6, pady=3)

        # ── Title ────────────────────────────────────────────────────────
        tk.Label(
            self.root, text="Robot Arm Test Interface", font=("Helvetica", 16, "bold"),
            bg=BG, fg=ACCENT,
        ).pack(fill="x", pady=(10, 4))

        # ── Joint Control Section ────────────────────────────────────────
        joint_frame = tk.LabelFrame(
            self.root, text="  Joint Control (Degrees)  ", bg=BG_SECTION, fg=ACCENT,
            font=("Helvetica", 11, "bold"), relief="groove", bd=1,
        )
        joint_frame.pack(fill="x", padx=10, pady=4)

        # Joint input fields
        self.joint_entries = []
        for i, name in enumerate(JOINT_NAMES):
            row = tk.Frame(joint_frame, bg=BG_SECTION)
            row.pack(fill="x", padx=6, pady=2)

            tk.Label(
                row, text=f"{name}:", width=12, anchor="w",
                bg=BG_SECTION, fg=FG, font=("Helvetica", 10),
            ).pack(side="left")

            entry = tk.Entry(
                row, width=10, bg=BTN_BG, fg=FG,
                font=("Helvetica", 10), insertbackground=FG,
            )
            entry.insert(0, "0.0")
            entry.pack(side="left", padx=4)
            self.joint_entries.append(entry)

            tk.Label(
                row, text="°", width=2, anchor="w",
                bg=BG_SECTION, fg=FG, font=("Helvetica", 10),
            ).pack(side="left")

        # Send button
        send_frame = tk.Frame(joint_frame, bg=BG_SECTION)
        send_frame.pack(fill="x", padx=6, pady=6)

        self.send_btn = tk.Button(
            send_frame, text="Send Joint Commands", width=20,
            command=self._send_joint_commands,
            bg=ACCENT, fg=BG, activebackground=ACCENT_HOVER,
            font=("Helvetica", 11, "bold"), relief="flat",
        )
        self.send_btn.pack()

        # ── Feedback Display Section ─────────────────────────────────────
        feedback_frame = tk.LabelFrame(
            self.root, text="  Joint Feedback (Degrees)  ", bg=BG_SECTION, fg=ACCENT,
            font=("Helvetica", 11, "bold"), relief="groove", bd=1,
        )
        feedback_frame.pack(fill="x", padx=10, pady=4)

        # Feedback display labels
        self.feedback_labels = []
        for i, name in enumerate(JOINT_NAMES):
            row = tk.Frame(feedback_frame, bg=BG_SECTION)
            row.pack(fill="x", padx=6, pady=2)

            tk.Label(
                row, text=f"{name}:", width=12, anchor="w",
                bg=BG_SECTION, fg=FG, font=("Helvetica", 10),
            ).pack(side="left")

            label = tk.Label(
                row, text="0.0°", width=10, anchor="w",
                bg=BG_SECTION, fg=YELLOW, font=("Helvetica", 10, "bold"),
            )
            label.pack(side="left", padx=4)
            self.feedback_labels.append(label)

        # ── Gripper Control Section ──────────────────────────────────────
        gripper_frame = tk.LabelFrame(
            self.root, text="  Gripper Control  ", bg=BG_SECTION, fg=ACCENT,
            font=("Helvetica", 11, "bold"), relief="groove", bd=1,
        )
        gripper_frame.pack(fill="x", padx=10, pady=4)

        # Current angle display
        angle_display_frame = tk.Frame(gripper_frame, bg=BG_SECTION)
        angle_display_frame.pack(fill="x", padx=6, pady=4)

        tk.Label(
            angle_display_frame, text="Angle:", width=8, anchor="w",
            bg=BG_SECTION, fg=FG, font=("Helvetica", 11),
        ).pack(side="left")

        self.gripper_angle_var = tk.IntVar(value=90)
        self.gripper_angle_label = tk.Label(
            angle_display_frame, text="90°", width=6,
            bg=BG_SECTION, fg=YELLOW, font=("Helvetica", 12, "bold"),
        )
        self.gripper_angle_label.pack(side="left", padx=4)

        # Slider
        slider_frame = tk.Frame(gripper_frame, bg=BG_SECTION)
        slider_frame.pack(fill="x", padx=6, pady=4)

        tk.Label(
            slider_frame, text="0°", width=4, anchor="w",
            bg=BG_SECTION, fg=FG, font=("Helvetica", 9),
        ).pack(side="left")

        self.gripper_slider = ttk.Scale(
            slider_frame, from_=0, to=180, orient="horizontal",
            variable=self.gripper_angle_var, command=self._on_gripper_slider_change,
        )
        self.gripper_slider.pack(side="left", fill="x", expand=True, padx=6)

        tk.Label(
            slider_frame, text="180°", width=4, anchor="e",
            bg=BG_SECTION, fg=FG, font=("Helvetica", 9),
        ).pack(side="left")

        # Preset buttons
        preset_frame = tk.Frame(gripper_frame, bg=BG_SECTION)
        preset_frame.pack(fill="x", padx=6, pady=4)

        preset_angles = [0, 45, 90, 135, 180]
        for angle in preset_angles:
            btn = tk.Button(
                preset_frame, text=f"{angle}°", width=6,
                command=lambda a=angle: self._on_gripper_preset(a),
                bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
                font=("Helvetica", 9, "bold"), relief="flat",
            )
            btn.pack(side="left", padx=2)

        # ── Status bar ───────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(
            self.root, textvariable=self.status_var, anchor="w",
            bg=BG_SECTION, fg=FG, font=("Helvetica", 10),
            relief="sunken", bd=1, padx=6, pady=4,
        )
        self.status_bar.pack(fill="x", side="bottom", padx=0, pady=0)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Callbacks ────────────────────────────────────────────────────────
    def _send_joint_commands(self):
        """Read joint angles from entries, convert to radians, and publish."""
        try:
            angles_deg = []
            for entry in self.joint_entries:
                value = float(entry.get())
                angles_deg.append(value)

            # Convert degrees to radians
            angles_rad = [math.radians(deg) for deg in angles_deg]

            # Publish
            self.node.publish_joint_commands(angles_rad)

            # Update status
            self.status_var.set(f"Sent joint commands: {[f'{d:.1f}°' for d in angles_deg]}")

        except ValueError as e:
            self.status_var.set(f"Error: Invalid input - {str(e)}")
            self.status_bar.configure(fg=RED)

    def _on_gripper_slider_change(self, val):
        """Handle gripper slider change."""
        angle = int(float(val))
        self.gripper_angle_var.set(angle)
        self.gripper_angle_label.configure(text=f"{angle}°")
        self.node.publish_gripper_angle(angle)

    def _on_gripper_preset(self, angle: int):
        """Handle gripper preset button press."""
        self.gripper_angle_var.set(angle)
        self.gripper_slider.set(angle)
        self.gripper_angle_label.configure(text=f"{angle}°")
        self.node.publish_gripper_angle(angle)

    def _update_display(self):
        """Update feedback display and status."""
        # Update feedback labels
        if self.node.feedback_received:
            for i, label in enumerate(self.feedback_labels):
                rad_value = self.node.latest_feedback[i]
                deg_value = math.degrees(rad_value)
                label.configure(text=f"{deg_value:.2f}°")

        # Update status bar
        status_parts = []
        if self.node.feedback_received:
            if self.node.last_feedback_time:
                elapsed = (datetime.now() - self.node.last_feedback_time).total_seconds()
                status_parts.append(f"Feedback: {elapsed:.1f}s ago")
        else:
            status_parts.append("Waiting for feedback...")

        if self.node.last_command_time:
            elapsed = (datetime.now() - self.node.last_command_time).total_seconds()
            status_parts.append(f"Last command: {elapsed:.1f}s ago")

        if status_parts:
            self.status_var.set(" | ".join(status_parts))
            self.status_bar.configure(fg=GREEN if self.node.feedback_received else YELLOW)
        else:
            self.status_var.set("Ready")
            self.status_bar.configure(fg=FG)

        # Schedule next update
        self.root.after(100, self._update_display)

    def _on_close(self):
        """Handle window close."""
        self.root.destroy()

    # ── Main loop ────────────────────────────────────────────────────────
    def run(self):
        """Run the GUI main loop."""
        self.root.mainloop()


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════
def main():
    rclpy.init()
    node = TestGuiNode()

    # Spin ROS 2 in a background thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # Run tkinter on the main thread
    gui = TestGui(node)
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
