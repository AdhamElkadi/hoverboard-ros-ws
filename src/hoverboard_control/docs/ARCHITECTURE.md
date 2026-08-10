# 🏗️ System Architecture

## Overview
The system uses a three-tier architecture separating high-level perception and web interface (ROS 2) from low-level motor control (ESP32 for base, ESP8266 for head).

## Data Flow Diagram (Manual Teleoperation Mode)

```mermaid
graph TD
    subgraph Web_Client ["📱 Mobile / Phone Web UI"]
        UI[Flask Touch Controls] -->|GET /move/cmd| MWC[manual_web_controller]
        UI -->|GET /head/cmd| MWC
        UI -->|GET /emotion/name| MWC
    end

    subgraph ROS2_Environment ["🖥️ ROS 2 Environment - Laptop"]
        MWC -->|/app_command| MC[manual_controller]
        MWC -->|/head/command| MC
        MWC -->|/eilik/command| EB[eilik_bridge]
        CAM[USB Webcam] -->|/image_raw| FD[Face Detector]
        FD -->|/face/center| EB
        KIN[Depth Camera] -->|/depth/image_raw| MC
    end

    subgraph Comm_Bridge ["🔌 USB Serial Bridges"]
        MC ==>|"F, B, L, R, S @ 115200"| ESP_BASE["/dev/ttyUSB0 - Base ESP32"]
        ESP_BASE ==>|"U:dist_cm"| MC
        MC ==>|"U, D, Y, Z @ 115200"| ESP_HEAD["/dev/ttyUSB1 - Head ESP8266"]
    end

    subgraph Embedded ["🤖 Robot Base & Head"]
        ESP_BASE -->|UART| STM[Hoverboard STM32]
        US[Rear Ultrasonic] -.->|GPIO| ESP_BASE
        ESP_HEAD -->|Stepper / Motor| HEAD[Pan / Tilt Head]
    end
```
