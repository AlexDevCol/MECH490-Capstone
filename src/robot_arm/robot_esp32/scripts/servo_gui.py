#!/usr/bin/env python3

"""
ESP32 Servo Control Test Interface

A tkinter-based GUI for controlling the ESP32 servo motor via ROS 2.
Publishes angle commands to the /servo_angle topic.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import tkinter as tk
from tkinter import ttk
import threading
import sys


class ServoControlGUI:
    """GUI for controlling ESP32 servo motor."""
    
    def __init__(self, root, ros_node):
        self.root = root
        self.ros_node = ros_node
        self.current_angle = 90  # Default angle
        
        # Setup GUI
        self.setup_gui()
        
        # Update status periodically
        self.update_status()
        
    def setup_gui(self):
        """Create and layout GUI components."""
        self.root.title("ESP32 Servo Control Test Interface")
        self.root.geometry("400x350")
        self.root.resizable(False, False)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="ESP32 Servo Control", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Current angle display
        angle_frame = ttk.Frame(main_frame)
        angle_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        ttk.Label(angle_frame, text="Current Angle:", font=("Arial", 10)).grid(row=0, column=0, padx=(0, 10))
        self.angle_label = ttk.Label(
            angle_frame, 
            text="90°", 
            font=("Arial", 14, "bold"),
            foreground="blue"
        )
        self.angle_label.grid(row=0, column=1)
        
        # Slider
        slider_frame = ttk.Frame(main_frame)
        slider_frame.grid(row=2, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
        ttk.Label(slider_frame, text="0°").grid(row=0, column=0, padx=(0, 10))
        
        self.angle_var = tk.IntVar(value=90)
        self.angle_slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=180,
            orient=tk.HORIZONTAL,
            length=250,
            variable=self.angle_var,
            command=self.on_slider_change
        )
        self.angle_slider.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(slider_frame, text="180°").grid(row=0, column=2, padx=(10, 0))
        
        # Preset buttons frame
        preset_frame = ttk.LabelFrame(main_frame, text="Quick Presets", padding="10")
        preset_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        preset_angles = [0, 45, 90, 135, 180]
        for i, angle in enumerate(preset_angles):
            btn = ttk.Button(
                preset_frame,
                text=f"{angle}°",
                width=8,
                command=lambda a=angle: self.set_angle(a)
            )
            btn.grid(row=0, column=i, padx=5)
        
        # Send button
        send_frame = ttk.Frame(main_frame)
        send_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        self.send_button = ttk.Button(
            send_frame,
            text="Send Angle",
            command=self.send_angle,
            width=20
        )
        self.send_button.grid(row=0, column=0)
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Label(status_frame, text="Status:", font=("Arial", 9)).grid(row=0, column=0, padx=(0, 10))
        self.status_label = ttk.Label(
            status_frame,
            text="Initializing...",
            font=("Arial", 9),
            foreground="orange"
        )
        self.status_label.grid(row=0, column=1)
        
        # Configure column weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        slider_frame.columnconfigure(1, weight=1)
        
    def on_slider_change(self, value):
        """Called when slider value changes."""
        angle = int(float(value))
        self.current_angle = angle
        self.angle_label.config(text=f"{angle}°")
        
    def set_angle(self, angle):
        """Set angle from preset button."""
        self.angle_var.set(angle)
        self.current_angle = angle
        self.angle_label.config(text=f"{angle}°")
        
    def send_angle(self):
        """Publish angle command to ROS 2 topic."""
        angle = self.current_angle
        msg = Int32()
        msg.data = angle
        
        self.ros_node.publisher.publish(msg)
        self.ros_node.get_logger().info(f"Published angle: {angle}°")
        
        # Visual feedback
        self.status_label.config(text=f"Sent: {angle}°", foreground="green")
        self.root.after(1000, lambda: self.status_label.config(text="Ready", foreground="blue"))
        
    def update_status(self):
        """Periodically update connection status."""
        # Check if ROS 2 is running
        if rclpy.ok():
            # Simple status - if ROS is running, assume ready
            # User can verify connection by checking if servo responds
            self.status_label.config(text="Ready", foreground="blue")
        else:
            self.status_label.config(text="ROS 2 not running", foreground="red")
            
        # Schedule next update
        self.root.after(2000, self.update_status)


class ServoControlNode(Node):
    """ROS 2 node for servo control."""
    
    def __init__(self):
        super().__init__('servo_control_gui')
        
        # Create publisher
        self.publisher = self.create_publisher(
            Int32,
            '/servo_angle',
            10
        )
        
        self.get_logger().info('Servo Control GUI node started')
        self.get_logger().info('Publishing to /servo_angle topic')


def spin_ros_node(node):
    """Spin ROS node in separate thread."""
    rclpy.spin(node)


def main(args=None):
    """Main function."""
    # Initialize ROS 2
    rclpy.init(args=args)
    
    # Create ROS node
    ros_node = ServoControlNode()
    
    # Create GUI in main thread
    root = tk.Tk()
    gui = ServoControlGUI(root, ros_node)
    
    # Spin ROS node in background thread
    ros_thread = threading.Thread(target=spin_ros_node, args=(ros_node,), daemon=True)
    ros_thread.start()
    
    try:
        # Run GUI main loop
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        ros_node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()
