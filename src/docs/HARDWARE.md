# Hardware Interface Specifications

## ESP32 Pinout & Wiring
| Function | GPIO Pin | Connection | Notes |
| :--- | :--- | :--- | :--- |
| UART1 RX | GPIO 16 | STM32 TX | Hoverboard serial receive |
| UART1 TX | GPIO 17 | STM32 RX | Hoverboard serial transmit |
| USB Serial | Native | Laptop/PC | Face search commands (L/R/S) |
| LED_BUILTIN | GPIO 2 | Onboard LED | HIGH = Active turn, LOW = Stop/Idle |

## Movement Constants Reference
These values are critical for safe operation. Changing them without understanding hardware limits may damage motors or cause instability.

| Parameter | Value | Location | Safety Note |
| :--- | :--- | :--- | :--- |
| `TURN_STEER` | 300 | ESP32 `#define` | Safe continuous turn magnitude |
| `MAX_STEER_ABS` | 450 | ESP32 `#define` | Hard hardware limit — do not exceed |
| `TURN_SPEED` | 50 | ESP32 `#define` | Keep-alive speed to prevent STM32 beep |
| `STEER_RATE_LIMIT` | 60 | ESP32 `#define` | Smooths transitions; prevents jerky motion |
| `COMMAND_TIMEOUT_MS` | 500 | ESP32 `#define` | Auto-stop if no command received |
| `TIME_SEND` | 100ms | ESP32 `#define` | STM32 keep-alive interval |
| `START_FRAME` | 0xABCD | ESP32 `#define` | Binary packet sync word |
| `CAM_WIDTH` | 640 | JS `renderer.js` | Must match actual camera resolution |
| `CAM_HEIGHT` | 480 | JS `renderer.js` | Critical for Y-axis normalization |

## Camera Setup
-   **Resolution:** 640×480 @ 30fps
-   **Mounting:** Front-facing, centered on robot chassis
-   **Exposure:** Auto-exposure enabled; manual exposure set to ~100 to reduce motion blur during turns
-   **Orientation:** X-axis inverted in software (`nx = -(...)`) to create mirror effect matching human eye contact

## Motor Driver Protocol
The STM32 expects an 8-byte binary struct via UART at 115200 baud:
```c
typedef struct {
  uint16_t start;     // Always 0xABCD
  int16_t  steer;     // -450 to +450 (positive=left, negative=right)
  int16_t  speed;     // Always 0 for face tracking mode
  uint16_t checksum;  // XOR(start ^ steer ^ speed) & 0xFFFF
} SerialCommand;
