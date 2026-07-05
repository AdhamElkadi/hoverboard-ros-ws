# 🏗️ System Architecture

## Overview
The system uses a three-tier architecture separating high-level perception (ROS 2) from low-level motor control (ESP32/STM32).

## Data Flow Diagram

```mermaid
graph TD
    subgraph ROS2_Laptop ["🖥️ ROS 2 Environment (Laptop)"]
        KC[Azure Kinect] -->|/depth/image_raw| FC[Fusion Controller]
        WC[Webcam] -->|/image_raw| FD[Face Detector]
        FD -->|/face/center| FC
        UB[Ultrasonic Bridge] -->|/sensor/ultrasonic/rear| FC
    end

    subgraph Comm_Bridge ["🔌 USB Serial Bridge"]
        FC ==>|'F','B','L','R','S'| ESP
        ESP ==>|'U:dist_cm'| UB
    end

    subgraph Embedded ["🤖 Robot Base"]
        ESP[ESP32 Firmware] -->|UART 0xABCD| STM[Hoverboard STM32]
        US[Rear Ultrasonic] -.->|GPIO| ESP
        ESP -.->|Local Safety Override| ESP
    end
