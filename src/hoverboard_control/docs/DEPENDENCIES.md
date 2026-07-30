#  Dependencies & Installation Guide

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

## 2. Serial Port Permissions

Grant access to USB serial devices (required for ESP32 communication):

```bash
sudo usermod -a -G dialout $USER
newgrp dialout  # Apply immediately without reboot
```

Verify access:
```bash
ls -la /dev/ttyUSB* /dev/ttyACM* | grep "dialout" && echo "✅ Serial permissions OK" || echo "❌ Fix: sudo usermod -aG dialout $USER && log out/in"
```

## 3. ROS 2 Packages

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
```

## 4. Azure Kinect DK Drivers

The depth camera requires Microsoft's official SDK. Follow these steps exactly:

### 4.1 Add Microsoft Package Repository
```bash
curl -sSL https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
sudo apt-add-repository https://packages.microsoft.com/ubuntu/22.04/prod
sudo apt update
```

### 4.2 Install Kinect SDK
```bash
sudo apt install -y libk4a1.4 k4a-tools azure-kinect-sensor-sdk
```

### 4.3 Configure Udev Rules (CRITICAL)
Without this step, the Kinect only works with `sudo`:
```bash
sudo cp /lib/udev/rules.d/99-k4a.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

> ⚠️ **Critical:** If you skip the udev rules step, the Kinect will only work with `sudo`.

## 5. Python Libraries

Install with pinned versions for guaranteed compatibility:

```bash
pip3 install --user \
    pyserial==3.5 \
    opencv-python-headless==4.8.0.76 \
    mediapipe==0.10.5 \
    numpy==1.24.3
```

### Library Purposes

| Library | Purpose |
| :--- | :--- |
| `pyserial` | USB serial communication with ESP32 (115200 baud) |
| `opencv-python-headless` | Image processing (no GUI deps; use `opencv-python` if display needed) |
| `mediapipe` | Real-time face mesh detection and tracking |
| `numpy` | Depth map array operations and median filtering |

## 6. ESP32 Firmware Setup

No external Arduino libraries are required. Only standard `Arduino.h` and `HardwareSerial`.

### 6.1 Arduino IDE Configuration
1.  Install **Arduino IDE 2.x**
2.  Add ESP32 board URL:  
    `File > Preferences > Additional Board Manager URLs` →  
    `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3.  Install **ESP32 by Espressif Systems v2.0.14+** via Board Manager
4.  Select Board: **ESP32 Dev Module**
5.  Upload `esp32/esp32_hoverboard_fusion.ino`

### 6.2 Required GPIO Pins

| Pin | Function |
| :--- | :--- |
| GPIO 16, 17 | UART2 (Hoverboard TX/RX) |
| GPIO 5 | Ultrasonic TRIG |
| GPIO 18 | Ultrasonic ECHO |
| GPIO 2 | Built-in LED (status indicator) |

## 7. Build & Verification

### 7.1 Build Workspace
```bash
cd ~/ros2_ws
colcon build --packages-select hoverboard_control
source install/setup.bash
```

### 7.2 Dependency Verification Script
Run this checklist to confirm everything is installed correctly:

```bash
#!/bin/bash
echo "=== Dependency Check ==="

# ROS 2
ros2 --version >/dev/null 2>&1 && echo "✅ ROS 2 OK" || echo "❌ ROS 2 Missing"

# Python Libraries
python3 -c "import serial, cv2, mediapipe, numpy" 2>/dev/null && \
    echo "✅ Python Libraries OK" || echo "❌ Python Libraries Missing"

# Kinect SDK
command -v k4aviewer >/dev/null 2>&1 && echo "✅ Kinect SDK OK" || echo "❌ Kinect SDK Missing"

# Serial Port Access
[ -w /dev/ttyUSB0 ] 2>/dev/null && echo "✅ Serial Port Access OK" || echo "❌ Serial Port Permission Denied"

# ESP32 Board Support
grep -q "esp32" ~/.arduino15/packages/esp32/hardware/esp32/*/boards.txt 2>/dev/null && \
    echo "✅ ESP32 Board Support OK" || echo "❌ ESP32 Board Support Missing"

echo "=== Check Complete ==="
```

## 8. Comprehensive Troubleshooting

| Error / Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'serial'` | pyserial not installed | Run `pip3 install pyserial` |
| `Permission denied: '/dev/ttyUSB0'` | User not in dialout group | Run `sudo usermod -a -G dialout $USER` then **log out and back in** |
| `k4aviewer: command not found` | Kinect SDK not installed | Reinstall `azure-kinect-sensor-sdk` + reload udev rules |
| `cv_bridge import error` | Missing ROS cv-bridge | Run `sudo apt install ros-humble-cv-bridge` |
| ESP32 upload fails | Charge-only USB cable | Use **data-capable** cable; try different USB port |
| Face detector crashes | OpenCV/MediaPipe version mismatch | Run `pip3 install --force-reinstall opencv-python-headless mediapipe` |
| Kinect "No devices found" | udev rules not loaded | Run `sudo udevadm control --reload-rules && sudo udevadm trigger` |
| Robot moves but sensors don't update | Serial buffer overflow | Reduce debug prints in ESP32 code |
| Depth data all zeros | Kinect not initialized | Run `k4aviewer` first; ensure USB 3.0 connection |
| `colcon build` CMake error | Missing build dependencies | Run `rosdep install --from-paths src --ignore-src -r -y` |
| Ultrasonic reads 0 constantly | Sensor disconnected/wrong pins | Verify GPIO 5/18 wiring; test with multimeter |
| Robot jitters when backing up | False ultrasonic reading | Debounce implemented; check ECHO pin for noise |
| `fusion_controller` can't connect to ESP | Wrong serial port | Run `ls /dev/tty*` before/after plugging in ESP |

## 9. Optional but Recommended Tools

-   **rqt_graph**: `ros2 run rqt_graph rqt_graph` — Visualize live topic connections
-   **tmux/screen**: Manage multiple terminal sessions during testing
-   **ros2 doctor**: `ros2 doctor` — Diagnose ROS 2 environment issues
-   **minicom**: `sudo apt install minicom` — Test raw serial communication with ESP32
