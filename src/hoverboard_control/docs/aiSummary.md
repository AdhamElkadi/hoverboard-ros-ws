Here is a comprehensive project summary document designed to be given to an AI coding agent. It captures the architecture, hardware mapping, protocol specifics, and critical known issues derived from our debugging session.

***

# Project Context: Hoverboard ROS 2 Manual Control System

## 1. System Overview
This is a ROS 2 (Jazzy) teleoperation system for a hoverboard-based robot with a pan/tilt head and Eilik emotion display. The system operates in **Manual Mode** where all movement is commanded via a web UI on a phone connected to the laptop's hotspot. Sensors (depth camera + ultrasonic) act **only as safety overrides**, never for autonomous navigation.

## 2. Hardware & Serial Port Mapping (CRITICAL)
| Device | Port | Baud | Protocol | Notes |
| :--- | :--- | :--- | :--- | :--- |
| ESP32 (Base) | `/dev/ttyUSB0` | 115200 | ASCII + newline (`F\n`, `B\n`, `L\n`, `R\n`, `S\n`) | Ultrasonic data returned as `U:<dist_cm>\n` |
| ESP8266 (Head) | `/dev/ttyUSB1` | 115200 | Raw single byte (`Y`, `Z`, `U`, `D`) | **NO newline.** Silence = stop (internal timeout). Lowercase = same as uppercase. |
| Laptop Webcam | `/dev/video0` | N/A | V4L2 YUYV 640x480@30 | RGB for face detection → Eilik gaze |
| Azure Kinect | N/A | N/A | Depth only (RGB disabled) | Front obstacle safety only |

> ⚠️ **ESP8266 Head Protocol**: Motors run continuously while commands are received. They stop ONLY when serial commands cease (firmware internal timeout). There are NO explicit stop commands. Lowercase `y`/`u` are NOT stop commands — they behave identically to uppercase.

## 3. ROS 2 Node Architecture

### `manual_controller.py`
-   **Subscribes**: `/app_command` (base), `/head/command` (head), `/depth/image_raw` (safety)
-   **Publishes**: `/sensor/ultrasonic/rear`, `/eilik/command`, `/robot/state`
-   **Serial**: Opens BOTH `/dev/ttyUSB0` (base) and `/dev/ttyUSB1` (head) with separate locks
-   **Head callback**: Per-axis rate limiting (pan/tilt independent at 50Hz max). Writes raw byte via `self.head_ser.write(cmd.encode('ascii'))`
-   **Base control loop**: 10Hz timer. Safety checks run FIRST (rear stop ≤22cm, front stop <500mm). Then honors manual command if within 2s timeout, else auto-stops.
-   **Base serial write**: `(cmd + '\n').encode()` — newline is REQUIRED for ESP32 parsing

### `manual_web_controller.py`
-   **Flask server** on port 5000 serving HTML/CSS/JS control UI
-   **Publishes**: `/app_command`, `/head/command`, `/eilik/command`
-   **Routes**: `/move/<cmd>`, `/head/<cmd>`, `/emotion/<name>`, `/mode`
-   **Head "Hold" button**: Sends NO fetch request (silence triggers ESP8266 auto-stop)
-   **State polling**: JS polls `/mode` every 1s to update banner

### Supporting Nodes
-   `face_detector`: Publishes `/face/center` for Eilik eye gaze tracking
-   `eilik_bridge`: Translates emotion strings to Eilik display app
-   `usb_cam`: Laptop webcam driver
-   Electron app (`eilik_eyes`): Local display for Eilik emotions/gaze

## 4. Launch File: `WebCamera.launch.py`
1.  Activates hotspot via `nmcli connection up MyRobotHotspot`
2.  Waits 5 seconds for network/hardware init
3.  Starts: `usb_cam` → `face_detector` → `manual_controller` → `manual_web_controller` → `eilik_bridge` → `eilik_eyes` (Electron)

