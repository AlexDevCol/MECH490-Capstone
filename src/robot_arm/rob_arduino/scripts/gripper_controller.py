#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import math
import serial

class GripperAngleSender(Node):
    def __init__(self):
        super().__init__('gripper_angle_sender')

        self.joint_name = 'joint_R_gear'  
        self.gear_ratio = 1.0  
        
        self.serial_port = '/dev/ttyACM0'  
        self.baud_rate = 115200  
        self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)

        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10)
        
        self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz (50ms)
        self.current_angle = 90  
        self.last_sent_angle = None  

    def joint_state_callback(self, msg):
        if self.joint_name in msg.name:
            index = msg.name.index(self.joint_name)
            joint_position = msg.position[index]

            gripper_angle_radians = joint_position * self.gear_ratio
            gripper_angle_degrees = gripper_angle_radians * (180 / math.pi)

            self.current_angle = max(0, min(90, int(gripper_angle_degrees)))

    def timer_callback(self):
        # Always log the angle
        self.get_logger().info(f"Current gripper angle: {self.current_angle} deg")

        # Send only if the angle changes by at least 2 degrees
        if self.last_sent_angle is None or abs(self.current_angle - self.last_sent_angle) >= 2:
            try:
                self.ser.write(f"{self.current_angle}\n".encode())
                # self.get_logger().info(f"Sent gripper angle: {self.current_angle} deg")
                self.last_sent_angle = self.current_angle  # Update last sent angle
            except Exception as e:
                self.get_logger().error(f"Serial write error: {e}")

    def __del__(self):
        if self.ser.is_open:
            self.ser.close()

def main(args=None):
    rclpy.init(args=args)
    gripper_angle_sender = GripperAngleSender()
    rclpy.spin(gripper_angle_sender)
    gripper_angle_sender.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()