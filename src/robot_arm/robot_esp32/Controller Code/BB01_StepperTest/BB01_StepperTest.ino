/**
 * BB01_StepperTest.ino
 *
 * Standalone stepper motor test sketch for BB01 6-DOF robot arm.
 * NO micro-ROS - pure stepper control for hardware/software isolation testing.
 *
 * Tests motors individually and in combinations to diagnose speed differential
 * between motors 1-3 (fast) and motors 4-6 (slow).
 *
 * Hardware:
 *   - 6x NEMA23 steppers via CL42T / CL57T closed-loop drivers
 *   - 2x ULN2803A signal buffers (common anode)
 *   - Shared ENA on IO16
 *   - Status LED on IO2
 */

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

// Status LED
#define LED_PIN   2

// ─────────────────────────────────────────────
//  Motor Parameters (per joint)
// ─────────────────────────────────────────────

#define NUM_JOINTS 6

// Steps per motor revolution (driver microstep setting)
static const float steps_per_rev[NUM_JOINTS] = {
  800.0, 800.0, 800.0, 800.0, 800.0, 800.0
};

// Gear ratio — motor revolutions per output revolution
static const float gear_ratio[NUM_JOINTS] = {
  19.0, 19.0, 19.0, 19.0, 19.0, 19.0
};

// ─────────────────────────────────────────────
//  Motion Limits (OUTPUT shaft, rad/s and rad/s²)
// ─────────────────────────────────────────────

// Maximum output velocity per joint (rad/s)
static const float max_velocity_rad[NUM_JOINTS] = {
  0.3, 0.3, 0.3, 0.3, 0.3, 0.3
};

// Maximum output acceleration per joint (rad/s²)
static const float max_accel_rad[NUM_JOINTS] = {
  2.4, 2.4, 2.4, 2.4, 2.4, 2.4
};

// ─────────────────────────────────────────────
//  Derived quantities (computed in setup())
// ─────────────────────────────────────────────

static float steps_per_radian[NUM_JOINTS];
static float max_speed_steps[NUM_JOINTS];
static float max_accel_steps[NUM_JOINTS];

// ─────────────────────────────────────────────
//  Custom Stepper Motor Driver
// ─────────────────────────────────────────────

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
//  Diagnostics and Serial Interface
// ─────────────────────────────────────────────

static unsigned long last_debug_ms = 0;
static long last_pos_debug[NUM_JOINTS];
static unsigned long loop_count = 0;
static unsigned long last_loop_count = 0;
static unsigned long last_loop_time_us = 0;
static unsigned long max_loop_time_us = 0;
static unsigned long total_loop_time_us = 0;
static unsigned long loop_samples = 0;

void printStatus() {
  unsigned long now_ms = millis();
  unsigned long elapsed_ms = now_ms - last_debug_ms;
  
  if (elapsed_ms < 1000) return;  // Print every 1 second
  
  Serial.println("\n=== Stepper Status ===");
  Serial.print("Loop iterations/sec: ");
  Serial.println(loop_count - last_loop_count);
  Serial.print("Avg loop time (us): ");
  if (loop_samples > 0) {
    Serial.println(total_loop_time_us / loop_samples);
  } else {
    Serial.println("N/A");
  }
  Serial.print("Max loop time (us): ");
  Serial.println(max_loop_time_us);
  Serial.println();
  
  Serial.println("Motor | Position (steps) | Speed (steps/s) | Speed (rad/s) | Target (steps) | Status");
  Serial.println("------|-------------------|-----------------|---------------|----------------|--------");
  
  for (int i = 0; i < NUM_JOINTS; i++) {
    long pos = motors[i].current_pos;
    long delta = pos - last_pos_debug[i];
    last_pos_debug[i] = pos;
    
    float steps_per_s = (elapsed_ms > 0) ? ((float)delta * 1000.0f / (float)elapsed_ms) : 0.0f;
    float rad_per_s = (steps_per_radian[i] > 0.0) ? (steps_per_s / steps_per_radian[i]) : 0.0f;
    
    Serial.print("  ");
    Serial.print(i + 1);
    Serial.print("   | ");
    Serial.print(pos);
    Serial.print("              | ");
    Serial.print(steps_per_s, 1);
    Serial.print("            | ");
    Serial.print(rad_per_s, 3);
    Serial.print("          | ");
    Serial.print(motors[i].target_pos);
    Serial.print("            | ");
    
    if (motors[i].current_pos == motors[i].target_pos) {
      Serial.println("IDLE");
    } else {
      Serial.println("MOVING");
    }
  }
  
  Serial.println();
  Serial.println("Commands: '1'=motor1, '4'=motor4, '1,4'=motors1+4, 'all'=all motors, 'r'=reset all");
  Serial.println("Send angle in degrees (e.g., '1 90' moves motor 1 to 90 degrees)");
  Serial.println();
  
  // Reset counters
  last_debug_ms = now_ms;
  last_loop_count = loop_count;
  max_loop_time_us = 0;
  total_loop_time_us = 0;
  loop_samples = 0;
}

