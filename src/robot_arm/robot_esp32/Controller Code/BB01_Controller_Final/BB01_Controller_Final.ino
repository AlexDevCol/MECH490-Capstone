/**
 * BB01_Controller.ino
 *
 * ESP32 micro-ROS firmware for the BB01 6-DOF robot arm.

 run 
  ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 --baudrate 115200
  ros2 topic pub --once /joint_position_commands std_msgs/msg/Float64MultiArray   "{data: [1.5, 0.5, 0.5, 0.5, 0.5, -1.5]}"
  ros2 topic echo /joint_position_feedback

 *
 * Dual-Core FreeRTOS Architecture:
 *   - Core 0 (ROS Manager): Handles all micro-ROS communications (subscription,
 *     feedback publishing, debug publishing) via a dedicated FreeRTOS task.
 *   - Core 1 (Stepper Worker): Tight loop() executes updateStepper() for all 6
 *     joints with zero blocking, ensuring smooth stepper pulse timing.
 *
 * Subscribes to /joint_position_commands (Float64MultiArray) — 6 joint
 * positions in radians — converts them to stepper steps and drives six
 * stepper motors through ULN2803A Darlington buffers in common-anode
 * wiring using a braking-distance-aware trapezoidal velocity profile driver.
 *
 * Publishes current joint positions on /joint_position_feedback
 * (Float64MultiArray) in radians, allowing the host-side ros2_control
 * hardware interface to close the loop.
 *
 * Hardware:
 *   - 6x NEMA23 steppers via CL42T / CL57T closed-loop drivers
 *   - 2x ULN2803A signal buffers (common anode)
 *   - 1x servo (gripper) on IO4
 *   - Shared ENA on IO16
 *   - Status LED on IO2
 *
 * Thread Safety:
 *   - motors[i].target_pos and motors[i].current_pos are marked volatile
 *     for safe cross-core access (Core 0 writes target_pos, Core 1 reads it;
 *     Core 1 writes current_pos, Core 0 reads it).
 *   - On ESP32 (Xtensa), 32-bit aligned volatile reads/writes are hardware-atomic.
 *
 * Timing Notes:
 *   - micros() wraps every ~71.6 minutes. Unsigned subtraction handles wrap-around
 *     correctly (e.g., if now_us=10 and last_step_us=4294967290, then 10-4294967290=16).
 *   - millis() wraps every ~49 days, also handled correctly by unsigned arithmetic.
 */

 #include <micro_ros_arduino.h>

 #include <stdio.h>
 #include <rcl/rcl.h>
 #include <rcl/error_handling.h>
 #include <rclc/rclc.h>
 #include <rclc/executor.h>
 
 #include <std_msgs/msg/float64_multi_array.h>
 #include <std_msgs/msg/int32.h>
 
 // ─────────────────────────────────────────────
 //  Pin Definitions (from BB01 schematic)
 // ─────────────────────────────────────────────
 
 // Joint stepper pins — DRIVER mode (step, dir)
 // ULN2803A #1 → CL42T drivers (Joints 1-3)
 #define J1_STEP_PIN 12
 #define J1_DIR_PIN  13
 #define J2_STEP_PIN 14
 #define J2_DIR_PIN  15
 #define J3_STEP_PIN 17
 #define J3_DIR_PIN  18
 
 // ULN2803A #2 → CL57T drivers (Joints 4-6)
 // Note: Pins 22-26 are not available on ESP32-S3 (used by flash/PSRAM)
 // Remapped motors 5-6 to GPIO 35-38 (ESP32-S3 compatible)
 #define J4_STEP_PIN 19
 #define J4_DIR_PIN  21
 #define J5_STEP_PIN 35  // Changed from 22 (ESP32-S3 incompatible)
 #define J5_DIR_PIN  36  // Changed from 23 (ESP32-S3 incompatible)
 #define J6_STEP_PIN 37  // Changed from 25 (ESP32-S3 incompatible)
 #define J6_DIR_PIN  38  // Changed from 26 (ESP32-S3 incompatible)
 
 // Shared enable — active via ULN2803A (LOW = enabled on driver)
 #define ENA_PIN   16
 
 // Servo (gripper)
 #define SERVO_PIN 4
 
 // Status LED
 #define LED_PIN   2
 
 // ─────────────────────────────────────────────
 //  Motor Parameters (per joint)
 // ─────────────────────────────────────────────
 //  steps_per_rev: microstep setting on the driver
 //  gear_ratio:    mechanical reduction (motor-revs per output-rev)
 //
 //  Adjust these constants once the physical robot is characterised.
 
 #define NUM_JOINTS 6
 
 // ─────────────────────────────────────────────
 //  Joint Position Limits (OUTPUT shaft, degrees)
 // ─────────────────────────────────────────────
 //  Minimum and maximum joint positions in degrees.
 //  These are converted to radians and steps in setup().
 //  Motion beyond these limits will be prevented.
 
 // Joint limits: [min_deg, max_deg] for each joint
 static const float joint_min_deg[NUM_JOINTS] = {
   -90.0, -90.0, -90.0, -90.0, -90.0, -90.0
 };
 
 static const float joint_max_deg[NUM_JOINTS] = {
   90.0, 90.0, 90.0, 90.0, 90.0, 90.0
 };
 
 // Steps per motor revolution (driver microstep setting)
 static const float steps_per_rev[NUM_JOINTS] = {
   800.0, 800.0, 800.0, 800.0, 800.0, 800.0
 };
 
 // Gear ratio — motor revolutions per output revolution
 static const float gear_ratio[NUM_JOINTS] = {
   23.0, 29.0, 23.0, 19.0, 5.0, 1.0
 };
 
 // ─────────────────────────────────────────────
 //  Motion Limits (OUTPUT shaft, rad/s and rad/s²)
 // ─────────────────────────────────────────────
 //  Specify limits in real-world units here.
 //  They are converted to steps/s and steps/s²
 //  automatically using steps_per_radian[].
 
 // Maximum output velocity per joint (rad/s)
 // Enforced by per-step kinematic speed updates.
 static const float max_velocity_rad[NUM_JOINTS] = {
   0.2, 0.15, 0.2, 0.4, 0.5, 0.5
 };
 
 // Maximum output acceleration per joint (rad/s²)
 static const float max_accel_rad[NUM_JOINTS] = {
   0.5, 0.25, 0.4, 1.0, 1.5, 2.0
 };
 
 // ─────────────────────────────────────────────
 //  Derived quantities (computed in setup())
 // ─────────────────────────────────────────────
 //  steps_per_radian = (steps_per_rev * gear_ratio) / (2 * PI)
 //  max_speed_steps  = max_velocity_rad * steps_per_radian
 //  max_accel_steps  = max_accel_rad    * steps_per_radian
 //  joint_min_steps  = joint_min_deg * (PI/180) * steps_per_radian
 //  joint_max_steps  = joint_max_deg * (PI/180) * steps_per_radian
 
 static float steps_per_radian[NUM_JOINTS];
 static float max_speed_steps[NUM_JOINTS];
 static float max_accel_steps[NUM_JOINTS];
 static long joint_min_steps[NUM_JOINTS];  // Joint limits in steps (from home position)
 static long joint_max_steps[NUM_JOINTS];  // Joint limits in steps (from home position)
 
 // Debug / profiling helpers (ROS topic based, no Serial)
 // Note: last_debug_ms is now local to ros_communications_task() to avoid cross-core access
 static long last_pos_debug[NUM_JOINTS];
 
 // Debug publisher for approximate joint velocities (rad/s)
 rcl_publisher_t    pub_joint_vel_debug;
 std_msgs__msg__Float64MultiArray msg_joint_vel_debug;
 static double joint_vel_debug_data[NUM_JOINTS];
 
 // ─────────────────────────────────────────────
 //  Custom Stepper Motor Driver
 // ─────────────────────────────────────────────
 //  Lightweight trapezoidal velocity profile using
 //  actual step timing (micros()) instead of
 //  programmed intervals.
 
 struct StepperMotor {
   uint8_t step_pin;
   uint8_t dir_pin;
   volatile long current_pos;  // Written by Core 1 (updateStepper), read by Core 0 (feedback/debug)
   volatile long target_pos;   // Written by Core 0 (subscription callback), read by Core 1 (updateStepper)
   float speed;          // current speed (steps/s, always >= 0)
   float max_speed;      // cap (steps/s)
   float accel;          // acceleration (steps/s^2)
   unsigned long last_step_us;  // Unsigned subtraction handles micros() wrap-around (~71.6 min)
   int8_t dir;           // +1 forward, -1 reverse
 };
 
 // Forward declaration
 void updateStepper(StepperMotor& m, int joint_idx);
 
 // ─────────────────────────────────────────────
 //  Stepper Motor instances
 // ─────────────────────────────────────────────
 
 static StepperMotor motors[NUM_JOINTS];
 
 // ─────────────────────────────────────────────
 //  Servo (gripper)
 // ─────────────────────────────────────────────
 
 // Initial gripper position (degrees, 0-180)
 #define GRIPPER_INITIAL_ANGLE 90
 
 // Volatile target angle set by Core 0 (ROS callback), read by Core 1 (loop())
 volatile int gripper_target_angle = GRIPPER_INITIAL_ANGLE;
 
 // --- Native ESP32 LEDC Servo Driver ---
 #define SERVO_FREQ 50
 #define SERVO_RES_BITS 14
 #define SERVO_CHANNEL 0
 
 // Duty cycle limits mapped to 14-bit (0-16383) for 500us to 2400us pulses
 #define SERVO_DUTY_MIN 409
 #define SERVO_DUTY_MAX 1966
 
 void setGripperAngle(int angle) {
   if (angle < 0) angle = 0;
   if (angle > 180) angle = 180;
 
   uint32_t duty = map(angle, 0, 180, SERVO_DUTY_MIN, SERVO_DUTY_MAX);
 
 #if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
   ledcWrite(SERVO_PIN, duty);
 #else
   ledcWrite(SERVO_CHANNEL, duty);
 #endif
 }
 
 // ─────────────────────────────────────────────
 //  micro-ROS objects
 // ─────────────────────────────────────────────
 
 rcl_subscription_t sub_joint_cmd;
 rcl_subscription_t sub_gripper_cmd;
 rcl_publisher_t    pub_joint_fb;
 
 std_msgs__msg__Float64MultiArray msg_joint_cmd;
 std_msgs__msg__Float64MultiArray msg_joint_fb;
 std_msgs__msg__Int32 msg_gripper_cmd;
 
 // Pre-allocated backing arrays for the Float64MultiArray data fields.
 // micro-ROS requires static allocation — no malloc at runtime.
 static double joint_cmd_data[NUM_JOINTS];
 static double joint_fb_data[NUM_JOINTS];
 
 rclc_executor_t executor;
 rclc_support_t  support;
 rcl_allocator_t allocator;
 rcl_node_t      node;
 rcl_timer_t     fb_timer;
 
 // FreeRTOS task handle for ROS communications (Core 0)
 TaskHandle_t RosTaskHandle;
 
 // Feedback publish rate (ms)
 #define FEEDBACK_PERIOD_MS 200
 
 // ─────────────────────────────────────────────
 //  Custom Stepper Motor Driver Implementation
 // ─────────────────────────────────────────────
 
 // Update one stepper motor (braking-distance-aware trapezoidal profile)
 // Uses per-step displacement-based kinematics for loop-rate-independent behavior.
 // Handles mid-flight target changes gracefully by computing braking distance
 // and smoothly decelerating/reversing when needed.
 // Enforces joint position limits to prevent motion beyond physical constraints.
 void updateStepper(StepperMotor& m, int joint_idx) {
   // Read target position (volatile - may be updated by Core 0)
   volatile long target = m.target_pos;
   volatile long current = m.current_pos;
   
   // Enforce joint limits: clamp target to valid range
   if (target < joint_min_steps[joint_idx]) {
     target = joint_min_steps[joint_idx];
     m.target_pos = target;  // Update volatile target to clamped value
   }
   if (target > joint_max_steps[joint_idx]) {
     target = joint_max_steps[joint_idx];
     m.target_pos = target;  // Update volatile target to clamped value
   }
   
   // Safety: also clamp current position if it somehow goes beyond limits
   if (current < joint_min_steps[joint_idx]) {
     current = joint_min_steps[joint_idx];
     m.current_pos = current;
   }
   if (current > joint_max_steps[joint_idx]) {
     current = joint_max_steps[joint_idx];
     m.current_pos = current;
   }
   
   // If at target, stop
   if (current == target) {
     m.speed = 0.0;
     if(m.dir!=0){
       m.dir = 0;
       digitalWrite(m.dir_pin, LOW); //Turn off pin to relieve electrical load
     }
     return;
   }
   
   // Determine desired direction based on current target
   long remaining = target - current;
   int8_t desired_dir = (remaining > 0) ? 1 : -1;
   long remaining_abs = abs(remaining);
   
   // Handle direction reversal: if moving wrong direction, decelerate first
   if (m.dir != 0 && m.dir != desired_dir) {
     // Moving in wrong direction - decelerate at max rate
     // v² = v₀² - 2aΔx (decelerating)
     float v_decel_reverse = sqrt(max(0.0f, m.speed * m.speed - 2.0f * m.accel));
     m.speed = v_decel_reverse;
     
     // If speed drops to minimum, stop and let next iteration handle reversal
     if (m.speed < 10.0) {
       m.speed = 0.0;
       m.dir = 0;
       return;
     }
     // Continue stepping in current direction while decelerating
   } else {
     // Moving in correct direction (or stopped)
     // Update direction pin if changed (only when starting or reversing)
     if (m.dir != desired_dir) {
       m.dir = desired_dir;
       digitalWrite(m.dir_pin, (m.dir > 0) ? HIGH : LOW);
       // Start at minimum speed when direction changes
       if (m.speed < 10.0) {
         m.speed = 10.0;
       }
     }
   }
   
   // If speed is 0 and we're not at target, start moving
   if (m.speed <= 0.0 && current != target) {
     m.speed = 10.0;  // Minimum speed to avoid stalling
   }
   
   // Compute step interval from current speed
   unsigned long step_interval_us = (unsigned long)(1000000.0 / m.speed);
   
   // Check if it's time to step
   unsigned long now_us = micros();
   // Unsigned subtraction handles micros() wrap-around correctly (~71.6 min period)
   unsigned long elapsed_us = now_us - m.last_step_us;
   
   if (elapsed_us >= step_interval_us) {
     // Pulse step pin (minimum 3us HIGH per CL42T/CL57T spec)
     digitalWrite(m.step_pin, HIGH);
     delayMicroseconds(3);  // 3us is very short, acceptable blocking
     digitalWrite(m.step_pin, LOW);
     
     // Update position (volatile write - Core 0 reads this)
     m.current_pos += m.dir;
     current = m.current_pos;  // Update local copy
     
     // Update last_step_us
     m.last_step_us = now_us;
     
     // Re-read target in case it changed mid-step (volatile read)
     target = m.target_pos;
     remaining = target - current;
     remaining_abs = abs(remaining);
     
     // If we've reached target, stop
     if (remaining_abs == 0) {
       m.speed = 0.0;
       m.dir = 0;
       return;
     }
     
     // Recompute desired direction (may have changed)
     desired_dir = (remaining > 0) ? 1 : -1;
     
     // If moving in wrong direction, continue decelerating
     if (m.dir != 0 && m.dir != desired_dir) {
       float v_decel_reverse = sqrt(max(0.0f, m.speed * m.speed - 2.0f * m.accel));
       m.speed = v_decel_reverse;
       if (m.speed < 10.0) {
         m.speed = 0.0;
         m.dir = 0;
       }
       return;
     }
     
     // Moving in correct direction - compute braking distance
     // d_brake = v² / (2a) - minimum distance needed to stop
     float d_brake = (m.speed * m.speed) / (2.0f * m.accel);
     
     if (remaining_abs <= d_brake) {
       // Within braking zone - decelerate to stop at target
       // v² = 2ad, solve for v: v = sqrt(2ad)
       m.speed = sqrt(2.0f * m.accel * (float)remaining_abs);
       // Ensure minimum speed while still moving
       if (m.speed < 10.0 && remaining_abs > 0) {
         m.speed = 10.0;
       }
     } else {
       // Outside braking zone - accelerate or cruise
       // Speed after accelerating for 1 step: v² = v₀² + 2a
       float v_accel = sqrt(m.speed * m.speed + 2.0f * m.accel);
       // Cap at max speed
       m.speed = min(v_accel, m.max_speed);
     }
   }
   // If not time to step yet, return without updating speed
   // Speed only changes when a step actually occurs
 }
 
 // ─────────────────────────────────────────────
 //  Utility macros
 // ─────────────────────────────────────────────
 
 #define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if (temp_rc != RCL_RET_OK) { error_loop(); } }
 #define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if (temp_rc != RCL_RET_OK) { /* non-fatal */ } }
 
 void error_loop() {
   while (1) {
     digitalWrite(LED_PIN, !digitalRead(LED_PIN));
     delay(100);
   }
 }
 
 // ─────────────────────────────────────────────
 //  FreeRTOS Task: ROS Communications (Core 0)
 // ─────────────────────────────────────────────
 
 void ros_communications_task(void *pvParameters) {
   (void)pvParameters;
   
   unsigned long last_debug_publish_ms = 0;
   
   for (;;) {
     // Spin the micro-ROS executor - handles subscription callbacks and timer callbacks
     // This processes incoming /joint_position_commands and triggers feedback_timer_callback
     RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(0)));
     
     // Handle 1-second debug velocity publisher (moved from loop())
     unsigned long now_ms = millis();
     // Unsigned subtraction handles millis() wrap-around correctly (~49 days)
     if (now_ms - last_debug_publish_ms >= 1000) {
       last_debug_publish_ms = now_ms;
       
       for (int i = 0; i < NUM_JOINTS; i++) {
         // Read current position (volatile - written by Core 1)
         volatile long pos = motors[i].current_pos;
         long delta = pos - last_pos_debug[i];
         last_pos_debug[i] = pos;
         
         // J5 (index 4) is not inverted - use original direction
         double rad_per_s = (steps_per_radian[i] > 0.0)
                              ? ((i == 4) ? ((double)delta / steps_per_radian[i]) : (-(double)delta / steps_per_radian[i]))
                              : 0.0;
         joint_vel_debug_data[i] = rad_per_s;
       }
       
       // Publish approximate velocities (rad/s) for all joints
       RCSOFTCHECK(rcl_publish(&pub_joint_vel_debug, &msg_joint_vel_debug, NULL));
     }
     
     // Yield to FreeRTOS scheduler
     vTaskDelay(1);
   }
 }
 
 // ─────────────────────────────────────────────
 //  Subscription callback — joint commands
 // ─────────────────────────────────────────────
 
 void joint_cmd_callback(const void *msgin) {
   const std_msgs__msg__Float64MultiArray *msg =
       (const std_msgs__msg__Float64MultiArray *)msgin;
 
   // Safety: only process if we received exactly NUM_JOINTS values
   if (msg->data.size != NUM_JOINTS) return;
 
   for (int i = 0; i < NUM_JOINTS; i++) {
     double target_rad = msg->data.data[i];
     // J5 (index 4) is not inverted - use original direction
     long target_steps = (i == 4) ? (long)(target_rad * steps_per_radian[i]) : (long)(-target_rad * steps_per_radian[i]);
     motors[i].target_pos = target_steps;
   }
 
   // Flash LED to indicate command received
   digitalWrite(LED_PIN, HIGH);
 }
 
 // ─────────────────────────────────────────────
 //  Subscription callback — gripper commands
 // ─────────────────────────────────────────────
 
 void gripper_cmd_callback(const void *msgin) {
   const std_msgs__msg__Int32 *msg =
       (const std_msgs__msg__Int32 *)msgin;
 
   // Clamp angle to valid servo range (0-180 degrees)
   int angle = msg->data;
   if (angle < 0) angle = 0;
   if (angle > 180) angle = 180;
 
   // Set volatile target (Core 1 will read this and actuate)
   gripper_target_angle = angle;
 }
 
 // ─────────────────────────────────────────────
 //  Timer callback — publish feedback
 // ─────────────────────────────────────────────
 
 void feedback_timer_callback(rcl_timer_t *timer, int64_t last_call_time) {
   (void)last_call_time;
   if (timer == NULL) return;
 
   for (int i = 0; i < NUM_JOINTS; i++) {
     // J5 (index 4) is not inverted - use original direction
     joint_fb_data[i] = (i == 4) ? ((double)motors[i].current_pos / steps_per_radian[i]) : (-(double)motors[i].current_pos / steps_per_radian[i]);
   }
 
   RCSOFTCHECK(rcl_publish(&pub_joint_fb, &msg_joint_fb, NULL));
 }
 
 // ─────────────────────────────────────────────
 //  setup()
 // ─────────────────────────────────────────────
 
 void setup() {
   Serial.begin(115200);
 
   // --- Pin setup ---
   pinMode(LED_PIN, OUTPUT);
   digitalWrite(LED_PIN, LOW);
 
   pinMode(ENA_PIN, OUTPUT);
   digitalWrite(ENA_PIN, HIGH);  // Enable drivers (active through ULN2803A)
 
   // --- Compute per-joint derived quantities ---
   for (int i = 0; i < NUM_JOINTS; i++) {
     steps_per_radian[i] = (steps_per_rev[i] * gear_ratio[i]) / (2.0 * PI);
     max_speed_steps[i]  = max_velocity_rad[i] * steps_per_radian[i];
     max_accel_steps[i]  = max_accel_rad[i]    * steps_per_radian[i];
     
     // Convert joint limits from degrees to steps (relative to home position at 0)
     float min_rad = joint_min_deg[i] * (PI / 180.0);
     float max_rad = joint_max_deg[i] * (PI / 180.0);
     // J5 (index 4) is not inverted - use original direction
     if (i == 4) {
       joint_min_steps[i] = (long)(min_rad * steps_per_radian[i]);
       joint_max_steps[i] = (long)(max_rad * steps_per_radian[i]);
     } else {
       joint_min_steps[i] = (long)(-max_rad * steps_per_radian[i]);  // Swap and negate
       joint_max_steps[i] = (long)(-min_rad * steps_per_radian[i]);  // Swap and negate
     }
 
     // Initialise debug tracking
     last_pos_debug[i] = 0;
   }
 
   // --- Configure stepper motors ---
   // Pin assignments per joint
   uint8_t step_pins[NUM_JOINTS] = {J1_STEP_PIN, J2_STEP_PIN, J3_STEP_PIN, J4_STEP_PIN, J5_STEP_PIN, J6_STEP_PIN};
   uint8_t dir_pins[NUM_JOINTS]  = {J1_DIR_PIN,  J2_DIR_PIN,  J3_DIR_PIN,  J4_DIR_PIN,  J5_DIR_PIN,  J6_DIR_PIN};
   
   for (int i = 0; i < NUM_JOINTS; i++) {
     // Initialize pin modes
     pinMode(step_pins[i], OUTPUT);
     pinMode(dir_pins[i], OUTPUT);
     digitalWrite(step_pins[i], LOW);
     digitalWrite(dir_pins[i], LOW);
     
     // Initialize motor struct
     motors[i].step_pin = step_pins[i];
     motors[i].dir_pin = dir_pins[i];
     motors[i].current_pos = 0;
     motors[i].target_pos = 0;
     motors[i].speed = 0.0;
     motors[i].max_speed = max_speed_steps[i];
     motors[i].accel = max_accel_steps[i];
     motors[i].last_step_us = micros();
     motors[i].dir = 0;
   }
 
   // --- Configure servo (Native LEDC) ---
#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
   ledcAttach(SERVO_PIN, SERVO_FREQ, SERVO_RES_BITS);
#else
   ledcSetup(SERVO_CHANNEL, SERVO_FREQ, SERVO_RES_BITS);
   ledcAttachPin(SERVO_PIN, SERVO_CHANNEL);
#endif

   setGripperAngle(GRIPPER_INITIAL_ANGLE);
 
   // Allow hardware to stabilise before micro-ROS init
   delay(2000);
 
   // --- micro-ROS transport ---
   set_microros_transports();
   allocator = rcl_get_default_allocator();
 
   // --- Support & node ---
   RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
   RCCHECK(rclc_node_init_default(&node, "esp32_bb01_node", "", &support));
 
   // --- Pre-allocate Float64MultiArray buffers ---
   // Command message (incoming)
   msg_joint_cmd.data.data     = joint_cmd_data;
   msg_joint_cmd.data.size     = NUM_JOINTS;
   msg_joint_cmd.data.capacity = NUM_JOINTS;
 
   // Feedback message (outgoing)
   msg_joint_fb.data.data     = joint_fb_data;
   msg_joint_fb.data.size     = NUM_JOINTS;
   msg_joint_fb.data.capacity = NUM_JOINTS;
 
   // Debug velocity message (outgoing)
   msg_joint_vel_debug.data.data     = joint_vel_debug_data;
   msg_joint_vel_debug.data.size     = NUM_JOINTS;
   msg_joint_vel_debug.data.capacity = NUM_JOINTS;
 
   // --- Subscriber: /joint_position_commands ---
   RCCHECK(rclc_subscription_init_default(
       &sub_joint_cmd,
       &node,
       ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
       "/joint_position_commands"));
 
   // --- Subscriber: /gripper_angle ---
   RCCHECK(rclc_subscription_init_default(
       &sub_gripper_cmd,
       &node,
       ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
       "/gripper_angle"));
 
   // --- Publisher: /joint_position_feedback ---
   RCCHECK(rclc_publisher_init_default(
       &pub_joint_fb,
       &node,
       ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
       "/joint_position_feedback"));
 
   // --- Publisher: /joint_velocity_debug ---
   RCCHECK(rclc_publisher_init_default(
       &pub_joint_vel_debug,
       &node,
       ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float64MultiArray),
       "/joint_velocity_debug"));
 
   // --- Timer for periodic feedback publishing ---
   RCCHECK(rclc_timer_init_default(
       &fb_timer,
       &support,
       RCL_MS_TO_NS(FEEDBACK_PERIOD_MS),
       feedback_timer_callback));
 
   // --- Executor: 2 subscriptions + 1 timer ---
   RCCHECK(rclc_executor_init(&executor, &support.context, 3, &allocator));
   RCCHECK(rclc_executor_add_subscription(
       &executor, &sub_joint_cmd, &msg_joint_cmd,
       &joint_cmd_callback, ON_NEW_DATA));
   RCCHECK(rclc_executor_add_subscription(
       &executor, &sub_gripper_cmd, &msg_gripper_cmd,
       &gripper_cmd_callback, ON_NEW_DATA));
   RCCHECK(rclc_executor_add_timer(&executor, &fb_timer));
   
   // --- Create FreeRTOS task for ROS communications on Core 0 ---
   // This task handles all micro-ROS processing, leaving Core 1's loop()
   // free for uninterrupted stepper motor control.
   xTaskCreatePinnedToCore(
       ros_communications_task,  // Task function
       "ROS_Task",               // Task name
       8192,                     // Stack size (bytes) - sufficient for micro-ROS serial I/O
       NULL,                     // Parameters
       1,                        // Priority (same as default Arduino loop)
       &RosTaskHandle,           // Task handle
       0);                       // Pin to Core 0
 }
 
 // ─────────────────────────────────────────────
 //  loop()
 // ─────────────────────────────────────────────
 
 void loop() {
   // ── Core 1: Tight stepper control loop — zero blocking, no micro-ROS overhead ──
   // All micro-ROS processing (subscription, feedback publishing, debug publishing)
   // is handled by ros_communications_task() on Core 0.
   
   // Update all 6 stepper motors
   for (int i = 0; i < NUM_JOINTS; i++) {
     updateStepper(motors[i], i);
   }
 
   // ── Gripper actuation: read target from Core 0 and update servo ──
   static int last_gripper_angle = -1;  // Track last set angle to avoid redundant writes
   volatile int gripper_target = gripper_target_angle;  // Read volatile variable (set by Core 0)
   if (gripper_target != last_gripper_angle) {
     setGripperAngle(gripper_target);
     last_gripper_angle = gripper_target;
   }
 
   // ── LED: turn off when all joints have reached their targets ──
   bool all_arrived = true;
   for (int i = 0; i < NUM_JOINTS; i++) {
     // Read target and current positions (volatile - may be updated by Core 0)
     volatile long target = motors[i].target_pos;
     volatile long current = motors[i].current_pos;
     if (target != current) {
       all_arrived = false;
       break;
     }
   }
   if (all_arrived && digitalRead(LED_PIN) == HIGH) {
     digitalWrite(LED_PIN, LOW);
   }
 }
 