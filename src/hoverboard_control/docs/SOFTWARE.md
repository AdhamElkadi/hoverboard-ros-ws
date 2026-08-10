# 💻 Software Structure

## ROS 2 Nodes

### `manual_controller.py`
*   **Role:** Core manual base + head teleoperation and safety manager.
*   **Subscribers:** `/app_command` (base), `/head/command` (head), `/depth/image_raw` (front safety).
*   **Serial Ports:** `/dev/ttyUSB0` (Base ESP32 at 115200) and `/dev/ttyUSB1` (Head ESP8266 at 115200).
*   **Publishers:** `/sensor/ultrasonic/rear`, `/eilik/command`, `/robot/state`.
*   **Safety Overrides:** Priority 1: Rear ultrasonic stop (≤ 22 cm). Priority 2: Front depth camera stop/backup (< 500 mm).

### `manual_web_controller.py`
*   **Role:** Flask web server (port 5000) providing touch control UI for phone/browser.
*   **Publishers:** `/app_command`, `/head/command`, `/eilik/command`.
*   **Routes:** `/move/<cmd>`, `/head/<cmd>`, `/emotion/<name>`, `/mode`.

### `fusion_controller.py`
*   **Role:** Autonomous mode decision maker.
*   **Subscribers:** `/face/center`, `/depth/image_raw`, `/sensor/ultrasonic/rear`
*   **Publisher:** Serial Command Stream to ESP32.

### `ultrasonic_bridge.py`
*   **Role:** Middleware between ESP32 and ROS.
*   **Function:** Reads `U:dist` from serial, publishes `/sensor/ultrasonic/rear`.
*   **Rate:** 20Hz.

### `face_detector.py`
*   **Role:** Visual perception.
*   **Library:** MediaPipe FaceMesh.
*   **Output:** Normalized face center coordinates (`/face/center`).

## ESP Firmware
*   **ESP32 Base Firmware:** Dual UART to Hoverboard STM32 mainboard and HC-SR04 ultrasonic sensor. Receives `F\n`, `B\n`, `L\n`, `R\n`, `S\n`.
*   **ESP8266 Head Firmware:** Accepts raw ASCII byte stream `U`, `D`, `Y`, `Z` at 115200 (no newline). Silence triggers internal timeout auto-stop.

## File Structure
```text
hoverboard_control/
├── hoverboard_control/
│   ├── manual_controller.py
│   ├── manual_web_controller.py
│   ├── fusion_controller.py
│   ├── ultrasonic_bridge.py
│   ├── face_detector.py
│   └── eilik_bridge.py
├── launch/
│   ├── WebCamera.launch.py   (Manual Mode: Base + Head + Safety)
│   └── camera.launch.py      (Autonomous Mode)
└── EspCode/
    └── espcode/espcode.ino
```
