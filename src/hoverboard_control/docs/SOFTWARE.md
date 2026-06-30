## Core Modules

### `face_search_controller.py`
**Purpose:** Autonomous face search and tracking motor control  
**Key Features:**
-   State machine with `is_searching` and `search_timed_out` flags to prevent rapid-fire start/stop cycles
-   5-second search timeout after face loss; 1.5-second grace period before initiating search
-   Continuous ASCII command stream (`L\n`, `R\n`, `S\n`) at 30Hz to satisfy ESP32 500ms timeout
-   Remembers last-known face position to determine search direction

### `esp32_hoverboard_face_tracking.ino`
**Purpose:** Serial bridge between Python ROS node and STM32 hoverboard controller  
**Key Features:**
-   Dual-mode parser: Accepts both ASCII chars (`L/R/S`) and raw binary packets
-   Silent keep-alive: Sends valid neutral packets every 100ms to prevent STM32 fault beeps
-   Rate limiting: Applies `STEER_RATE_LIMIT=60` to smooth motor transitions
-   Safety timeout: Forces STOP if no command received for 500ms

### Eilik Expression Engine (Customized)
Modified from Shutter Studio's official Robot Eyes Hub to integrate with ROS face tracking.

#### Modified Files
| File | Original Name | Changes Made |
| :--- | :--- | :--- |
| `style.css` | `eilik-face.css` | Renamed; adjusted `--face-zoom: 0.72` for fullscreen robot display; added `.robot-screen` overrides |
| `script.js` | N/A | Added ROS bridge override in `setFaceTrack()`; forced eyes open on init via `forceEyesOpen()`; implemented `gazeLayoutScale()` returning 1.0 for fullscreen |
| `roboeyes-dom.js` | N/A | Integrated with `window.setEyeGaze` API; exposed `RoboEyesDom` globally; added safety clamps for gaze coordinates |
| `renderer.js` | N/A | Subscribes to `/face/center`; normalizes pixel coords to [-1,1]; applies mirror inversion on X-axis |

#### Unmodified Modules (Loaded As-Is)
-   `eilik-morph.js`: SVG path interpolation via Flubber library (15+ emotions)
-   `eilik-animations.js`: Transient reaction animations (pop, jiggle, laugh-bounce)
-   `eilik-kiss.js`: Flying heart animation triggered on "kiss" emotion
-   `eilik-love.js`: Heart-eye pulse + sparkle FX on "love" emotion
-   `face-track.js`: Webcam face detector stub (overridden by ROS bridge in production)

## Dependencies & Versions
Install these exact versions to avoid compatibility issues:

```bash
pip3 install opencv-python==4.9.0 mediapipe==0.10.14 pyserial==3.5 --break-system-packages
npm install electron@28.0 rclnodejs@2.0 flubber@0.4.2
