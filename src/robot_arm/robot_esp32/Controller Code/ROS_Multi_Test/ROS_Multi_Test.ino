#include <micro_ros_arduino.h>

#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <std_msgs/msg/int32.h>
#include <ESP32Servo.h> // Include the servo library
#include <AccelStepper.h>

// --- Configuration ---
// Stepper motor pins (4-pin direct control for ULN2003 or similar drivers)
#define IN1_PIN 14         // GPIO pin for coil 1
#define IN2_PIN 15         // GPIO pin for coil 2
#define IN3_PIN 16         // GPIO pin for coil 3
#define IN4_PIN 17         // GPIO pin for coil 4
// Servo motor pin
#define SERVO_PIN 13       // The pin connected to the servo signal wire (PWM Pin)
// Shared LED pin
#define LED_PIN 2          // LED pin for status indication

// Stepper motor parameters
// As per Half Step Mode Recommendation
#define STEPS_PER_REV 2048  // Steps per motor revolution (0.18° per step)
#define GEAR_RATIO 19       // Gear ratio (19:1 means 19 motor revs = 1 output rev)
#define MAX_SPEED 600       // Maximum speed in steps per second
#define ACCELERATION 60     // Acceleration in steps per second^2

// ROS topic names
#define STEPPER_TOPIC "stepper_angle"
#define SERVO_TOPIC "servo_angle"

// Servo limits
const int MIN_ANGLE = 0;
const int MAX_ANGLE = 180;

// --- Global Stepper Object ---
// Use FULL4WIRE mode for 4-pin direct control (full step)
// Alternative: AccelStepper::HALF4WIRE for half-step mode (more steps, smoother)
AccelStepper stepper(AccelStepper::FULL4WIRE, IN1_PIN, IN3_PIN, IN2_PIN, IN4_PIN);

// --- Position Tracking ---
float steps_per_degree;        // Calculated steps per output degree

// --- Global Servo Object ---
Servo servo1;

// --- Global ROS Objects ---
rcl_subscription_t subscriber_stepper;
rcl_subscription_t subscriber_servo;
std_msgs__msg__Int32 msg_in_stepper; // Message object for stepper topic
std_msgs__msg__Int32 msg_in_servo;   // Message object for servo topic
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- Utility Macros ---
#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){error_loop();}}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){}}

// Function to handle critical errors (flashes LED rapidly)
void error_loop(){
  while(1){
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(100);
  }
}

// --- ROS Subscription Callback for Stepper ---
void stepper_callback(const void * msgin)
{  
  const std_msgs__msg__Int32 * msg = (const std_msgs__msg__Int32 *)msgin;
  int target_angle = msg->data;
  
  // Calculate absolute target position in steps
  long target_steps = (long)(target_angle * steps_per_degree);
  
  // Immediately set new target (non-blocking, allows interruption)
  stepper.moveTo(target_steps);
  
  // Flash LED to indicate movement starting
  digitalWrite(LED_PIN, HIGH);
}

// --- ROS Subscription Callback for Servo ---
void servo_callback(const void * msgin)
{  
  // Cast the incoming message to the correct type
  const std_msgs__msg__Int32 * msg = (const std_msgs__msg__Int32 *)msgin;
  
  // 1. Get the desired angle
  int desired_angle = msg->data;

  // 2. Clamp the angle to the physical limits of the servo (0 to 180 degrees)
  int final_angle = desired_angle;
  if (final_angle < MIN_ANGLE) {
      final_angle = MIN_ANGLE;
  } else if (final_angle > MAX_ANGLE) {
      final_angle = MAX_ANGLE;
  }

  // 3. Move the servo
  servo1.write(final_angle);

  // 4. Provide feedback
  Serial.print("Received Servo Angle: ");
  Serial.print(desired_angle);
  Serial.print(" -> Setting Servo to: ");
  Serial.println(final_angle);

  // Optional: Flash LED briefly to indicate successful message receipt
  digitalWrite(LED_PIN, HIGH);
  delay(10);
  digitalWrite(LED_PIN, LOW);
}


void setup() {
  // Initialize Serial for debugging
  Serial.begin(115200);

  // Configure LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // LED off initially
  
  // --- Stepper Setup ---
  // Calculate steps per output degree
  // steps_per_degree = (steps_per_rev * gear_ratio) / 360
  steps_per_degree = (float)(STEPS_PER_REV * GEAR_RATIO) / 360.0;
  
  // Configure stepper
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setAcceleration(ACCELERATION);
  stepper.setCurrentPosition(0);  // Set current position to 0 steps

  // --- Servo Setup ---
  // Allow allocation of all timers
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  
  // Attach the servo object to the specified pin
  servo1.attach(SERVO_PIN, 500, 2400); // Standard microsecond pulse range for most servos

  // Give time for initialization before starting micro-ROS connection
  delay(2000);

  // --- micro-ROS Setup ---
  set_microros_transports();
  allocator = rcl_get_default_allocator();

  // Create init_options
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

  // Create node
  RCCHECK(rclc_node_init_default(&node, "esp32_multi_motor_node", "", &support));

  // Create subscriber for the stepper angle topic
  RCCHECK(rclc_subscription_init_default(
    &subscriber_stepper,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    STEPPER_TOPIC));
  
  Serial.print("Subscribing to stepper topic: ");
  Serial.println(STEPPER_TOPIC);

  // Create subscriber for the servo angle topic
  RCCHECK(rclc_subscription_init_default(
    &subscriber_servo,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    SERVO_TOPIC));
  
  Serial.print("Subscribing to servo topic: ");
  Serial.println(SERVO_TOPIC);

  // Create executor with 2 subscriptions and add both callbacks
  RCCHECK(rclc_executor_init(&executor, &support.context, 2, &allocator));
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber_stepper, &msg_in_stepper, &stepper_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber_servo, &msg_in_servo, &servo_callback, ON_NEW_DATA));
}

void loop() {
  // Check for new commands without blocking (zero timeout for maximum responsiveness)
  RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(0)));
  
  // Run stepper (CRITICAL: must be called as frequently as possible for smooth movement)
  // This is the equivalent of the while loop in the stable version, but non-blocking
  stepper.run();
  
  // Turn off LED when movement completes
  if (stepper.distanceToGo() == 0 && digitalRead(LED_PIN) == HIGH) {
    digitalWrite(LED_PIN, LOW);
  }
}
