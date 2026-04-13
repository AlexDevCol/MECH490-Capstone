#!/usr/bin/env python3
"""
Floating Gripper Control Window

Standalone Tkinter GUI for gripper control when MoveIt Servo is not enabled.
Provides a floating window with slider and preset buttons for gripper control.

Usage:
    python3 gripper_control.py

:author: MECH490-Capstone Team
:date: February 2026
"""

import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32

# ── Colour palette ───────────────────────────────────────────────────────────
BG           = "#1e1e2e"
BG_SECTION   = "#2a2a3d"
FG           = "#cdd6f4"
ACCENT       = "#89b4fa"
YELLOW       = "#f9e2af"
BTN_BG       = "#45475a"
BTN_ACTIVE   = "#585b70"


class GripperControlNode(Node):
    """ROS 2 node that publishes gripper angle commands."""

    def __init__(self):
        super().__init__("gripper_control_node")

        # Publisher
        self.gripper_pub = self.create_publisher(
            Int32, "/gripper_angle", 10
        )

        self.get_logger().info("Gripper control node initialised")

    def publish_gripper_angle(self, angle: int):
        """Publish gripper angle command (0-180 degrees)."""
        msg = Int32()
        msg.data = max(0, min(180, angle))  # Clamp to valid range
        self.gripper_pub.publish(msg)
        self.get_logger().info(f"Published gripper angle: {angle}°")


class GripperControlGui:
    """Floating Tkinter window for gripper control."""

    def __init__(self, node: GripperControlNode):
        self.node = node

        # ── Root window ──────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("Gripper Control")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Style
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TScale", background=BG, troughcolor=BTN_BG)
        style.configure("TLabel", background=BG, foreground=FG)

        self._build_ui()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ──────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=6, pady=3)

        # ── Title ────────────────────────────────────────────────────────
        tk.Label(
            self.root, text="Gripper Control", font=("Helvetica", 14, "bold"),
            bg=BG, fg=ACCENT,
        ).pack(fill="x", pady=(10, 8))

        # ── Current angle display ────────────────────────────────────────
        angle_frame = tk.Frame(self.root, bg=BG)
        angle_frame.pack(fill="x", **pad)

        tk.Label(
            angle_frame, text="Angle:", width=8, anchor="w",
            bg=BG, fg=FG, font=("Helvetica", 11),
        ).pack(side="left")

        self.gripper_angle_var = tk.IntVar(value=90)
        self.gripper_angle_label = tk.Label(
            angle_frame, text="90°", width=6,
            bg=BG, fg=YELLOW, font=("Helvetica", 12, "bold"),
        )
        self.gripper_angle_label.pack(side="left", padx=4)

        # ── Slider ───────────────────────────────────────────────────────
        slider_frame = tk.Frame(self.root, bg=BG)
        slider_frame.pack(fill="x", padx=10, pady=6)

        tk.Label(
            slider_frame, text="0°", width=4, anchor="w",
            bg=BG, fg=FG, font=("Helvetica", 9),
        ).pack(side="left")

        self.gripper_slider = ttk.Scale(
            slider_frame, from_=0, to=180, orient="horizontal",
            variable=self.gripper_angle_var, command=self._on_slider_change,
        )
        self.gripper_slider.pack(side="left", fill="x", expand=True, padx=6)

        tk.Label(
            slider_frame, text="180°", width=4, anchor="e",
            bg=BG, fg=FG, font=("Helvetica", 9),
        ).pack(side="left")

        # ── Preset buttons ──────────────────────────────────────────────
        preset_frame = tk.LabelFrame(
            self.root, text="  Quick Presets  ", bg=BG_SECTION, fg=ACCENT,
            font=("Helvetica", 10, "bold"), relief="groove", bd=1,
        )
        preset_frame.pack(fill="x", padx=10, pady=6)

        preset_angles = [0, 45, 90, 135, 180]
        for angle in preset_angles:
            btn = tk.Button(
                preset_frame, text=f"{angle}°", width=8,
                command=lambda a=angle: self._on_preset(a),
                bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE,
                font=("Helvetica", 10, "bold"), relief="flat",
            )
            btn.pack(side="left", padx=4, pady=4)

    # ── Callbacks ────────────────────────────────────────────────────────
    def _on_slider_change(self, val):
        angle = int(float(val))
        self.gripper_angle_var.set(angle)
        self.gripper_angle_label.configure(text=f"{angle}°")
        self.node.publish_gripper_angle(angle)

    def _on_preset(self, angle: int):
        self.gripper_angle_var.set(angle)
        self.gripper_slider.set(angle)
        self.gripper_angle_label.configure(text=f"{angle}°")
        self.node.publish_gripper_angle(angle)

    # ── Close ────────────────────────────────────────────────────────────
    def _on_close(self):
        self.root.destroy()

    # ── Main loop ────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════
def main():
    rclpy.init()
    node = GripperControlNode()

    # Spin ROS 2 in a background thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # Run tkinter on the main thread
    gui = GripperControlGui(node)
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