## 5. Web UI Command Protocol
| Button | Flask Route | ROS Topic | Serial Output |
| :--- | :--- | :--- | :--- |
| Fwd/Back/Left/Right/Stop | `/move/F` etc. | `/app_command` | `F\n` / `B\n` / `L\n` / `R\n` / `S\n` to ESP32 |
| Head Up/Down/Left/Right | `/head/U` etc. | `/head/command` | `U` / `D` / `Y` / `Z` (raw byte) to ESP8266 |
| Head Hold | None (JS only) | None | Stops sending → ESP8266 timeout stops motors |
| Emotions | `/emotion/<name>` | `/eilik/command` | String to eilik_bridge |

## 6. Known Issues & Critical Constraints

### File Corruption Problem
Python files transferred via chat/upload consistently lose indentation and corrupt `\n` escape sequences into literal line breaks. **Always verify syntax after any file transfer:**
```bash
python3 -c "import ast; ast.parse(open('FILE_PATH').read()); print('VALID')"
```
If invalid, use `nano` or `vim` to edit directly in terminal.

### Current Web-Head Diagnostics
1. **Manual UI only:** `WebCamera.launch.py` starts `manual_web_controller`, which is the only port-5000 UI with `/head/<cmd>` and `/head/command`. `camera.launch.py` starts `web_controller`, which handles base movement only. Do not run both web controllers.
2. **Head request visibility:** The manual UI uses explicit JavaScript listeners for buttons with `data-head-command`. A successful click requests `/head/U`, `/head/D`, `/head/Y`, or `/head/Z`; HTTP failures are displayed in the web-page status instead of being reported as a false success.
3. **ROS/serial visibility:** `manual_web_controller` logs `Web head command published: <cmd>` after publishing `/head/command`; `manual_controller` logs `HEAD CMD:<cmd> sent to /dev/ttyUSB1` after a serial write. This makes the browser -> ROS -> UART path traceable in the launch terminal.
4. **Port 5000 conflict:** Only one Flask controller can bind port 5000. Use `ss -ltnp '( sport = :5000 )'` and `ros2 node list` to identify the active stack rather than killing processes blindly.

### Build Procedure After Any Code Change
```bash
sudo lsof -ti:5000 | xargs kill -9 2>/dev/null
cd ~/ros2_ws && rm -rf install/hoverboard_control build/hoverboard_control
colcon build --packages-select hoverboard_control --force-cmake-clean
source install/setup.bash
```

## 7. Entry Points (setup.py)
All nodes registered under `hoverboard_control` package:
-   `manual_controller = hoverboard_control.manual_controller:main`
-   `manual_web_controller = hoverboard_control.manual_web_controller:main`
-   `face_detector`, `fusion_controller`, `head_controller`, `eilik_bridge`, `web_controller`, etc.

## 8. Key Design Decisions
-   **No autonomous behavior in manual mode**: Face detector runs ONLY for Eilik gaze, not for motor control
-   **Safety cannot be disabled**: Depth/ultrasonic overrides always take priority over manual commands
-   **Open-loop head control**: No encoder feedback. Virtual pose tracking in RViz is command-integration only
-   **Per-axis head rate limiting**: Pan and tilt have independent 20ms timers to prevent command starvation
-   **Dual serial architecture**: Base (ESP32) and head (ESP8266) are completely independent hardware with different protocols

## 9. Last Verified Session (2026-08-10)
- Updated `manual_web_controller.py` to use explicit head-button listeners and truthful HTTP responses for `/head/<cmd>`.
- Updated `manual_controller.py` with INFO-level head serial-write logging and a warning when the head serial port is unavailable.
- `python3` AST parsing passed for both manual controller files; `colcon build --packages-select hoverboard_control` passed. The package-wide lint/docstring test suite still has pre-existing failures outside this focused change.
- Runtime confirmation remains: restart the manual launch, hard-refresh the browser, then verify a head-button click produces a `U`/`D`/`Y`/`Z` Network request and `ros2 topic echo /head/command std_msgs/msg/String` output.
