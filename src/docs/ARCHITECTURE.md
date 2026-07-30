# System Architecture & Data Flow

## 1. High-Level Overview
This project integrates three distinct subsystems into a single autonomous robotic face-tracking platform:
-   **Perception Layer (ROS 2):** Handles camera input, smart face detection with anti-hallucination filters, and motor control logic.
-   **Expression Layer (Electron + Eilik):** Renders the robot's emotional state using SVG morphing, CSS animations, and real-time gaze tracking.
-   **Actuation Layer (ESP32 + STM32):** Bridges high-level commands to low-level hoverboard motor controllers via serial protocols.

---

## 2. Communication Protocols & Data Flow

The system operates across three distinct communication boundaries. Understanding this chain is critical for debugging.

### Layer A: Python → ESP32 (USB Serial)
-   **Protocol:** ASCII Character Stream
-   **Baud Rate:** 115200
-   **Commands:**
    -   `L\n` / `l\n`: Turn Left (Maps to steer +300)
    -   `R\n` / `r\n`: Turn Right (Maps to steer -300)
    -   `S\n` / `s\n`: Stop / Idle (Maps to steer 0)
-   **Timing:** Continuous stream at ~30Hz from `face_search_controller.py`.
-   **Safety:** ESP32 enforces a 500ms command timeout; if no char received, it forces STOP.

### Layer B: ESP32 Internal Processing
-   **Input Parsing:** `readLaptopCommand()` accumulates chars or validates binary packets.
-   **State Machine:** Maintains `currentCommand` enum (`CMD_STOP`, `CMD_LEFT`, `CMD_RIGHT`).
-   **Keep-Alive Logic:** Sends valid neutral packets every 100ms regardless of search state to prevent STM32 fault beeps.
-   **Rate Limiting:** Applies `STEER_RATE_LIMIT = 60` to smooth transitions between states.

### Layer C: ESP32 → STM32 (UART HardwareSerial)
-   **Protocol:** Binary Struct Packet (8 Bytes)
-   **Pinout:** GPIO16 (RX) / GPIO17 (TX)
-   **Structure:**
    ```c
    typedef struct {
      uint16_t start;     // 0xABCD
      int16_t  steer;     // -450 to +450
      int16_t  speed;     // Always 0 for face tracking
      uint16_t checksum;  // XOR(start ^ steer ^ speed)
    } SerialCommand;
    ```
-   **Validation:** STM32 silently discards packets with invalid start frames or checksums.

### Layer D: ROS 2 → Electron (IPC Bridge)
-   **Topic:** `/face/center` (`geometry_msgs/msg/PointStamped`)
-   **Bridge:** `renderer.js` subscribes to ROS topic → normalizes coords to [-1, 1] → calls `window.setEyeGaze(nx, ny)`.
-   **Driver:** `roboeyes-dom.js` applies gaze to CSS variables (`--eyes-x`, `--eyes-y`, `--pupil-x/y`) and triggers morphing via `EilikMorph.startMorph()`.

---

## 3. Smart Face Detection Pipeline
Located in `hoverboard_control/face_detector.py`, this prevents false positives through four sequential filters:

| Filter Stage | Threshold | Purpose |
| :--- | :--- | :--- |
| **Confidence Gate** | > 0.75 | Rejects shadows, posters, partial occlusions |
| **Size Validation** | > 6% frame width | Eliminates tiny distant noise detections |
| **Spatial Jump Limit** | < 120px/frame | Prevents tracking erratic false positives at edges |
| **Temporal Gate** | 3 consecutive frames | Requires stability before publishing to `/face/center` |

> ⚠️ **Note:** Output is smoothed with exponential moving average (α=0.20) to prevent jittery motor commands.

---

## 4. Eilik Expression Engine Architecture
The visual layer uses a hybrid rendering approach defined in the uploaded files:

-   **Morph Mode (`eilik-morph.js`):** Uses Flubber library to interpolate SVG paths between 15+ emotions (neutral, smile, laugh, love, etc.). Activated when `.eilik-morph-on` class is present.
-   **CSS Drive Mode (`roboeyes-dom.js`):** Controls eye position, blink squash (`scaleY`), pupil offset, and curiosity puff via CSS custom properties. Used for real-time gaze tracking.
-   **Reaction System (`eilik-animations.js`):** Triggers transient CSS animations (jiggle, pop, bounce) on emotion changes without disrupting base morph state.
-   **Special FX Modules:**
    -   `eilik-kiss.js`: Launches flying heart animation on "kiss" emotion.
    -   `eilik-love.js`: Pulses heart eyes + sparkles on "love" emotion.

---

## 5. Critical Constants Reference

| Parameter | Value | Location | Safety Note |
| :--- | :--- | :--- | :--- |
| `TURN_STEER` | 300 | ESP32 `#define` | Max safe turn magnitude |
| `MAX_STEER_ABS` | 450 | ESP32 `#define` | Hard hardware limit |
| `COMMAND_TIMEOUT_MS` | 500 | ESP32 `#define` | Auto-stop if Python dies |
| `TIME_SEND` | 100ms | ESP32 `#define` | STM32 keep-alive interval |
| `START_FRAME` | 0xABCD | ESP32 `#define` | Binary packet sync word |
| `min_confidence` | 0.75 | Python `__init__` | Anti-hallucination threshold |
| `search_timeout_sec` | 5.0 | Python `__init__` | Max search duration |
| `CAM_HEIGHT` | 480 | JS `renderer.js` | Must match actual camera res |
```
