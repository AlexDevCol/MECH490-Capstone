/**
 * BB01_Controller_Arduino_Test.ino
 *
 * Arduino-only ESP32 firmware for BB01 6-DOF robot arm testing.
 * Preserves dual-core architecture and motion logic from BB01_Controller_Final.ino,
 * but replaces micro-ROS with Serial CSV command/feedback.
 *
 * Protocol:
 *   RX command:  cmd,j1_rad,j2_rad,j3_rad,j4_rad,j5_rad,j6_rad,gripper_deg
 *   TX feedback: fb,j1_rad,j2_rad,j3_rad,j4_rad,j5_rad,j6_rad,gripper_deg
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <ESP32Servo.h>

// ─────────────────────────────────────────────
//  Pin Definitions (from BB01 schematic)
// ─────────────────────────────────────────────

#define J1_STEP_PIN 12
#define J1_DIR_PIN  13
#define J2_STEP_PIN 14
#define J2_DIR_PIN  15
#define J3_STEP_PIN 17
#define J3_DIR_PIN  18

#define J4_STEP_PIN 19
#define J4_DIR_PIN  21
#define J5_STEP_PIN 35
#define J5_DIR_PIN  36
#define J6_STEP_PIN 37
#define J6_DIR_PIN  38

#define ENA_PIN   16
#define SERVO_PIN 4
#define LED_PIN   2

// ULN2803A common-anode: several DIR lines held HIGH can sag the bank and starve
// neighbors (e.g. J2 affecting J1). If drivers have a dedicated 5V rail and the
// ULN has a solid ground, set this to 0 to match the minimal "at target" behavior.
#ifndef ULN2803A_RELIEVE_DIR_AT_TARGET
#define ULN2803A_RELIEVE_DIR_AT_TARGET 1
#endif

// ─────────────────────────────────────────────
//  Motor Parameters (per joint)
// ─────────────────────────────────────────────

#define NUM_JOINTS 6

static const float joint_min_deg[NUM_JOINTS] = {
  -90.0, -90.0, -90.0, -90.0, -90.0, -90.0
};

static const float joint_max_deg[NUM_JOINTS] = {
  90.0, 90.0, 90.0, 90.0, 90.0, 90.0
};

static const float steps_per_rev[NUM_JOINTS] = {
  800.0, 800.0, 800.0, 800.0, 800.0, 800.0
};

// Gear ratio — motor revolutions per output revolution
static const float gear_ratio[NUM_JOINTS] = {
  23.0, 29.0, 23.0, 19.0, 5.0, 1.0
};

// Maximum output velocity per joint (rad/s)
// Enforced by per-step kinematic speed updates.
static const float max_velocity_rad[NUM_JOINTS] = {
  0.2, 0.15, 0.2, 0.4, 0.5, 0.5
};

// Maximum output acceleration per joint (rad/s²)
static const float max_accel_rad[NUM_JOINTS] = {
  0.4, 0.25, 0.4, 1.0, 1.5, 2.0
};

static float steps_per_radian[NUM_JOINTS];
static float max_speed_steps[NUM_JOINTS];
static float max_accel_steps[NUM_JOINTS];
static long joint_min_steps[NUM_JOINTS];
static long joint_max_steps[NUM_JOINTS];

static long last_pos_debug[NUM_JOINTS];

// ─────────────────────────────────────────────
//  Custom Stepper Motor Driver
// ─────────────────────────────────────────────

struct StepperMotor {
  uint8_t step_pin;
  uint8_t dir_pin;
  volatile long current_pos;
  volatile long target_pos;
  float speed;
  float max_speed;
  float accel;
  unsigned long last_step_us;
  int8_t dir;
};

void updateStepper(StepperMotor& m, int joint_idx);
static StepperMotor motors[NUM_JOINTS];

// When at target and idle: optionally drive DIR LOW to reduce ULN2803A load.
static inline void stepperIdleAtTarget(StepperMotor& m) {
  m.speed = 0.0f;
#if ULN2803A_RELIEVE_DIR_AT_TARGET
  if (m.dir != 0) {
    m.dir = 0;
    digitalWrite(m.dir_pin, LOW);
    return;
  }
#endif
  m.dir = 0;
}

// ─────────────────────────────────────────────
//  Servo (gripper)
// ─────────────────────────────────────────────

#define GRIPPER_INITIAL_ANGLE 90
Servo gripper;
volatile int gripper_target_angle = GRIPPER_INITIAL_ANGLE;

// ─────────────────────────────────────────────
//  Serial comms state (Core 0)
// ─────────────────────────────────────────────

TaskHandle_t SerialTaskHandle;
#define SERIAL_BAUD 115200
#define FEEDBACK_PERIOD_MS 200

static char serial_rx_buffer[192];
static size_t serial_rx_index = 0;

static inline float degToRad(float deg) {
  return deg * (PI / 180.0f);
}

static inline bool safeParseFloat(const char *token, float *out) {
  if (token == NULL) return false;
  char *endptr = NULL;
  float value = strtof(token, &endptr);
  if (endptr == token) return false;
  while (*endptr != '\0') {
    if (!isspace((unsigned char)(*endptr))) return false;
    endptr++;
  }
  *out = value;
  return true;
}

static inline bool safeParseInt(const char *token, int *out) {
  if (token == NULL) return false;
  char *endptr = NULL;
  long value = strtol(token, &endptr, 10);
  if (endptr == token) return false;
  while (*endptr != '\0') {
    if (!isspace((unsigned char)(*endptr))) return false;
    endptr++;
  }
  *out = (int)value;
  return true;
}

static bool parse_and_apply_command(char *line) {
  char *tokens[10] = {0};
  int token_count = 0;

  char *context = NULL;
  char *tok = strtok_r(line, ",", &context);
  while (tok != NULL && token_count < 10) {
    tokens[token_count++] = tok;
    tok = strtok_r(NULL, ",", &context);
  }

  // Expected with prefix: cmd + 6 joints + gripper = 8 tokens
  if (token_count == 8 && strcmp(tokens[0], "cmd") == 0) {
    float target_rad[NUM_JOINTS];
    for (int i = 0; i < NUM_JOINTS; i++) {
      if (!safeParseFloat(tokens[i + 1], &target_rad[i])) {
        return false;
      }
      long target_steps = (long)(target_rad[i] * steps_per_radian[i]);
      motors[i].target_pos = target_steps;
    }

    int gripper_deg = 0;
    if (!safeParseInt(tokens[7], &gripper_deg)) {
      return false;
    }
    if (gripper_deg < 0) gripper_deg = 0;
    if (gripper_deg > 180) gripper_deg = 180;
    gripper_target_angle = gripper_deg;

    digitalWrite(LED_PIN, HIGH);
    return true;
  }

  // Compatibility mode: no "cmd" prefix, just 6 joints + gripper
  if (token_count == 7) {
    float target_rad[NUM_JOINTS];
    for (int i = 0; i < NUM_JOINTS; i++) {
      if (!safeParseFloat(tokens[i], &target_rad[i])) {
        return false;
      }
      long target_steps = (long)(target_rad[i] * steps_per_radian[i]);
      motors[i].target_pos = target_steps;
    }

    int gripper_deg = 0;
    if (!safeParseInt(tokens[6], &gripper_deg)) {
      return false;
    }
    if (gripper_deg < 0) gripper_deg = 0;
    if (gripper_deg > 180) gripper_deg = 180;
    gripper_target_angle = gripper_deg;

    digitalWrite(LED_PIN, HIGH);
    return true;
  }

  return false;
}

static void process_serial_input() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      serial_rx_buffer[serial_rx_index] = '\0';
      if (serial_rx_index > 0) {
        bool ok = parse_and_apply_command(serial_rx_buffer);
        if (!ok) {
          Serial.println("err,parse");
        }
      }
      serial_rx_index = 0;
      continue;
    }

    if (serial_rx_index < sizeof(serial_rx_buffer) - 1) {
      serial_rx_buffer[serial_rx_index++] = c;
    } else {
      serial_rx_index = 0;
      Serial.println("err,overflow");
    }
  }
}

static void publish_feedback_line() {
  // Serialize from core 0 using volatile reads from core 1.
  Serial.print("fb");
  for (int i = 0; i < NUM_JOINTS; i++) {
    volatile long pos_steps = motors[i].current_pos;
    double rad = (steps_per_radian[i] > 0.0f)
                 ? ((double)pos_steps / (double)steps_per_radian[i])
                 : 0.0;
    Serial.print(",");
    Serial.print(rad, 6);
  }
  Serial.print(",");
  Serial.println((int)gripper_target_angle);
}

void serial_communications_task(void *pvParameters) {
  (void)pvParameters;
  unsigned long last_feedback_ms = 0;

  for (;;) {
    process_serial_input();

    unsigned long now_ms = millis();
    if (now_ms - last_feedback_ms >= FEEDBACK_PERIOD_MS) {
      last_feedback_ms = now_ms;
      publish_feedback_line();
    }

    vTaskDelay(1);
  }
}

// ─────────────────────────────────────────────
//  Custom Stepper Motor Driver Implementation
// ─────────────────────────────────────────────

void updateStepper(StepperMotor& m, int joint_idx) {
  volatile long target = m.target_pos;
  volatile long current = m.current_pos;

  if (target < joint_min_steps[joint_idx]) {
    target = joint_min_steps[joint_idx];
    m.target_pos = target;
  }
  if (target > joint_max_steps[joint_idx]) {
    target = joint_max_steps[joint_idx];
    m.target_pos = target;
  }

  if (current < joint_min_steps[joint_idx]) {
    current = joint_min_steps[joint_idx];
    m.current_pos = current;
  }
  if (current > joint_max_steps[joint_idx]) {
    current = joint_max_steps[joint_idx];
    m.current_pos = current;
  }

  if (current == target) {
    stepperIdleAtTarget(m);
    return;
  }

  long remaining = target - current;
  int8_t desired_dir = (remaining > 0) ? 1 : -1;
  long remaining_abs = abs(remaining);

  if (m.dir != 0 && m.dir != desired_dir) {
    float v_decel_reverse = sqrt(max(0.0f, m.speed * m.speed - 2.0f * m.accel));
    m.speed = v_decel_reverse;
    if (m.speed < 10.0f) {
      m.speed = 0.0f;
      m.dir = 0;
      return;
    }
  } else {
    if (m.dir != desired_dir) {
      m.dir = desired_dir;
      digitalWrite(m.dir_pin, (m.dir > 0) ? HIGH : LOW);
      if (m.speed < 10.0f) {
        m.speed = 10.0f;
      }
    }
  }

  if (m.speed <= 0.0f && current != target) {
    m.speed = 10.0f;
  }

  unsigned long step_interval_us = (unsigned long)(1000000.0f / m.speed);
  unsigned long now_us = micros();
  unsigned long elapsed_us = now_us - m.last_step_us;

  if (elapsed_us >= step_interval_us) {
    digitalWrite(m.step_pin, HIGH);
    delayMicroseconds(3);
    digitalWrite(m.step_pin, LOW);

    m.current_pos += m.dir;
    current = m.current_pos;
    m.last_step_us = now_us;

    target = m.target_pos;
    remaining = target - current;
    remaining_abs = abs(remaining);

    if (remaining_abs == 0) {
      stepperIdleAtTarget(m);
      return;
    }

    desired_dir = (remaining > 0) ? 1 : -1;
    if (m.dir != 0 && m.dir != desired_dir) {
      float v_decel_reverse = sqrt(max(0.0f, m.speed * m.speed - 2.0f * m.accel));
      m.speed = v_decel_reverse;
      if (m.speed < 10.0f) {
        m.speed = 0.0f;
        m.dir = 0;
      }
      return;
    }

    float d_brake = (m.speed * m.speed) / (2.0f * m.accel);
    if (remaining_abs <= d_brake) {
      m.speed = sqrt(2.0f * m.accel * (float)remaining_abs);
      if (m.speed < 10.0f && remaining_abs > 0) {
        m.speed = 10.0f;
      }
    } else {
      float v_accel = sqrt(m.speed * m.speed + 2.0f * m.accel);
      m.speed = min(v_accel, m.max_speed);
    }
  }
}

// ─────────────────────────────────────────────
//  setup()
// ─────────────────────────────────────────────

void setup() {
  Serial.begin(SERIAL_BAUD);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  pinMode(ENA_PIN, OUTPUT);
  digitalWrite(ENA_PIN, HIGH);

  for (int i = 0; i < NUM_JOINTS; i++) {
    steps_per_radian[i] = (steps_per_rev[i] * gear_ratio[i]) / (2.0f * PI);
    max_speed_steps[i]  = max_velocity_rad[i] * steps_per_radian[i];
    max_accel_steps[i]  = max_accel_rad[i] * steps_per_radian[i];

    float min_rad = degToRad(joint_min_deg[i]);
    float max_rad = degToRad(joint_max_deg[i]);
    joint_min_steps[i] = (long)(min_rad * steps_per_radian[i]);
    joint_max_steps[i] = (long)(max_rad * steps_per_radian[i]);
    last_pos_debug[i] = 0;
  }

  uint8_t step_pins[NUM_JOINTS] = {
    J1_STEP_PIN, J2_STEP_PIN, J3_STEP_PIN, J4_STEP_PIN, J5_STEP_PIN, J6_STEP_PIN
  };
  uint8_t dir_pins[NUM_JOINTS] = {
    J1_DIR_PIN, J2_DIR_PIN, J3_DIR_PIN, J4_DIR_PIN, J5_DIR_PIN, J6_DIR_PIN
  };

  for (int i = 0; i < NUM_JOINTS; i++) {
    pinMode(step_pins[i], OUTPUT);
    pinMode(dir_pins[i], OUTPUT);
    digitalWrite(step_pins[i], LOW);
    digitalWrite(dir_pins[i], LOW);

    motors[i].step_pin = step_pins[i];
    motors[i].dir_pin = dir_pins[i];
    motors[i].current_pos = 0;
    motors[i].target_pos = 0;
    motors[i].speed = 0.0f;
    motors[i].max_speed = max_speed_steps[i];
    motors[i].accel = max_accel_steps[i];
    motors[i].last_step_us = micros();
    motors[i].dir = 0;
  }

  // ESP32-S3: allocating all four LEDC timers can clash with RTOS / core internals.
  // One servo → one timer is enough; let the library use a single channel.
 // ESP32PWM::allocateTimer(0);
 // gripper.setPeriodHertz(50);  // standard analog servo frame rate
 // gripper.attach(SERVO_PIN, 500, 2400);
 // gripper.write(GRIPPER_INITIAL_ANGLE);

  delay(2000);

  xTaskCreatePinnedToCore(
      serial_communications_task,
      "Serial_Task",
      8192,
      NULL,
      1,
      &SerialTaskHandle,
      0);

  // One-line banner: if you see this on the correct COM port, USB serial is alive.
  Serial.println("bb01_test_ready");
}

// ─────────────────────────────────────────────
//  loop() - Core 1
// ─────────────────────────────────────────────

void loop() {
  for (int i = 0; i < NUM_JOINTS; i++) {
    updateStepper(motors[i], i);
  }

  static int last_gripper_angle = -1;
  volatile int gripper_target = gripper_target_angle;
  if (gripper_target != last_gripper_angle) {
    gripper.write(gripper_target);
    last_gripper_angle = gripper_target;
  }

  bool all_arrived = true;
  for (int i = 0; i < NUM_JOINTS; i++) {
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
