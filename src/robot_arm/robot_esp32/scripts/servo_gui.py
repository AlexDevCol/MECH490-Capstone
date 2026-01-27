#!/usr/bin/env python3

"""
ESP32 Motor Control Test Interface

A tkinter-based GUI for controlling ESP32 servo and stepper motors via ROS 2.
Supports both servo and stepper motor testing through a mode selector.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import tkinter as tk
from tkinter import ttk
import threading
import sys
import time


class MotorControlGUI:
    """GUI for controlling ESP32 servo and stepper motors."""
    
    # Stepper motor parameters (from Arduino code)
    STEPS_PER_REV = 2048
    GEAR_RATIO = 19
    MAX_SPEED = 600  # steps/s
    ACCELERATION = 60  # steps/s²
    
    def __init__(self, root, ros_node):
        self.root = root
        self.ros_node = ros_node
        self.current_angle = 90  # Default angle for servo
        self.current_mode = "Servo Test"  # Current mode
        
        # Calculate steps per degree
        self.steps_per_degree = (self.STEPS_PER_REV * self.GEAR_RATIO) / 360.0
        
        # Live Mode state
        self.live_mode_var = tk.BooleanVar(value=False)
        self.last_publish_time = 0
        self.MIN_PUBLISH_INTERVAL = 0.05  # 50ms = 20 Hz max
        
        # Connection status
        self.esp32_connected = False
        
        # Setup GUI
        self.setup_gui()
        
        # Update status periodically
        self.update_status()
        
    def setup_gui(self):
        """Create and layout GUI components."""
        self.root.title("ESP32 Motor Control Test Interface")
        self.root.geometry("500x650")
        self.root.resizable(False, False)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="ESP32 Motor Control", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Mode selector
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        ttk.Label(mode_frame, text="Test Mode:", font=("Arial", 10)).grid(row=0, column=0, padx=(0, 10))
        self.mode_var = tk.StringVar(value="Servo Test")
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=["Servo Test", "Stepper Test"],
            state="readonly",
            width=15
        )
        mode_combo.grid(row=0, column=1)
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)
        
        # Create interface frames (will be shown/hidden)
        self.servo_frame = ttk.Frame(main_frame)
        self.stepper_frame = ttk.Frame(main_frame)
        
        # Setup both interfaces
        self.setup_servo_interface()
        self.setup_stepper_interface()
        
        # Status frame (shared)
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=10, column=0, columnspan=3, pady=(20, 0))
        
        ttk.Label(status_frame, text="Status:", font=("Arial", 9)).grid(row=0, column=0, padx=(0, 10))
        
        # Connection indicator (circle)
        self.connection_indicator = tk.Canvas(status_frame, width=12, height=12, highlightthickness=0)
        self.connection_indicator.grid(row=0, column=1, padx=(0, 5))
        self.connection_circle = self.connection_indicator.create_oval(2, 2, 10, 10, fill="orange", outline="")
        
        self.status_label = ttk.Label(
            status_frame,
            text="Checking...",
            font=("Arial", 9),
            foreground="orange"
        )
        self.status_label.grid(row=0, column=2)
        
        # Configure column weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Show initial interface
        self.show_servo_interface()
        
    def setup_servo_interface(self):
        """Create servo control interface."""
        # Current angle display
        angle_frame = ttk.Frame(self.servo_frame)
        angle_frame.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        ttk.Label(angle_frame, text="Current Angle:", font=("Arial", 10)).grid(row=0, column=0, padx=(0, 10))
        self.servo_angle_label = ttk.Label(
            angle_frame, 
            text="90°", 
            font=("Arial", 14, "bold"),
            foreground="blue"
        )
        self.servo_angle_label.grid(row=0, column=1)
        
        # Slider
        slider_frame = ttk.Frame(self.servo_frame)
        slider_frame.grid(row=1, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
        ttk.Label(slider_frame, text="0°").grid(row=0, column=0, padx=(0, 10))
        
        self.servo_angle_var = tk.IntVar(value=90)
        self.servo_angle_slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=180,
            orient=tk.HORIZONTAL,
            length=250,
            variable=self.servo_angle_var,
            command=self.on_servo_slider_change
        )
        self.servo_angle_slider.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(slider_frame, text="180°").grid(row=0, column=2, padx=(10, 0))
        
        # Preset buttons frame
        preset_frame = ttk.LabelFrame(self.servo_frame, text="Quick Presets", padding="10")
        preset_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        preset_angles = [0, 45, 90, 135, 180]
        for i, angle in enumerate(preset_angles):
            btn = ttk.Button(
                preset_frame,
                text=f"{angle}°",
                width=8,
                command=lambda a=angle: self.set_servo_angle(a)
            )
            btn.grid(row=0, column=i, padx=5)
        
        # Live Mode checkbox
        live_mode_frame = ttk.Frame(self.servo_frame)
        live_mode_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.servo_live_mode_checkbox = ttk.Checkbutton(
            live_mode_frame,
            text="Live Mode",
            variable=self.live_mode_var,
            command=self.on_live_mode_toggle
        )
        self.servo_live_mode_checkbox.grid(row=0, column=0)
        
        # Send button
        send_frame = ttk.Frame(self.servo_frame)
        send_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.servo_send_button = ttk.Button(
            send_frame,
            text="Send Angle",
            command=lambda: self.send_angle("servo"),
            width=20
        )
        self.servo_send_button.grid(row=0, column=0)
        
        # Configure column weights
        slider_frame.columnconfigure(1, weight=1)
        
    def setup_stepper_interface(self):
        """Create stepper control interface."""
        # Current angle display
        angle_frame = ttk.Frame(self.stepper_frame)
        angle_frame.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        ttk.Label(angle_frame, text="Target Angle:", font=("Arial", 10)).grid(row=0, column=0, padx=(0, 10))
        self.stepper_angle_label = ttk.Label(
            angle_frame, 
            text="0°", 
            font=("Arial", 14, "bold"),
            foreground="blue"
        )
        self.stepper_angle_label.grid(row=0, column=1)
        
        # Slider
        slider_frame = ttk.Frame(self.stepper_frame)
        slider_frame.grid(row=1, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
        ttk.Label(slider_frame, text="0°").grid(row=0, column=0, padx=(0, 10))
        
        self.stepper_angle_var = tk.IntVar(value=0)
        self.stepper_angle_slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=360,
            orient=tk.HORIZONTAL,
            length=250,
            variable=self.stepper_angle_var,
            command=self.on_stepper_slider_change
        )
        self.stepper_angle_slider.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(slider_frame, text="360°").grid(row=0, column=2, padx=(10, 0))
        
        # Preset buttons frame
        preset_frame = ttk.LabelFrame(self.stepper_frame, text="Quick Presets", padding="10")
        preset_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        preset_angles = [0, 90, 180, 270, 360]
        for i, angle in enumerate(preset_angles):
            btn = ttk.Button(
                preset_frame,
                text=f"{angle}°",
                width=8,
                command=lambda a=angle: self.set_stepper_angle(a)
            )
            btn.grid(row=0, column=i, padx=5)
        
        # Live Mode checkbox
        live_mode_frame = ttk.Frame(self.stepper_frame)
        live_mode_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.stepper_live_mode_checkbox = ttk.Checkbutton(
            live_mode_frame,
            text="Live Mode",
            variable=self.live_mode_var,
            command=self.on_live_mode_toggle
        )
        self.stepper_live_mode_checkbox.grid(row=0, column=0)
        
        # Send button
        send_frame = ttk.Frame(self.stepper_frame)
        send_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.stepper_send_button = ttk.Button(
            send_frame,
            text="Send Angle",
            command=lambda: self.send_angle("stepper"),
            width=20
        )
        self.stepper_send_button.grid(row=0, column=0)
        
        # Information display panel
        info_frame = ttk.LabelFrame(self.stepper_frame, text="Stepper Motor Information", padding="10")
        info_frame.grid(row=5, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # Motor parameters
        ttk.Label(info_frame, text="Steps per Revolution:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=f"{self.STEPS_PER_REV}", font=("Arial", 9, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(info_frame, text="Gear Ratio:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=f"{self.GEAR_RATIO}:1", font=("Arial", 9, "bold")).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(info_frame, text="Steps per Degree:", font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.steps_per_degree_label = ttk.Label(
            info_frame, 
            text=f"{self.steps_per_degree:.2f}", 
            font=("Arial", 9, "bold")
        )
        self.steps_per_degree_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(info_frame, text="Max Speed:", font=("Arial", 9)).grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=f"{self.MAX_SPEED} steps/s", font=("Arial", 9, "bold")).grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(info_frame, text="Acceleration:", font=("Arial", 9)).grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=f"{self.ACCELERATION} steps/s²", font=("Arial", 9, "bold")).grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Calculation display
        calc_frame = ttk.LabelFrame(self.stepper_frame, text="Step Calculation", padding="10")
        calc_frame.grid(row=6, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.calc_formula_label = ttk.Label(
            calc_frame,
            text="Formula: steps = angle × (2048 × 19) / 360",
            font=("Arial", 8),
            foreground="gray"
        )
        self.calc_formula_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))
        
        self.calc_result_label = ttk.Label(
            calc_frame,
            text="Target: 0° = 0 steps",
            font=("Arial", 10, "bold"),
            foreground="green"
        )
        self.calc_result_label.grid(row=1, column=0, columnspan=2)
        
        # Configure column weights
        slider_frame.columnconfigure(1, weight=1)
        
    def show_servo_interface(self):
        """Show servo interface and hide stepper interface."""
        self.stepper_frame.grid_remove()
        self.servo_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_mode = "Servo Test"
        
    def show_stepper_interface(self):
        """Show stepper interface and hide servo interface."""
        self.servo_frame.grid_remove()
        self.stepper_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_mode = "Stepper Test"
        # Update calculation display
        self.update_stepper_calculation()
        
    def on_mode_change(self, event=None):
        """Handle mode selection change."""
        mode = self.mode_var.get()
        if mode == "Servo Test":
            self.show_servo_interface()
        elif mode == "Stepper Test":
            self.show_stepper_interface()
        
    def on_servo_slider_change(self, value):
        """Called when servo slider value changes."""
        angle = int(float(value))
        self.current_angle = angle
        self.servo_angle_label.config(text=f"{angle}°")
        
        # Auto-send in Live Mode
        if self.live_mode_var.get() and self.current_mode == "Servo Test":
            current_time = time.time()
            if current_time - self.last_publish_time >= self.MIN_PUBLISH_INTERVAL:
                self.send_angle("servo", quiet=True)
                self.last_publish_time = current_time
                
    def on_stepper_slider_change(self, value):
        """Called when stepper slider value changes."""
        angle = int(float(value))
        self.current_angle = angle
        self.stepper_angle_label.config(text=f"{angle}°")
        self.update_stepper_calculation()
        
        # Auto-send in Live Mode
        if self.live_mode_var.get() and self.current_mode == "Stepper Test":
            current_time = time.time()
            if current_time - self.last_publish_time >= self.MIN_PUBLISH_INTERVAL:
                self.send_angle("stepper", quiet=True)
                self.last_publish_time = current_time
                
    def update_stepper_calculation(self):
        """Update stepper calculation display."""
        angle = self.stepper_angle_var.get()
        steps = int(angle * self.steps_per_degree)
        self.calc_result_label.config(text=f"Target: {angle}° = {steps} steps")
        
    def set_servo_angle(self, angle):
        """Set servo angle from preset button."""
        self.servo_angle_var.set(angle)
        self.current_angle = angle
        self.servo_angle_label.config(text=f"{angle}°")
        
        # Auto-send in Live Mode
        if self.live_mode_var.get() and self.current_mode == "Servo Test":
            current_time = time.time()
            if current_time - self.last_publish_time >= self.MIN_PUBLISH_INTERVAL:
                self.send_angle("servo", quiet=True)
                self.last_publish_time = current_time
                
    def set_stepper_angle(self, angle):
        """Set stepper angle from preset button."""
        self.stepper_angle_var.set(angle)
        self.current_angle = angle
        self.stepper_angle_label.config(text=f"{angle}°")
        self.update_stepper_calculation()
        
        # Auto-send in Live Mode
        if self.live_mode_var.get() and self.current_mode == "Stepper Test":
            current_time = time.time()
            if current_time - self.last_publish_time >= self.MIN_PUBLISH_INTERVAL:
                self.send_angle("stepper", quiet=True)
                self.last_publish_time = current_time
        
    def send_angle(self, motor_type, quiet=False):
        """Publish angle command to ROS 2 topic.
        
        Args:
            motor_type: "servo" or "stepper"
            quiet: If True, don't update status label (for Live Mode)
        """
        angle = self.current_angle
        msg = Int32()
        msg.data = angle
        
        if motor_type == "servo":
            self.ros_node.servo_publisher.publish(msg)
            self.ros_node.get_logger().info(f"Published servo angle: {angle}°")
        elif motor_type == "stepper":
            self.ros_node.stepper_publisher.publish(msg)
            self.ros_node.get_logger().info(f"Published stepper angle: {angle}°")
        
        # Visual feedback (only if not in quiet mode)
        if not quiet:
            self.status_label.config(text=f"Sent: {angle}°", foreground="green")
            self.root.after(1000, self.update_connection_status_display)
    
    def on_live_mode_toggle(self):
        """Called when Live Mode checkbox is toggled."""
        if self.live_mode_var.get():
            # Live Mode enabled - disable send button
            if self.current_mode == "Servo Test":
                self.servo_send_button.config(state="disabled")
            else:
                self.stepper_send_button.config(state="disabled")
        else:
            # Live Mode disabled - enable send button
            if self.current_mode == "Servo Test":
                self.servo_send_button.config(state="normal")
            else:
                self.stepper_send_button.config(state="normal")
    
    def check_esp32_connection(self):
        """Check if ESP32 is connected by checking topic subscribers.
        
        Checks the appropriate topic based on current mode.
        """
        try:
            # Determine which topic to check based on current mode
            if self.current_mode == "Servo Test":
                topic_name = '/servo_angle'
            else:
                topic_name = '/stepper_angle'
            
            # First, check if the topic exists
            topic_names_and_types = self.ros_node.get_topic_names_and_types()
            topic_exists = any(topic_name == name for name, _ in topic_names_and_types)
            
            if not topic_exists:
                # Topic doesn't exist, ESP32 is definitely not connected
                self.esp32_connected = False
                return False
            
            # Topic exists, check subscriber count
            # ESP32 subscribes to this topic, so subscribers > 0 means ESP32 is connected
            subscriber_count = self.ros_node.count_subscribers(topic_name)
            self.esp32_connected = subscriber_count > 0
            return self.esp32_connected
            
        except Exception as e:
            # If any check fails, assume disconnected
            # This handles cases where topic disappears, ROS graph changes, or ESP32 disconnects
            self.esp32_connected = False
            return False
    
    def update_connection_status_display(self):
        """Update the connection status display."""
        if self.esp32_connected:
            # Connected - green
            self.connection_indicator.itemconfig(self.connection_circle, fill="green", outline="")
            self.status_label.config(text="Connected", foreground="green")
        else:
            # Disconnected - red
            self.connection_indicator.itemconfig(self.connection_circle, fill="red", outline="")
            self.status_label.config(text="Disconnected", foreground="red")
        
    def update_status(self):
        """Periodically update connection status."""
        # Check if ROS 2 is running
        if not rclpy.ok():
            self.connection_indicator.itemconfig(self.connection_circle, fill="red", outline="")
            self.status_label.config(text="ROS 2 not running", foreground="red")
            self.root.after(2000, self.update_status)
            return
        
        # Check ESP32 connection
        self.check_esp32_connection()
        self.update_connection_status_display()
        
        # Schedule next update (every 2 seconds)
        self.root.after(2000, self.update_status)


class MotorControlNode(Node):
    """ROS 2 node for motor control (servo and stepper)."""
    
    def __init__(self):
        super().__init__('multi_motor_control_gui')
        
        # Create servo publisher
        self.servo_publisher = self.create_publisher(
            Int32,
            '/servo_angle',
            10
        )
        
        # Create stepper publisher
        self.stepper_publisher = self.create_publisher(
            Int32,
            '/stepper_angle',
            10
        )
        
        self.get_logger().info('Multi Motor Control GUI node started')
        self.get_logger().info('Publishing to /servo_angle and /stepper_angle topics')


def spin_ros_node(node):
    """Spin ROS node in separate thread."""
    rclpy.spin(node)


def main(args=None):
    """Main function."""
    # Initialize ROS 2
    rclpy.init(args=args)
    
    # Create ROS node
    ros_node = MotorControlNode()
    
    # Create GUI in main thread
    root = tk.Tk()
    gui = MotorControlGUI(root, ros_node)
    
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
