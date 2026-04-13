#include <micro_ros_arduino.h>

#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <std_msgs/msg/int32.h>
#include <AccelStepper.h>

// --- Configuration ---
// 4-pin direct control (for ULN2003 or similar drivers)
#define IN1_PIN 14         // GPIO pin for coil 1
#define IN2_PIN 15         // GPIO pin for coil 2
#define IN3_PIN 16         // GPIO pin for coil 3
#define IN4_PIN 17         // GPIO pin for coil 4
#define LED_PIN 2          // LED pin for status indication
//As per Half Step Mode Recommendation
#define STEPS_PER_REV 2048  // Steps per motor revolution (0.18° per step)
#define GEAR_RATIO 19      // Gear ratio (19:1 means 19 motor revs = 1 output rev)
#define MAX_SPEED 600     // Maximum speed in steps per second
#define ACCELERATION 60   // Acceleration in steps per second^2
#define ROS_TOPIC_NAME "stepper_angle"

// --- Global Stepper Object ---
// Use FULL4WIRE mode for 4-pin direct control (full step)
// Alternative: AccelStepper::HALF4WIRE for half-step mode (more steps, smoother)
AccelStepper stepper(AccelStepper::FULL4WIRE, IN1_PIN, IN3_PIN, IN2_PIN, IN4_PIN);

// --- Position Tracking ---
float current_position = 0.0;  // Current position in degrees
float steps_per_degree;        // Calculated steps per output degree

// --- Global ROS Objects ---
rcl_subscription_t subscriber;
std_msgs__msg__Int32 msg_in; // Message object to store incoming data
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

// --- ROS Subscription Callback ---
void subscription_callback(const void * msgin)
{  
  const std_msgs__msg__Int32 * msg = (const std_msgs__msg__Int32 *)msgin;
  int target_angle = msg->data;
  
  // Call existing move_to_angle function
  move_to_angle((float)target_angle);
}

// --- Function to calculate steps from angle delta ---
long calculate_steps(float angle_delta) {
  // Convert angle delta to steps
  // steps = angle_delta * (steps_per_rev * gear_ratio) / 360
  return (long)(angle_delta * steps_per_degree);
}

// --- Function to move stepper to target angle ---
void move_to_angle(float target_angle) {
  // Calculate angle delta
  float delta_angle = target_angle - current_position;
  
  // Calculate steps needed
  long steps = calculate_steps(delta_angle);
  
  // Move stepper
  if (steps != 0) {
    stepper.move(steps);
    
    // Flash LED to indicate movement starting
    digitalWrite(LED_PIN, HIGH);
    
    // Wait for movement to complete
    while (stepper.distanceToGo() != 0) {
      stepper.run();
    }
    
    // Update current position
    current_position = target_angle;
    
    // Turn off LED
    digitalWrite(LED_PIN, LOW);
  }
}

void setup() {
  // Configure LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Calculate steps per output degree
  // steps_per_degree = (steps_per_rev * gear_ratio) / 360
  steps_per_degree = (float)(STEPS_PER_REV * GEAR_RATIO) / 360.0;
  
  // Configure stepper
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setAcceleration(ACCELERATION);
  stepper.setCurrentPosition(0);  // Set current position to 0 steps
  
  // --- micro-ROS Setup ---
  delay(2000);  // Give time for initialization before starting micro-ROS connection
  set_microros_transports();
  allocator = rcl_get_default_allocator();

  // Create init_options
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

  // Create node
  RCCHECK(rclc_node_init_default(&node, "esp32_stepper_node", "", &support));

  // Create subscriber for the stepper angle topic
  RCCHECK(rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    ROS_TOPIC_NAME));

  // Create executor and add the subscription callback
  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber, &msg_in, &subscription_callback, ON_NEW_DATA));
}

void loop() {
  // Spin ROS executor to check for incoming messages
  RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100)));
  
  // Run stepper (needed for movement execution)
  stepper.run();
  
  // Small delay to avoid busy looping
  delay(1);
}
