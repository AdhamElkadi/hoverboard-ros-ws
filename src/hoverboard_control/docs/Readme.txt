# 🤖 Hoverboard ROS 2 Autonomous Control System

This repository contains the ROS 2 firmware and control logic for an autonomous hoverboard robot. The system fuses data from an **Azure Kinect DK**, a **Webcam**, and **Ultrasonic Sensors** to enable face tracking, depth-based obstacle avoidance, and rear-collision safety.

## 📚 Documentation Index

| Document | Description |
| :--- | :--- |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System design, data flow diagrams, and communication protocols. |
| **[HARDWARE.md](HARDWARE.md)** | Wiring diagrams, pinouts, and hardware requirements. |
| **[SOFTWARE.md](SOFTWARE.md)** | Node descriptions, topic lists, and ESP32 firmware details. |
| **[DEPENDENCIES.md](DEPENDENCIES.md)** | Required packages, libraries, and installation steps. |
| **[OPERATIONS.md](OPERATIONS.md)** | Launch commands, usage guide, and safety testing procedures. |

## 🚀 Quick Start

1.  **Install Dependencies:** See [DEPENDENCIES.md](DEPENDENCIES.md)
2.  **Wire Hardware:** See [HARDWARE.md](HARDWARE.md)
3.  **Build Workspace:** `colcon build && source install/setup.bash`
4.  **Launch System:** See [OPERATIONS.md](OPERATIONS.md)

## ️ Key Features
*   **Sensor Fusion:** Combines Depth, RGB, and Ultrasonic data in real-time.
*   **Dual-Layer Safety:** ROS-level logic + ESP32 local hardware override.
*   **Face Tracking:** Autonomous following using MediaPipe.
*   **Modular Design:** Separate nodes for bridging, detection, and control.

