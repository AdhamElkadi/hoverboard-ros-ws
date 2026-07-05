# 💻 Software Structure

## ROS 2 Nodes

### `fusion_controller.py`
*   **Role:** Central decision maker.
*   **Subscribers:** `/face/center`, `/depth/image_raw`, `/sensor/ultrasonic/rear`
*   **Logic:** 
    *   Priority 1: Rear Safety (Stop if wall behind).
    *   Priority 2: Front Obstacle (Back up if clear behind).
    *   Priority 3: Face Tracking (Stop/Search/Roam).
*   **Publisher:** Serial Command Stream to ESP32.

### `ultrasonic_bridge.py`
*   **Role:** Middleware between ESP32 and ROS.
*   **Function:** Reads `U:dist` from serial, publishes `/sensor/ultrasonic/rear`.
*   **Rate:** 20Hz.

### `face_detector.py`
*   **Role:** Visual perception.
*   **Library:** MediaPipe FaceMesh.
*   **Output:** Normalized face center coordinates.

## ESP32 Firmware (`esp32_hoverboard_fusion.ino`)
*   **Non-Blocking Sensors:** Uses `pulseIn(..., 20000)` to prevent freezing.
*   **Debounce Logic:** Requires 3 consecutive close readings before triggering safety stop.
*   **Keep-Alive:** Sends motor packets every 100ms regardless of new commands.

## File Structure
```text
hoverboard_control/
├── hoverboard_control/
│   ├── fusion_controller.py
│   ├── ultrasonic_bridge.py
│   ├── face_detector.py
│   └── azure_kinect_publisher.py
├── launch/
│   ├── advanced_autonomy.launch.py
│   └── camera.launch.py
└── esp32/
    └── esp32_hoverboard_fusion.ino
