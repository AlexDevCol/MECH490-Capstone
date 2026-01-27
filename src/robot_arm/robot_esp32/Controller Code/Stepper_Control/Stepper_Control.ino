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
#define MAX_SPEED 750     // Maximum speed in steps per second
#define ACCELERATION 60   // Acceleration in steps per second^2

// --- Global Stepper Object ---
// Use FULL4WIRE mode for 4-pin direct control (full step)
// Alternative: AccelStepper::HALF4WIRE for half-step mode (more steps, smoother)
AccelStepper stepper(AccelStepper::FULL4WIRE, IN1_PIN, IN3_PIN, IN2_PIN, IN4_PIN);

// --- Position Tracking ---
float current_position = 0.0;  // Current position in degrees
float steps_per_degree;        // Calculated steps per output degree

// --- Serial Input Buffer ---
String serial_input = "";
bool command_received = false;

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
  
  // Print movement info
  Serial.print("Current position: ");
  Serial.print(current_position);
  Serial.print("° -> Target: ");
  Serial.print(target_angle);
  Serial.print("° (Delta: ");
  Serial.print(delta_angle);
  Serial.print("°) -> Steps: ");
  Serial.println(steps);
  
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
    
    Serial.print("Movement complete. New position: ");
    Serial.print(current_position);
    Serial.println("°");
  } else {
    Serial.println("Already at target position.");
  }
}

// --- Function to handle Serial input ---
void handle_serial_command() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      // End of command
      if (serial_input.length() > 0) {
        command_received = true;
      }
    } else {
      // Add character to input buffer
      serial_input += c;
    }
  }
  
  // Process command if received
  if (command_received) {
    serial_input.trim();
    
    if (serial_input.length() > 0) {
      // Try to parse as float
      float target_angle = serial_input.toFloat();
      
      // Check if valid number
      if (target_angle != 0.0 || serial_input == "0" || serial_input == "0.0") {
        // Valid angle command
        move_to_angle(target_angle);
      } else {
        // Check for special commands
        if (serial_input == "home" || serial_input == "H") {
          Serial.println("Moving to home position (0°)...");
          move_to_angle(0.0);
        } else if (serial_input == "status" || serial_input == "S") {
          Serial.println("=== Stepper Status ===");
          Serial.print("Current position: ");
          Serial.print(current_position);
          Serial.println("°");
          Serial.print("Steps per degree: ");
          Serial.println(steps_per_degree, 4);
          Serial.print("Gear ratio: ");
          Serial.print(GEAR_RATIO);
          Serial.println(":1");
          Serial.print("Steps per rev: ");
          Serial.println(STEPS_PER_REV);
        } else {
          Serial.print("Invalid command: ");
          Serial.println(serial_input);
          Serial.println("Usage: Enter angle in degrees (e.g., 45, 90.5)");
          Serial.println("Commands: 'home' or 'H' to go to 0°, 'status' or 'S' for status");
        }
      }
    }
    
    // Clear input buffer
    serial_input = "";
    command_received = false;
  }
}

void setup() {
  // Initialize Serial for debugging and commands
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("==========================================");
  Serial.println("ESP32 Stepper Motor Control - Phase 1");
  Serial.println("==========================================");
  
  // Configure LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Calculate steps per output degree
  // steps_per_degree = (steps_per_rev * gear_ratio) / 360
  steps_per_degree = (float)(STEPS_PER_REV * GEAR_RATIO) / 360.0;
  
  Serial.print("Configuration:");
  Serial.print("\n  Steps per revolution: ");
  Serial.print(STEPS_PER_REV);
  Serial.print("\n  Gear ratio: ");
  Serial.print(GEAR_RATIO);
  Serial.print(":1");
  Serial.print("\n  Steps per output degree: ");
  Serial.print(steps_per_degree, 4);
  Serial.print("\n  Max speed: ");
  Serial.print(MAX_SPEED);
  Serial.print(" steps/s");
  Serial.print("\n  Acceleration: ");
  Serial.print(ACCELERATION);
  Serial.println(" steps/s²");
  
  // Configure stepper
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setAcceleration(ACCELERATION);
  stepper.setCurrentPosition(0);  // Set current position to 0 steps
  
  Serial.println("\nStepper initialized.");
  Serial.println("Current position: 0.0°");
  Serial.println("\nReady for commands!");
  Serial.println("Enter angle in degrees (e.g., 45, 90.5)");
  Serial.println("Commands: 'home' or 'H' to go to 0°, 'status' or 'S' for status");
  Serial.println("==========================================");
}

void loop() {
  // Handle Serial input
  handle_serial_command();
  
  // Run stepper (needed for movement execution)
  stepper.run();
  
  // Small delay to avoid busy looping
  delay(1);
}
