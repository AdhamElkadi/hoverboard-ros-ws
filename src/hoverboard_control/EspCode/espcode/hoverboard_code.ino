

#include <Arduino.h>

// =========================
// Hoverboard UART settings
// =========================
#define HOVER_SERIAL_BAUD 115200
#define HOVER_RX 16
#define HOVER_TX 17
#define START_FRAME 0xABCD

// =========================
// Ultrasonic Sensor Pins
// =========================
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;

// =========================
// Movement settings
// =========================
#define MAX_SPEED_ABS 450
#define MAX_STEER_ABS 450
#define ACCELERATION_STEP 20 // ✅ NEW: Controls smoothness (Lower = Smoother)

// Timing
#define TIME_SEND 20         // ✅ OPTIMIZED: 20ms (50Hz) for smoother control
#define COMMAND_TIMEOUT_MS 500
#define SENSOR_INTERVAL_MS 50 // ✅ OPTIMIZED: Faster sensor updates

#define LED_BUILTIN 2

// =========================
// UART object
// =========================
HardwareSerial HoverSerial(1);

// =========================
// Packet structure
// =========================
#pragma pack(push, 1)
typedef struct {
  uint16_t start;
  int16_t  steer;
  int16_t  speed;
  uint16_t checksum;
} SerialCommand;
#pragma pack(pop)

static_assert(sizeof(SerialCommand) == 8, "SerialCommand size mismatch");
SerialCommand Command;

// =========================
// Robot command state
// =========================
enum RobotCommand {
  CMD_STOP,
  CMD_FORWARD,
  CMD_BACKWARD,
  CMD_LEFT,
  CMD_RIGHT
};

RobotCommand currentCommand = CMD_STOP;
unsigned long lastLaptopCommandTime = 0;
unsigned long lastHoverSendTime = 0;

// ✅ NEW: Variables for Smooth Movement
int targetSpeed = 0;
int targetSteer = 0;
int currentSpeed = 0;
int currentSteer = 0;

// ✅ NEW: Non-blocking Ultrasonic State
bool sensorActive = false;
unsigned long trigTime = 0;
unsigned long lastSensorTrigger = 0;

// =========================
// Helper functions
// =========================
static inline int16_t clamp16(int16_t value, int16_t minValue, int16_t maxValue) {
  if (value < minValue) return minValue;
  if (value > maxValue) return maxValue;
  return value;
}

void sendHoverCommand(int16_t steer, int16_t speed) {
  steer = clamp16(steer, -MAX_STEER_ABS, MAX_STEER_ABS);
  speed = clamp16(speed, -MAX_SPEED_ABS, MAX_SPEED_ABS);

  Command.start = START_FRAME;
  Command.steer = steer;
  Command.speed = speed;
  
  Command.checksum = 
    (uint16_t)Command.start ^ 
    (uint16_t)Command.steer ^ 
    (uint16_t)Command.speed;

  HoverSerial.write((uint8_t*)&Command, sizeof(Command));
}

// ✅ NEW: Smoothly ramp speed/steer toward targets
void updateSmoothMovement() {
  if (currentSpeed < targetSpeed) currentSpeed += ACCELERATION_STEP;
  else if (currentSpeed > targetSpeed) currentSpeed -= ACCELERATION_STEP;
  
  if (currentSteer < targetSteer) currentSteer += ACCELERATION_STEP;
  else if (currentSteer > targetSteer) currentSteer -= ACCELERATION_STEP;
}

void applyCurrentCommand() {
  // Set Targets based on Logic
  switch (currentCommand) {
    case CMD_FORWARD:
      targetSpeed = 400; targetSteer = 0;
      break;
    case CMD_BACKWARD:
      targetSpeed = -400; targetSteer = 0;
      break;
    case CMD_LEFT:
      targetSpeed = 0; targetSteer = 300; // Pivot turn
      break;
    case CMD_RIGHT:
      targetSpeed = 0; targetSteer = -300; // Pivot turn
      break;
    case CMD_STOP:
    default:
      targetSpeed = 0; targetSteer = 0;
      break;
  }

  // Apply Smoothed Values
  updateSmoothMovement();
  sendHoverCommand(currentSteer, currentSpeed);
  
  // LED Feedback
  digitalWrite(LED_BUILTIN, (currentSpeed != 0 || currentSteer != 0) ? HIGH : LOW);
}

void readLaptopCommand() {
  while (Serial.available() > 0) {
    char command = Serial.read();
    
    if (command == '\n' || command == '\r') continue;

    if (command == 'F' || command == 'f') {
      currentCommand = CMD_FORWARD;
      lastLaptopCommandTime = millis();
    }
    else if (command == 'B' || command == 'b') {
      currentCommand = CMD_BACKWARD;
      lastLaptopCommandTime = millis();
    }
    else if (command == 'L' || command == 'l') {
      currentCommand = CMD_LEFT;
      lastLaptopCommandTime = millis();
    }
    else if (command == 'R' || command == 'r') {
      currentCommand = CMD_RIGHT;
      lastLaptopCommandTime = millis();
    }
    else if (command == 'S' || command == 's') {
      currentCommand = CMD_STOP;
      lastLaptopCommandTime = millis();
    }
  }
}

// ✅ NEW: Non-blocking Ultrasonic Trigger
void triggerUltrasonic() {
  if (!sensorActive && (millis() - lastSensorTrigger >= SENSOR_INTERVAL_MS)) {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    
    sensorActive = true;
    trigTime = micros();
    lastSensorTrigger = millis();
  }
}

// ✅ NEW: Non-blocking Ultrasonic Read
void checkUltrasonicResult() {
  if (sensorActive) {
    if (digitalRead(ECHO_PIN) == HIGH) {
      // Still waiting for pulse to end
      if ((micros() - trigTime) > 30000) { // Timeout
        sensorActive = false;
      }
    } else {
      // Pulse ended
      long duration = micros() - trigTime;
      int distanceCm = duration * 0.034 / 2 / 1000; // Convert to cm
      
      Serial.print("U:");
      Serial.println(distanceCm);
      sensorActive = false;
    }
  }
}

// =========================
// Setup
// =========================
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP32 Optimized Hoverboard Control Ready");
  
  HoverSerial.begin(HOVER_SERIAL_BAUD, SERIAL_8N1, HOVER_RX, HOVER_TX);
  
  currentCommand = CMD_STOP;
  lastLaptopCommandTime = millis();
}

// =========================
// Main loop
// =========================
void loop() {
  // 1. Read commands from ROS (Laptop)
  readLaptopCommand();

  unsigned long now = millis();

  // 2. Safety: stop if laptop stops sending commands
  if (now - lastLaptopCommandTime > COMMAND_TIMEOUT_MS) {
    currentCommand = CMD_STOP;
  }

  // 3. Send hoverboard command repeatedly (Optimized to 20ms)
  if (now - lastHoverSendTime >= TIME_SEND) {
    applyCurrentCommand();
    lastHoverSendTime = now;
  }

  // 4. Handle Ultrasonic (Non-blocking)
  triggerUltrasonic();
  checkUltrasonicResult();
}
