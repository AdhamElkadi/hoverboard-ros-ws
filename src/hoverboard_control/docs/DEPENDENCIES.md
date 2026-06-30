# Project Dependencies & Installation Guide

This document lists all software dependencies required to build and run the Hoverboard Face Tracking + Eilik Expression system. All instructions are validated for **Ubuntu 24.04 (Noble Numbat)** with Python 3.12.

---

## 1. System-Level Prerequisites
Install these via `apt` before setting up Python or Node.js environments.

```bash
sudo apt update && sudo apt install -y \
  python3-pip \
  python3-venv \
  nodejs \
  npm \
  git \
  colcon-common-extensions \
  ros-dev-tools \
  libopencv-dev \
  ffmpeg \
  libusb-1.0-0-dev \
  screen
# Python dependencies
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
python3 -c "import mediapipe; print('MediaPipe OK')"
python3 -c "import serial; print('PySerial OK')"

# Node.js dependencies
cd ~/ros2_ws/src/hoverboard_control/eilik_app
node -e "const pkg = require('./package.json'); console.log('Electron:', pkg.dependencies.electron)"

# Serial port access
ls -la /dev/ttyUSB* | grep -q "dialout" && echo "Serial permissions OK" || echo "Fix: sudo usermod -aG dialout $USER && reboot"

# ROS 2 workspace
colcon list --packages-select hoverboard_control
