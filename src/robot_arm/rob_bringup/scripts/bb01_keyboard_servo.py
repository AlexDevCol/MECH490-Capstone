#!/usr/bin/env python3
"""
Keyboard input node for MoveIt Servo control of bb01 robot.

This script provides keyboard controls for realtime servo control of the bb01 robot.
It queries joint names dynamically from the move_group, making it robot-agnostic.

Usage:
    python3 bb01_keyboard_servo.py

Keyboard Controls:
    Cartesian (Twist) Mode:
        i/k: Move end-effector forward/backward (X-axis)
        j/l: Move end-effector left/right (Y-axis)
        u/o: Move end-effector up/down (Z-axis)
        y/h: Rotate about X-axis (roll)
        t/g: Rotate about Y-axis (pitch)
        r/f: Rotate about Z-axis (yaw)
    
    Joint Jog Mode:
        1-6: Jog individual joints (joint_1 through joint_6)
        +/-: Increase/decrease jog speed
    
    Mode Switching:
        t: Switch to Twist (Cartesian) mode
        j: Switch to Joint Jog mode
        w/e: Switch command frame (planning frame / end-effector frame)
        q/Q: Quit

:author: MECH490-Capstone Team
:date: February 2026
"""

import sys
import select
import termios
import tty
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import JointState
from control_msgs.msg import JointJog
from moveit_msgs.srv import ServoCommandType