void parseCommand(String cmd) {
  cmd.trim();
  cmd.toLowerCase();
  
  if (cmd.length() == 0) return;
  
  // Reset command
  if (cmd == "r" || cmd == "reset") {
    for (int i = 0; i < NUM_JOINTS; i++) {
      motors[i].target_pos = 0;
      motors[i].current_pos = 0;
      motors[i].speed = 0.0;
      motors[i].dir = 0;
    }
    Serial.println("All motors reset to position 0");
    return;
  }
  
  // Parse motor selection and angle
  // Format: "motor_list angle" or just "motor_list" (defaults to 90 degrees)
  // Examples: "1 90", "4 45", "1,4 90", "all 90"
  
  int space_idx = cmd.indexOf(' ');
  String motor_list = (space_idx > 0) ? cmd.substring(0, space_idx) : cmd;
  String angle_str = (space_idx > 0) ? cmd.substring(space_idx + 1) : "90";
  
  float angle_deg = angle_str.toFloat();
  if (angle_deg == 0.0 && angle_str != "0") {
    Serial.println("Error: Invalid angle");
    return;
  }
  
  float angle_rad = angle_deg * PI / 180.0;
  
  // Parse motor list
  bool motors_to_move[NUM_JOINTS] = {false, false, false, false, false, false};
  
  if (motor_list == "all") {
    for (int i = 0; i < NUM_JOINTS; i++) {
      motors_to_move[i] = true;
    }
  } else {
    // Parse comma-separated list: "1", "1,4", "4,5,6", etc.
    int start = 0;
    while (start < motor_list.length()) {
      int comma_idx = motor_list.indexOf(',', start);
      String motor_str = (comma_idx > 0) ? motor_list.substring(start, comma_idx) : motor_list.substring(start);
      motor_str.trim();
      
      int motor_num = motor_str.toInt();
      if (motor_num >= 1 && motor_num <= NUM_JOINTS) {
        motors_to_move[motor_num - 1] = true;
      }
      
      if (comma_idx < 0) break;
      start = comma_idx + 1;
    }
  }
  
  // Set targets for selected motors
  int count = 0;
  for (int i = 0; i < NUM_JOINTS; i++) {
    if (motors_to_move[i]) {
      long target_steps = (long)(angle_rad * steps_per_radian[i]);
      motors[i].target_pos = target_steps;
      count++;
    }
  }
  
  Serial.print("Moving ");
  Serial.print(count);
  Serial.print(" motor(s) to ");
  Serial.print(angle_deg);
  Serial.println(" degrees");
}

void checkSerial() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    parseCommand(cmd);
  }
}

// ─────────────────────────────────────────────
//  setup()
// ─────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================");
  Serial.println("BB01 Standalone Stepper Test");
  Serial.println("========================================");
  Serial.println();
  
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
    
    // Initialize debug tracking
    last_pos_debug[i] = 0;
  }
  
  // --- Configure stepper motors ---
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
  
  Serial.println("Hardware initialized");
  Serial.println("Steps per radian:");
  for (int i = 0; i < NUM_JOINTS; i++) {
    Serial.print("  Motor ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.println(steps_per_radian[i], 2);
  }
  Serial.println();
  Serial.println("Ready for commands!");
  Serial.println("Commands: '1'=motor1, '4'=motor4, '1,4'=motors1+4, 'all'=all motors, 'r'=reset");
  Serial.println("Send angle in degrees (e.g., '1 90' moves motor 1 to 90 degrees)");
  Serial.println();
  
  last_debug_ms = millis();
}

// ─────────────────────────────────────────────
//  loop()
// ─────────────────────────────────────────────

void loop() {
  unsigned long loop_start_us = micros();
  
  // Check for serial commands (non-blocking)
  checkSerial();
  
  // Update all steppers (tight loop, no blocking)
  for (int i = 0; i < NUM_JOINTS; i++) {
    updateStepper(motors[i]);
  }
  
  // Update loop timing statistics
  unsigned long loop_time_us = micros() - loop_start_us;
  loop_count++;
  total_loop_time_us += loop_time_us;
  loop_samples++;
  if (loop_time_us > max_loop_time_us) {
    max_loop_time_us = loop_time_us;
  }
  
  // Print status every second
  printStatus();
  
  // Small yield to prevent watchdog issues (only when idle)
  bool any_moving = false;
  for (int i = 0; i < NUM_JOINTS; i++) {
    if (motors[i].current_pos != motors[i].target_pos) {
      any_moving = true;
      break;
    }
  }
  
  if (!any_moving) {
    delayMicroseconds(10);  // Small delay when idle
  }
}
