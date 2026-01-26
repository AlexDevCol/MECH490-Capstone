#include <micro_ros_arduino.h>

#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <std_msgs/msg/int32.h>
#include <ESP32Servo.h> // Include the servo library

// --- Configuration ---
#define LED_PIN 2      // Use a separate pin for LED status (e.g., GPIO 2)
#define SERVO_PIN 13   // The pin connected to the servo signal wire (PWM Pin)
#define ROS_TOPIC_NAME "servo_angle"

// --- Global ROS Objects ---
rcl_subscription_t subscriber;
std_msgs__msg__Int32 msg_in; // Message object to store incoming data
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

// --- Global Servo Object ---
Servo servo1;
const int MIN_ANGLE = 0;
const int MAX_ANGLE = 180;

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
  Serial.print("Received Angle: ");
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
  RCCHECK(rclc_node_init_default(&node, "esp32_servo_node", "", &support));

  // Create subscriber for the servo angle topic
  RCCHECK(rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    ROS_TOPIC_NAME));
  
  Serial.print("Subscribing to topic: ");
  Serial.println(ROS_TOPIC_NAME);

  // Create executor and add the subscription callback
  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber, &msg_in, &subscription_callback, ON_NEW_DATA));
}

void loop() {
  // Spin the executor to check for incoming messages and execute callbacks
  RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100)));
  delay(10); // Small delay to avoid busy looping
}