class KeyboardServoInput(Node):
    """Keyboard input node for MoveIt Servo control."""
    
    # Command type constants
    JOINT_JOG = 0
    TWIST = 1
    POSE = 2
    
    def __init__(self):
        super().__init__('bb01_keyboard_servo')
        
        # Declare parameters
        self.declare_parameter('move_group_name', 'arm')
        self.declare_parameter('planning_frame', 'world')
        self.declare_parameter('servo_node_name', 'servo_node')
        
        # Get parameters
        self.move_group_name = self.get_parameter('move_group_name').value
        self.planning_frame = self.get_parameter('planning_frame').value
        self.servo_node_name = self.get_parameter('servo_node_name').value
        
        # use_sim_time is a standard ROS 2 parameter that can be set via command line
        # We don't need to declare it explicitly - it's handled automatically by ROS 2
        
        # Publishers
        self.twist_pub = self.create_publisher(
            TwistStamped,
            f'/{self.servo_node_name}/delta_twist_cmds',
            10
        )
        
        self.joint_jog_pub = self.create_publisher(
            JointJog,
            f'/{self.servo_node_name}/delta_joint_cmds',
            10
        )
        
        # Service client for switching command type
        self.switch_command_client = self.create_client(
            ServoCommandType,
            f'/{self.servo_node_name}/switch_command_type'
        )
        
        # Wait for service to be available
        self.get_logger().info(f'Waiting for service /{self.servo_node_name}/switch_command_type...')
        if not self.switch_command_client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error(f'Service /{self.servo_node_name}/switch_command_type not available!')
            sys.exit(1)
        
        # Subscribe to joint_states to get joint names dynamically
        self.joint_names = []
        self.joint_states_received = False
        self.joint_states_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_states_callback,
            10
        )
        
        # Wait for joint states to get joint names
        self.get_logger().info('Waiting for joint_states to get joint names...')
        timeout = 10.0
        start_time = self.get_clock().now()
        while not self.joint_states_received and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if (self.get_clock().now() - start_time).nanoseconds / 1e9 > timeout:
                self.get_logger().error('Timeout waiting for joint_states!')
                self.get_logger().error('Make sure robot_state_publisher and joint_state_broadcaster are running!')
                # Fallback to known bb01 joint names
                self.joint_names = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6']
                self.get_logger().warn(f'Using fallback joint names: {self.joint_names}')
                break
        
        if self.joint_names:
            self.get_logger().info(f'Found {len(self.joint_names)} joints: {self.joint_names}')
        else:
            self.get_logger().error('No joint names available!')
            sys.exit(1)
        
        # State variables
        self.current_command_type = self.TWIST  # Start in Twist mode
        self.command_frame = self.planning_frame  # Start with planning frame
        self.joint_speed = 0.1  # Default joint jog speed
        self.cartesian_speed = 0.1  # Default Cartesian speed
        
        # Switch to Twist mode initially
        self.switch_command_type(self.TWIST)
        
        # Save terminal settings
        self.settings = termios.tcgetattr(sys.stdin)
        
        self.get_logger().info('Keyboard servo input node initialized')
        self.print_instructions()
    
    def joint_states_callback(self, msg):
        """Callback to get joint names from joint_states."""
        if not self.joint_states_received and msg.name:
            # Filter to only include joints from the move group
            # For bb01, we expect joint_1 through joint_6
            self.joint_names = [name for name in msg.name if name.startswith('joint_')]
            self.joint_names.sort()  # Sort to ensure consistent order
            self.joint_states_received = True
            self.get_logger().info(f'Received joint names from joint_states: {self.joint_names}')
    
    def print_instructions(self):
        """Print keyboard control instructions."""
        print('\n' + '='*60)
        print('BB01 Keyboard Servo Control')
        print('='*60)
        print('\nAll commands are in the planning frame')
        print('\nCartesian (Twist) Mode:')
        print('  i/k: Move end-effector forward/backward (X-axis)')
        print('  j/l: Move end-effector left/right (Y-axis)')
        print('  u/o: Move end-effector up/down (Z-axis)')
        print('  y/h: Rotate about X-axis (roll)')
        print('  t/g: Rotate about Y-axis (pitch)')
        print('  r/f: Rotate about Z-axis (yaw)')
        print('\nJoint Jog Mode:')
        for i, joint_name in enumerate(self.joint_names, 1):
            print(f'  {i}: Jog {joint_name}')
        print('  +/-: Increase/decrease jog speed')
        print('\nMode Switching:')
        print('  t: Switch to Twist (Cartesian) mode')
        print('  j: Switch to Joint Jog mode')
        print('  w/e: Switch command frame (planning frame / end-effector frame)')
        print('  q/Q: Quit')
        print('\n' + '='*60 + '\n')
    
    def switch_command_type(self, command_type):
        """Switch the servo command type."""
        request = ServoCommandType.Request()
        request.command_type = command_type
        
        future = self.switch_command_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        
        if future.done():
            try:
                response = future.result()
                if response.success:
                    self.current_command_type = command_type
                    mode_name = ['JointJog', 'Twist', 'Pose'][command_type]
                    self.get_logger().info(f'Switched to input type: {mode_name}')
                    return True
                else:
                    self.get_logger().warn('Failed to switch command type')
                    return False
            except Exception as e:
                self.get_logger().error(f'Exception while switching command type: {e}')
                return False
        else:
            self.get_logger().warn('Service call timed out')
            return False
    
    def get_key(self):
        """Get a single keypress from stdin."""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None
    
    def publish_twist(self, linear_x=0.0, linear_y=0.0, linear_z=0.0,
                     angular_x=0.0, angular_y=0.0, angular_z=0.0):
        """Publish a twist command."""
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.command_frame
        msg.twist.linear.x = linear_x * self.cartesian_speed
        msg.twist.linear.y = linear_y * self.cartesian_speed
        msg.twist.linear.z = linear_z * self.cartesian_speed
        msg.twist.angular.x = angular_x * self.cartesian_speed
        msg.twist.angular.y = angular_y * self.cartesian_speed
        msg.twist.angular.z = angular_z * self.cartesian_speed
        self.twist_pub.publish(msg)
    
    def publish_joint_jog(self, joint_index, direction):
        """Publish a joint jog command."""
        if joint_index < 0 or joint_index >= len(self.joint_names):
            return
        
        msg = JointJog()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.planning_frame
        msg.joint_names = [self.joint_names[joint_index]]
        # For unitless command type, use velocities instead of displacements
        msg.velocities = [direction * self.joint_speed]
        self.joint_jog_pub.publish(msg)
    
    def run(self):
        """Main loop for keyboard input."""
        # Set terminal to raw mode
        tty.setraw(sys.stdin.fileno())
        
        try:
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.1)
                
                key = self.get_key()
                if key is None:
                    continue
                
                # Handle quit
                if key == 'q' or key == 'Q':
                    print('\nQuitting...')
                    break
                
                # Handle mode switching
                if key == 't':
                    self.switch_command_type(self.TWIST)
                    print('Mode: Twist (Cartesian)')
                    continue
                elif key == 'j':
                    self.switch_command_type(self.JOINT_JOG)
                    print('Mode: Joint Jog')
                    continue
                
                # Handle frame switching (only in Twist mode)
                if self.current_command_type == self.TWIST:
                    if key == 'w':
                        self.command_frame = self.planning_frame
                        self.get_logger().info(f'Command frame set to: {self.command_frame}')
                        continue
                    elif key == 'e':
                        # Use end-effector link (link_6 for bb01)
                        # Could query from move_group service, but for now use known link
                        self.command_frame = 'link_6'  # bb01's end-effector link
                        self.get_logger().info(f'Command frame set to: {self.command_frame}')
                        continue
                
                # Handle commands based on current mode
                if self.current_command_type == self.TWIST:
                    # Cartesian (Twist) commands
                    if key == 'i':
                        self.publish_twist(linear_x=1.0)
                    elif key == 'k':
                        self.publish_twist(linear_x=-1.0)
                    elif key == 'j':
                        self.publish_twist(linear_y=1.0)
                    elif key == 'l':
                        self.publish_twist(linear_y=-1.0)
                    elif key == 'u':
                        self.publish_twist(linear_z=1.0)
                    elif key == 'o':
                        self.publish_twist(linear_z=-1.0)
                    elif key == 'y':
                        self.publish_twist(angular_x=1.0)
                    elif key == 'h':
                        self.publish_twist(angular_x=-1.0)
                    elif key == 't':
                        self.publish_twist(angular_y=1.0)
                    elif key == 'g':
                        self.publish_twist(angular_y=-1.0)
                    elif key == 'r':
                        self.publish_twist(angular_z=1.0)
                    elif key == 'f':
                        self.publish_twist(angular_z=-1.0)
                
                elif self.current_command_type == self.JOINT_JOG:
                    # Joint jog commands
                    if key in ['1', '2', '3', '4', '5', '6']:
                        joint_index = int(key) - 1
                        if joint_index < len(self.joint_names):
                            self.publish_joint_jog(joint_index, 1.0)
                    elif key == '+':
                        self.joint_speed = min(1.0, self.joint_speed + 0.1)
                        print(f'Joint speed: {self.joint_speed:.1f}')
                    elif key == '-':
                        self.joint_speed = max(0.1, self.joint_speed - 0.1)
                        print(f'Joint speed: {self.joint_speed:.1f}')
        
        except KeyboardInterrupt:
            print('\nInterrupted by user')
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
            print('Terminal restored')


def main(args=None):
    """Main function."""
    rclpy.init(args=args)
    
    try:
        node = KeyboardServoInput()
        node.run()
    except Exception as e:
        print(f'Error: {e}')
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
