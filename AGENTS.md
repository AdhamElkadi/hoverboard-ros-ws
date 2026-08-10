# Hoverboard Control Workspace

## Package And Validation

- This workspace contains one ROS 2 Python package: `src/hoverboard_control`. Its executable node names are defined in `src/hoverboard_control/setup.py`.
- After changing package Python, launch, or packaged Electron-app files, rebuild and re-source before running ROS commands:
  ```bash
  cd ~/ros2_ws
  colcon build --packages-select hoverboard_control
  source install/setup.bash
  ```
- Run the package checks with:
  ```bash
  colcon test --packages-select hoverboard_control
  colcon test-result --verbose
  ```
- After transferring or manually repairing Python files, validate their syntax before building:
  ```bash
  python3 -c "import ast; ast.parse(open('PATH').read()); print('VALID')"
  ```

## Runtime Modes

- `launch/WebCamera.launch.py` is the manual base-and-head stack: it starts `manual_controller` and `manual_web_controller`.
- `launch/camera.launch.py` is the separate autonomous stack: it starts `fusion_controller` and `web_controller`.
- Do not run both stacks together. The web controllers both bind port `5000`, and their motor-controller roles conflict.
- Some older documentation, especially `docs/OPERATIONS.md`, describes the autonomous `camera.launch.py` path. When documentation conflicts, use `setup.py`, launch files, and controller source as the source of truth.

## Manual Control Contracts

- `manual_controller.py` owns both serial devices: base `/dev/ttyUSB0` and head `/dev/ttyUSB1`, each at 115200 baud.
- Base commands flow `/app_command` -> ESP32 as newline-terminated `F`, `B`, `L`, `R`, or `S`.
- Head commands flow `/head/command` -> ESP8266 as a raw one-byte `U`, `D`, `Y`, or `Z`; never append a newline.
- Front depth and rear ultrasonic safety checks override manual base commands. Do not weaken or bypass them without an explicit safety requirement.
- To trace a web command safely, observe the ROS topic while an operator uses the UI:
  ```bash
  ros2 topic echo /app_command std_msgs/msg/String
  ros2 topic echo /head/command std_msgs/msg/String
  ros2 topic info -v /head/command
  ```
