#include <Servo.h>

Servo gripperServo;
const int servoPin = 4;
int receivedAngle = 0;  
int currentAngle = 0;
const int stepDelay = 1;  

void setup() {
    Serial.begin(115200);
    gripperServo.attach(servoPin);
    gripperServo.write(receivedAngle);
    Serial.println("Servo Ready");
}

void loop() {
    if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n');
        Serial.print("Received: "); Serial.println(input);
        int angle = input.toInt();

        
        if (angle >= 0 && angle <= 90) {
            receivedAngle = map(angle, 0, 90, 0, 65);
        }
    }

    if (currentAngle < receivedAngle) {
        currentAngle++;
    } else if (currentAngle > receivedAngle) {
        currentAngle--;
    }

    gripperServo.write(currentAngle);
    delay(stepDelay);
}