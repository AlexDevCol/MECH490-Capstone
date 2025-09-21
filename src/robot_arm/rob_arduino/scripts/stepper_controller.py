#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import serial
import math

class StepperController(Node):
    def __init__(self):
        super().__init__('stepper_angle_controller')

        # Define joint names
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']

        self.serial_port = '/dev/ttyACM0'  
        self.baud_rate = 115200
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            self.get_logger().info(f"Connected to serial: {self.serial_port}")
        except serial.SerialException as e:
            self.get_logger().error(f"Failed to open serial port: {e}")
            self.ser = None

        # Subscribe to joint states
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states', 
            self.joint_state_callback,
            10)

    def joint_state_callback(self, msg):
        angles = {}

        for joint_name in self.joint_names:
            if joint_name in msg.name:
                index = msg.name.index(joint_name)
                joint_position = msg.position[index]

                # Convert radians to degrees
                angle_degrees = int(math.degrees(joint_position))
                angles[joint_name] = angle_degrees

        if angles and self.ser:
            command = ','.join([f"{angles[joint]}" for joint in self.joint_names if joint in angles])
            command += "\n"  # Add newline for serial parsing
            self.ser.write(command.encode())

            self.get_logger().info(f"Sent angles: {command.strip()}")

    def __del__(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

def main(args=None):
    rclpy.init(args=args)
    stepper_controller = StepperController()
    rclpy.spin(stepper_controller)
    stepper_controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()