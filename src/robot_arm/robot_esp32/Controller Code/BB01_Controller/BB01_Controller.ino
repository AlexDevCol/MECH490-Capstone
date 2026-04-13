/**
 * BB01_Controller.ino
 *
 * ESP32 micro-ROS firmware for the BB01 6-DOF robot arm.
 *
 * Subscribes to /joint_position_commands (Float64MultiArray) — 6 joint
 * positions in radians — converts them to stepper steps and drives six
 * stepper motors through ULN2803A Darlington buffers in common-anode
 * wiring using a custom trapezoidal velocity profile driver.
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
 */

#include <micro_ros_arduino.h>

#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <std_msgs/msg/float64_multi_array.h>
#include <ESP32Servo.h>

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

// Steps per motor revolution (driver microstep setting)
static const float steps_per_rev[NUM_JOINTS] = {
  800.0, 800.0, 800.0, 800.0, 800.0, 800.0
};

// Gear ratio — motor revolutions per output revolution
static const float gear_ratio[NUM_JOINTS] = {
  23.0, 23.0, 19.0, 19.0, 5.0, 1.0
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
  0.3, 0.3, 0.3, 0.3, 0.3, 0.3
};

// Maximum output acceleration per joint (rad/s²)
static const float max_accel_rad[NUM_JOINTS] = {
  2.4, 0.7, 2.4, 2.4, 2.4, 2.4
};

// ─────────────────────────────────────────────
//  Derived quantities (computed in setup())
// ─────────────────────────────────────────────
//  steps_per_radian = (steps_per_rev * gear_ratio) / (2 * PI)
//  max_speed_steps  = max_velocity_rad * steps_per_radian
//  max_accel_steps  = max_accel_rad    * steps_per_radian

static float steps_per_radian[NUM_JOINTS];
static float max_speed_steps[NUM_JOINTS];
static float max_accel_steps[NUM_JOINTS];

// Debug / profiling helpers (ROS topic based, no Serial)
static unsigned long last_debug_ms = 0;
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
  long current_pos;
  long target_pos;
  float speed;          // current speed (steps/s, always >= 0)
  float max_speed;      // cap (steps/s)
  float accel;          // acceleration (steps/s^2)
  unsigned long last_step_us;
  int8_t dir;           // +1 forward, -1 reverse
};

// Forward declaration
void updateStepper(StepperMotor& m);

// ─────────────────────────────────────────────
//  Stepper Motor instances
// ─────────────────────────────────────────────

static StepperMotor motors[NUM_JOINTS];

// ─────────────────────────────────────────────
//  Servo (gripper)
// ─────────────────────────────────────────────

Servo gripper;

// ─────────────────────────────────────────────
//  micro-ROS objects
// ─────────────────────────────────────────────

rcl_subscription_t sub_joint_cmd;
rcl_publisher_t    pub_joint_fb;

std_msgs__msg__Float64MultiArray msg_joint_cmd;
std_msgs__msg__Float64MultiArray msg_joint_fb;

// Pre-allocated backing arrays for the Float64MultiArray data fields.
// micro-ROS requires static allocation — no malloc at runtime.
static double joint_cmd_data[NUM_JOINTS];
static double joint_fb_data[NUM_JOINTS];

rclc_executor_t executor;
rclc_support_t  support;
rcl_allocator_t allocator;
rcl_node_t      node;
rcl_timer_t     fb_timer;

// Feedback publish rate (ms)
#define FEEDBACK_PERIOD_MS 200

// How often to let micro-ROS process (ms).
// Between spin calls the steppers get a tight, uninterrupted loop.
#define SPIN_PERIOD_MS 20

// ─────────────────────────────────────────────
//  Custom Stepper Motor Driver Implementation
// ─────────────────────────────────────────────

