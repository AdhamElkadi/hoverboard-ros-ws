## Startup Sequence

### Option A: Manual Control Stack (Primary)
Starts Flask Web UI (port 5000), `manual_controller`, `face_detector`, `eilik_bridge`, and Electron Eilik eyes:
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch hoverboard_control WebCamera.launch.py
```
Open browser on phone/laptop connected to hotspot: `http://<laptop-ip>:5000`

### Option B: Autonomous Control Stack
Starts `fusion_controller`, `web_controller`, and `azure_kinect_publisher`:
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch hoverboard_control camera.launch.py
```

> ⚠️ **Note:** Do NOT launch both stacks simultaneously as both web controllers bind port 5000.

## Diagnostic Commands

1. **Verify Base Commands from Web UI:**
   ```bash
   ros2 topic echo /app_command std_msgs/msg/String
   ```
2. **Verify Head Commands from Web UI:**
   ```bash
   ros2 topic echo /head/command std_msgs/msg/String
   ```
3. **Verify Face Tracking Point:**
   ```bash
   ros2 topic echo /face/center --once
   ```

## Troubleshooting Matrix

| Symptom | Likely Cause | Diagnostic Command | Fix |
| :--- | :--- | :--- | :--- |
| STM32 beeping continuously | Speed=0 or missing keep-alive | Check ESP32 Serial Monitor | Set `TURN_SPEED=50` in ESP32 firmware |
| Motors don't respond to L/R/S | Wrong serial port or permissions | `ls /dev/ttyUSB*` | `sudo chmod 666 /dev/ttyUSB*` + re-plug cable |
| Head buttons unresponsive | Wrong launch file or web route error | `curl -i http://localhost:5000/head/U` | Run `WebCamera.launch.py` and hard-refresh browser |
| Eyes squashed vertically | Bad Y-normalization or NaN | Open Electron DevTools → Console | Verify `CAM_HEIGHT` matches actual camera resolution |
| Face tracking jittery/spasmodic | Hallucination filters too loose | `ros2 topic echo /face/center` | Increase `min_confidence` to 0.85 in `face_detector.py` |
| Port 5000 already in use | Stale Flask process | `ss -ltnp '( sport = :5000 )'` | Kill stale process or launch single stack |

## Calibration Guide

### Tuning Anti-Hallucination Filters
Adjust in `face_detector.py` `__init__()`:
-   **Too many false positives?** → Increase `min_confidence` to 0.85 or `min_face_size_ratio` to 0.08
-   **Losing face during fast turns?** → Increase `max_pixel_jump` to 180 or decrease `min_confidence` to 0.65
-   **Tracking feels laggy?** → Decrease `required_valid_frames` to 2 or increase `smoothing_factor` to 0.25

### Tuning Search Behavior
Adjust in `face_search_controller.py` `__init__()`:
-   **Search ends too quickly?** → Increase `search_timeout_sec` to 8.0
-   **Turns too aggressive for camera?** → Reduce `TURN_STEER` equivalent in ESP32 to 200
-   **Wants wider sweep pattern?** → Not applicable (uses last-known-direction, not sweep); consider adding adaptive search module

### Tuning Gaze Tracking
Adjust in `renderer.js`:
-   **Eyes move opposite to face vertically?** → Invert Y: `ny = -((msg.point.y / CAM_HEIGHT) * 2.0 - 1.0)`
-   **Eyes don't reach screen edges?** → Increase `gazeLayoutScale()` return value in `script.js` (currently 1.0 for fullscreen)
-   **Pupil movement too subtle?** → Adjust `pupilRangeX/Y` in `roboeyes-dom.js` (default: 22/18)
