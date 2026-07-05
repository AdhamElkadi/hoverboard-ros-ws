# 📦 Dependencies & Installation Guide

This document contains **everything** required to set up the Hoverboard ROS 2 Autonomous Control System, including system requirements, ROS packages, Azure Kinect drivers, Python libraries, ESP32 firmware setup, hardware permissions, build verification, and comprehensive troubleshooting.

## 1. System Requirements

| Component | Requirement | Notes |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 LTS | Required for ROS 2 Humble compatibility |
| **ROS Distribution** | ROS 2 Humble Hawksbill | Primary middleware framework |
| **Python Version** | Python 3.10+ | Required for MediaPipe and CV Bridge |
| **Build Tool** | colcon | Standard ROS 2 build system |
| **CMake** | CMake 3.16+ | Required for building ROS packages |
| **Git** | Git 2.35+ | For version control and branching |

## 2. ROS 2 Packages

Install these core ROS 2 packages via `apt`:

```bash
sudo apt update
sudo apt install -y \
    ros-humble-usb-cam \
    ros-humble-cv-bridge \
    ros-humble-geometry-msgs \
    ros-humble-sensor-msgs \
    ros-humble-launch \
    ros-humble-launch-ros \
    ros-humble-rqt* \
    python3-rosdep
