#include <AccelStepper.h>

// ===============================
// TB6600 Stepper (الحركة الأفقية يمين/يسار)
// ===============================
// ⚠️ ESP8266 NOTE: Avoid GPIO15 (D8) for STEP/DIR if possible.
// GPIO15 has a boot-strapping resistor and can cause startup issues.
// GPIO4 (D2) and GPIO5 (D1) are safe alternatives.
#define STEP_PIN 4
#define DIR_PIN  5
#define MotorInterfaceType 1

AccelStepper headStepper(MotorInterfaceType, STEP_PIN, DIR_PIN);
const float HEAD_RUN_SPEED = 200;

bool rotateLeft = false;
bool rotateRight = false;

// ===============================
// Cytron MD10C R3 DC Linear Motor
// ⚠️ MUST BE WIRED TO GPIO2 (D4) ON ESP8266
// This is the ONLY hardware PWM pin available
// ===============================
#define DC_PWM_PIN 2   // D4 - Hardware PWM ONLY
#define DC_DIR_PIN 14  // D5

const int DC_MOVE_SPEED = 35;
const int DC_BRAKE_SPEED = 10;
bool brakeDirection = LOW;

// ESP8266 PWM Settings
// Range is 0-1023 (10-bit), NOT 0-255
// Frequency set globally in setup()
const int pwmFreq = 20000;      // 20kHz silent operation
const int pwmMaxDuty = 1023;    // ESP8266 native 10-bit resolution

// ===============================
// PWM helper (ESP8266 10-bit)
// ===============================
int percentToPWM(int percent) {
  percent = constrain(percent, 0, 100);
  return map(percent, 0, 100, 0, pwmMaxDuty);
}

// ===============================
// DC MOTOR FUNCTIONS
// ===============================
void dcMove(bool direction, int speed) {
  digitalWrite(DC_DIR_PIN, direction ? HIGH : LOW);
  analogWrite(DC_PWM_PIN, percentToPWM(speed));
}

void dcBrake() {
  digitalWrite(DC_DIR_PIN, brakeDirection);
  analogWrite(DC_PWM_PIN, percentToPWM(DC_BRAKE_SPEED));
}

// ===============================
// STEPPER FUNCTIONS
// ===============================
void startRotateLeft() {
  rotateLeft = true;
  rotateRight = false;
  headStepper.setSpeed(-HEAD_RUN_SPEED);
}

void startRotateRight() {
  rotateRight = true;
  rotateLeft = false;
  headStepper.setSpeed(HEAD_RUN_SPEED);
}

void stopRotation() {
  rotateLeft = false;
  rotateRight = false;
  headStepper.setSpeed(0);
}

// ===============================
// Serial command handler
// ===============================
void processCommand(char cmd) {
  switch(cmd) {
    case 'Y': startRotateLeft();  break;
    case 'Z': startRotateRight(); break;
    case 'y':
    case 'z': stopRotation();     break;

    case 'U': dcMove(true, DC_MOVE_SPEED);  break;
    case 'D': dcMove(false, DC_MOVE_SPEED); break;
    case 'u':
    case 'd': dcBrake();                    break;
  }
}

// ===============================
// SETUP
// ===============================
void setup() {
  Serial.begin(115200);

  Serial.println("\n==============================================");
  Serial.println("Robot Head Controller - ESP8266");
  Serial.println("⚠️  DC PWM MUST be wired to GPIO2 (D4)");
  Serial.println("Commands: Y/y=Left, Z/z=Right, U/u=Up, D/d=Down");  
  Serial.println("==============================================");

  headStepper.setMaxSpeed(1000);

  pinMode(DC_DIR_PIN, OUTPUT);
  pinMode(DC_PWM_PIN, OUTPUT);

  // Set global PWM frequency to 20kHz for silent operation
  // This affects ALL PWM pins on ESP8266
  analogWriteFreq(pwmFreq);
  analogWriteRange(pwmMaxDuty); // Explicitly set 10-bit range

  dcBrake();
}

// ===============================
// LOOP
// ===============================
void loop() {
  if (Serial.available()) {
    char command = Serial.read();
    Serial.print("Serial Command: ");
    Serial.println(command);
    processCommand(command);
  }

  if (rotateLeft || rotateRight) {
    headStepper.runSpeed();
  }
}
