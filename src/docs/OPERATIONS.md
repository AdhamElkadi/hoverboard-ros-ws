## Startup Sequence
Execute in this exact order to ensure all subsystems initialize correctly:

1.  **Source Workspace & Launch Perception**
    ```bash
    source ~/ros2_ws/install/setup.bash
    ros2 launch hoverboard_control camera.launch.py
    ```
2.  **Verify Face Detection Output**
    ```bash
    ros2 topic echo /face/center --once
    ```
    Expected: Valid `PointStamped` with x/y within [0,640] / [0,480]. If empty, check camera permissions and lighting.
3.  **Start ESP32 Serial Bridge**
    ```bash
    # Verify port exists first
    ls /dev/ttyUSB*
    # Fix permissions if needed
    sudo usermod -aG dialout $USER && sudo chmod 666 /dev/ttyUSB*
    # Log out/in required for group change
    ```
4. **Start Face Detector Node**
    '''bash
    cd ~/ros2_ws 
    ros2 run hoverboard_control face_detector
    '''
5.  **Launch Electron Display App**
    ```bash
    cd ~/ros2_ws/src/hoverboard_control/eilik_app
    nvm use 20 > /dev/null 2>&1
    npm start
    ```
6.  **Start Face Search Controller**
    ```bash
    ros2 run hoverboard_control face_search_controller
    ```

## Troubleshooting Matrix

| Symptom | Likely Cause | Diagnostic Command | Fix |
| :--- | :--- | :--- | :--- |
| STM32 beeping continuously | Speed=0 or missing keep-alive | Check ESP32 Serial Monitor | Set `TURN_SPEED=50` in ESP32 firmware |
| Motors don't respond to L/R/S | Wrong serial port or permissions | `ls /dev/ttyUSB*` | `sudo chmod 666 /dev/ttyUSB*` + re-plug cable |
| Eyes squashed vertically | Bad Y-normalization or NaN | Open Electron DevTools → Console | Verify `CAM_HEIGHT` matches actual camera resolution |
| Face tracking jittery/spasmodic | Hallucination filters too loose | `ros2 topic echo /face/center` | Increase `min_confidence` to 0.85 in `face_detector.py` |
| Rapid search start/stop spam | Missing `search_timed_out` flag | Check controller logs | Update `face_search_controller.py` state logic |
| "BAD FRAME" in ESP32 logs | Checksum mismatch or byte order | Verify Python `struct.pack('<HhhH',...)` | Ensure little-endian `<` prefix and XOR formula |
| Electron app shows white flash | Missing background color | Check `main.js` | Set `backgroundColor: '#000000'` in BrowserWindow options |
| Face detector crashes on startup | Missing cv2 dependency | `python3 -c "import cv2"` | `pip3 install opencv-python --break-system-packages` |

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