// Update one stepper motor (trapezoidal profile)
// Uses per-step displacement-based kinematics for loop-rate-independent behavior.
void updateStepper(StepperMotor& m) {
  // If at target, stop
  if (m.current_pos == m.target_pos) {
    m.speed = 0.0;
    m.dir = 0;
    return;
  }
  
  // Determine direction
  long remaining = m.target_pos - m.current_pos;
  int8_t new_dir = (remaining > 0) ? 1 : -1;
  
  // Update direction pin if changed (reset speed on reversal)
  if (new_dir != m.dir) {
    m.dir = new_dir;
    m.speed = 0.0;  // Reset speed when direction changes
    digitalWrite(m.dir_pin, (m.dir > 0) ? HIGH : LOW);
  }
  
  // Minimum speed to avoid stalling (but only if we have somewhere to go)
  if (m.speed < 10.0 && m.current_pos != m.target_pos) {
    m.speed = 10.0;
  }
  
  // If speed is still 0 (at target), don't try to step
  if (m.speed <= 0.0) {
    return;
  }
  
  // Compute step interval from current speed
  unsigned long step_interval_us = (unsigned long)(1000000.0 / m.speed);
  
  // Check if it's time to step
  unsigned long now_us = micros();
  unsigned long elapsed_us = now_us - m.last_step_us;  // Unsigned subtraction handles wrap-around
  
  if (elapsed_us >= step_interval_us) {
    // Pulse step pin (minimum 3us HIGH per CL42T/CL57T spec)
    digitalWrite(m.step_pin, HIGH);
    delayMicroseconds(3);  // 3us is very short, acceptable blocking
    digitalWrite(m.step_pin, LOW);
    
    // Update position
    m.current_pos += m.dir;
    
    // Update last_step_us
    m.last_step_us = now_us;
    
    // Compute new speed using displacement-based kinematics (per-step, not per-call)
    // v² = v₀² + 2aΔx, where Δx = 1 step
    // This naturally blends acceleration, cruise, and deceleration phases
    long remaining_abs = abs(m.target_pos - m.current_pos);
    
    // Speed after accelerating for 1 step: v² = v₀² + 2a
    float v_accel = sqrt(m.speed * m.speed + 2.0f * m.accel);
    
    // Maximum speed that can still stop in remaining distance: v² = 2ad
    float v_decel = sqrt(2.0f * m.accel * (float)remaining_abs);
    
    // Take minimum of: accelerated speed, max speed limit, and decel-limited speed
    // This gives us: accelerate → cruise → decelerate profile
    m.speed = min(min(v_accel, m.max_speed), v_decel);
    
    // Ensure we don't go below minimum speed (unless at target)
    if (m.speed < 10.0 && remaining_abs > 0) {
      m.speed = 10.0;
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
//  Subscription callback — joint commands
// ─────────────────────────────────────────────

void joint_cmd_callback(const void *msgin) {
  const std_msgs__msg__Float64MultiArray *msg =
      (const std_msgs__msg__Float64MultiArray *)msgin;

  // Safety: only process if we received exactly NUM_JOINTS values
  if (msg->data.size != NUM_JOINTS) return;

  for (int i = 0; i < NUM_JOINTS; i++) {
    double target_rad = msg->data.data[i];
    long target_steps = (long)(target_rad * steps_per_radian[i]);
    motors[i].target_pos = target_steps;
  }

  // Flash LED to indicate command received
  digitalWrite(LED_PIN, HIGH);
}

// ─────────────────────────────────────────────
//  Timer callback — publish feedback
// ─────────────────────────────────────────────

void feedback_timer_callback(rcl_timer_t *timer, int64_t last_call_time) {
  (void)last_call_time;
  if (timer == NULL) return;

  for (int i = 0; i < NUM_JOINTS; i++) {
    joint_fb_data[i] = (double)motors[i].current_pos / steps_per_radian[i];
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

  // --- Configure servo ---
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  gripper.attach(SERVO_PIN, 500, 2400);

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

  // --- Executor: 1 subscription + 1 timer ---
  RCCHECK(rclc_executor_init(&executor, &support.context, 2, &allocator));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &sub_joint_cmd, &msg_joint_cmd,
      &joint_cmd_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_timer(&executor, &fb_timer));
}

// ─────────────────────────────────────────────
//  loop()
// ─────────────────────────────────────────────

void loop() {
  // ── Tight stepping — runs every iteration, no micro-ROS overhead ──
  bool any_moving = false;
  for (int i = 0; i < NUM_JOINTS; i++) {
    updateStepper(motors[i]);
    if (motors[i].current_pos != motors[i].target_pos) {
      any_moving = true;
    }
  }

  // ── Throttled micro-ROS processing ──
  unsigned long now_ms = millis();
  static unsigned long last_spin = 0;
  if (now_ms - last_spin >= SPIN_PERIOD_MS) {
    last_spin = now_ms;
    RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(0)));
  }

  // ── LED: turn off when all joints have reached their targets ──
  bool all_arrived = true;
  for (int i = 0; i < NUM_JOINTS; i++) {
    if (motors[i].target_pos != motors[i].current_pos) {
      all_arrived = false;
      break;
    }
  }
  if (all_arrived && digitalRead(LED_PIN) == HIGH) {
    digitalWrite(LED_PIN, LOW);
  }

  // ── Debug: estimate effective speed once per second ──
  if (now_ms - last_debug_ms >= 1000) {
    last_debug_ms = now_ms;
    for (int i = 0; i < NUM_JOINTS; i++) {
      long pos = motors[i].current_pos;
      long delta = pos - last_pos_debug[i];
      last_pos_debug[i] = pos;

      double rad_per_s = (steps_per_radian[i] > 0.0)
                           ? ((double)delta / steps_per_radian[i])
                           : 0.0;
      joint_vel_debug_data[i] = rad_per_s;
    }

    // Publish approximate velocities (rad/s) for all joints
    RCSOFTCHECK(rcl_publish(&pub_joint_vel_debug, &msg_joint_vel_debug, NULL));
  }
}
