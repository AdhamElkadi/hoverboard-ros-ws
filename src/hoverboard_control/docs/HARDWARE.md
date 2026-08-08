
---

### 3. `HARDWARE.md`
*This covers the physical setup.*

```markdown
# 🔌 Hardware Setup

## Components List
*   **Compute:** Laptop/PC (Ubuntu 22.04)
*   **Sensors:** Azure Kinect DK, USB Webcam, HC-SR04 Ultrasonic
*   **Controllers:** ESP32 DevKit V1, Hoverboard Mainboard (STM32)

## ESP32 Pinout

| Component | ESP32 GPIO | Notes |
| :--- | :--- | :--- |
| **Hoverboard TX** | GPIO 16 | Connect to Hoverboard RX |
| **Hoverboard RX** | GPIO 17 | Connect to Hoverboard TX |
| **Ultrasonic TRIG** | GPIO 5 | Rear Sensor |
| **Ultrasonic ECHO** | GPIO 18 | Rear Sensor (Use voltage divider if 5V) |
| **LED Built-in** | GPIO 2 | Status Indicator |

## Wiring Diagram
1.  **Hoverboard UART:** Cross TX/RX between ESP32 and Hoverboard. Ensure common GND.
2.  **Ultrasonic:** 
    *   VCC → 3.3V (or 5V with level shifter)
    *   GND → GND
    *   TRIG → GPIO 5
    *   ECHO → GPIO 18
3.  **USB:** Connect ESP32 to Laptop via data-capable USB cable.

## ⚠️ Important Notes
*   **Voltage Levels:** Hoverboard UART is 3.3V. Do NOT connect 5V logic directly.
*   **Power:** ESP32 should be powered via USB or separate 5V supply. Do not power from hoverboard battery unless regulated.
*   **Sensor Placement:** Mount HC-SR04 on the rear, facing backward, clear of obstructions.
