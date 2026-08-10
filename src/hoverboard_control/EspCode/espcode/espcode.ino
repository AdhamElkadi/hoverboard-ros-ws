#include <BluetoothSerial.h>

#include <AccelStepper.h>



// ===============================

// Bluetooth

// ===============================

BluetoothSerial SerialBT;



// ===============================

// TB6600 Stepper (الحركة الأفقية يمين/يسار)

// ===============================

#define STEP_PIN 25

#define DIR_PIN  26

#define MotorInterfaceType 1



AccelStepper headStepper(MotorInterfaceType, STEP_PIN, DIR_PIN);

const float HEAD_RUN_SPEED = 200; // سرعة الاستبر المستمرة



bool rotateLeft = false;

bool rotateRight = false;



// ===============================

// Cytron MD10C R3 DC Linear Motor (الحركة الرأسية فوق/تحت)

// ===============================

#define DC_PWM_PIN 27

#define DC_DIR_PIN 14



const int DC_MOVE_SPEED = 35;    // سرعة الحركة الرأسية 30%

const int DC_BRAKE_SPEED = 10;   // قوة الفرملة ضد الجاذبية 10%

bool brakeDirection = LOW;       



// إعدادات الـ PWM الصامتة للـ ESP32 لمنع الضوضاء

const int pwmFreq = 20000;       // 20 كيلوهرتز (تردد فوق صوتي صامت كلياً)

const int pwmResolution = 8;    



// ===============================

// PWM helper

// ===============================

int percentToPWM(int percent) {

  percent = constrain(percent, 0, 100);

  return map(percent, 0, 100, 0, 255);

}



// ===============================

// DC MOTOR FUNCTIONS

// ===============================

void dcMove(bool direction, int speed) {

  digitalWrite(DC_DIR_PIN, direction ? HIGH : LOW);

  ledcWrite(DC_PWM_PIN, percentToPWM(speed));

}



void dcBrake() {

  digitalWrite(DC_DIR_PIN, brakeDirection);

  ledcWrite(DC_PWM_PIN, percentToPWM(DC_BRAKE_SPEED));

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

// Bluetooth command handler

// ===============================

void processCommand(char cmd) {

  switch(cmd) {

    

    // ------- تحكم الموتور الاستبر (يمين / يسار) -------

    case 'Y': startRotateLeft();  break; // اضغط للالتفات يسار

    case 'Z': startRotateRight(); break; // اضغط للالتفات يمين

    case 'y':

    case 'z': stopRotation();     break; // ارفع يدك ليقف الاستبر فوراً



    // ------- تحكم الموتور الخطي DC (فوق / تحت) -------

    case 'U': dcMove(true, DC_MOVE_SPEED);  break; // اضغط للصعود

    case 'D': dcMove(false, DC_MOVE_SPEED); break; // اضغط للنزول

    case 'u':

    case 'd': dcBrake();                    break; // ارفع يدك لتفعيل الفرملة الصامتة

  }

}



// ===============================

// SETUP

// ===============================

void setup() {

  Serial.begin(115200);

  SerialBT.begin("RobotHead"); // اسم البلوتوث الذي سيظهر في الموبايل

  

  Serial.println("\n==============================================");

  Serial.println("Robot Head Controller Fully Bluetooth Ready!");

  Serial.println("==============================================");



  // إعدادات الاستبر

  headStepper.setMaxSpeed(1000);



  // إعدادات الموتور الخطّي (Cytron MD10C)

  pinMode(DC_DIR_PIN, OUTPUT);

  ledcAttach(DC_PWM_PIN, pwmFreq, pwmResolution); // تشغيل التردد الصامت للـ PWM



  dcBrake(); // تفعيل الفرملة عند البدء لحماية الرأس من السقوط مفاجئاً

}



// ===============================

// LOOP

// ===============================

void loop() {

  

  // 1. استقبال جميع الأوامر من البلوتوث وتوجيهها للموتور المناسب

  if (SerialBT.available()) {

    char command = SerialBT.read();

    

    // طباعة الأمر في السيريال للتأكد من وصوله

    Serial.print("Bluetooth Command: ");

    Serial.println(command);

    

    processCommand(command);

  }



  // 2. تحديث حركة الموتور الخطوي المستمرة بدون أي تأخير

  if (rotateLeft || rotateRight) {

    headStepper.runSpeed();

  }

}