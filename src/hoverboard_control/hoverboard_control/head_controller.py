#!/usr/bin/env python3
"""
head_controller.py - ROS 2 Bridge for ESP8266 Head Controller
Behavior:
  - Face VISIBLE: Live pan+tilt tracking via continuous Y/Z/U/D commands
  - Face LOST: STOP SENDING COMMANDS → ESP8266 auto-stops motors via timeout
  - NO explicit stop commands (lowercase y/u are NOT stops)
Uses per-axis rate limiting and BestEffort QoS.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import PointStamped
import serial
import time
import threading


class HeadController(Node):
    # === CONFIGURATION ===
    SERIAL_PORT = '/dev/ttyUSB2'       # ESP8266 head controller
    BAUD_RATE = 115200
    MIN_CMD_INTERVAL_SEC = 0.02        # Per-axis rate limit (50 cmd/s max)

    # Tracking parameters
    PAN_GAIN = 0.8
    TILT_GAIN = 0.5
    DEADZONE_PX = 60
    CAM_CENTER_X = 320.0
    CAM_CENTER_Y = 240.0

    # Face loss detection
    FACE_LOST_TIMEOUT_SEC = 0.5        # No face messages for this long → stop sending

    def __init__(self):
        super().__init__('head_controller')

        # Serial connection
        self._serial_lock = threading.Lock()
        try:
            self.ser = serial.Serial(
                port=self.SERIAL_PORT,
                baudrate=self.BAUD_RATE,
                timeout=0.1
            )
            time.sleep(1)
            self.get_logger().info(f"✅ Connected to ESP8266 on {self.SERIAL_PORT}")
        except serial.SerialException as e:
            self.get_logger().error(f"❌ Serial open failed: {e}")
            self.ser = None
            return

        # Per-axis rate limiting
        self._last_pan_send_time = 0.0
        self._last_tilt_send_time = 0.0

        # Face state
        self._last_face_time = self.get_clock().now()

        # QoS matching face_detector
        face_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.create_subscription(
            PointStamped, '/face/center', self._face_callback, face_qos
        )

        # Control loop at ~30 Hz
        self.create_timer(0.033, self._control_loop)

        self.get_logger().info("Head controller ready. Track-only mode (silence = stop).")

    def _send_command(self, cmd: str, axis: str = 'pan'):
        """Thread-safe serial write with per-axis rate limiting.
        Only sends UPPERCASE direction commands. Never sends lowercase."""
        now = time.time()
        if axis == 'pan':
            if now - self._last_pan_send_time < self.MIN_CMD_INTERVAL_SEC:
                return
            self._last_pan_send_time = now
        elif axis == 'tilt':
            if now - self._last_tilt_send_time < self.MIN_CMD_INTERVAL_SEC:
                return
            self._last_tilt_send_time = now

        with self._serial_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(cmd.encode('ascii'))
                except serial.SerialException as e:
                    self.get_logger().warn(f"Serial write error: {e}")

    def _face_callback(self, msg: PointStamped):
        """Update last face timestamp. Actual motor commands sent in control_loop."""
        self._last_face_time = self.get_clock().now()

    def _control_loop(self):
        """Main control loop: send commands ONLY while face is visible."""
        if not self.ser or not self.ser.is_open:
            return

        now = self.get_clock().now()
        elapsed = (now - self._last_face_time).nanoseconds / 1e9

        # ✅ FACE LOST: Simply stop sending commands.
        # ESP8266 auto-stops motors via its internal serial timeout.
        # Do NOT send 'y', 'u', or any other character.
        if elapsed >= self.FACE_LOST_TIMEOUT_SEC:
            return  # Silence = stop

        # === FACE VISIBLE: Send continuous tracking commands ===
        # We need the latest face position, but callbacks are async.
        # Store last known position in callback and use it here.
        # For simplicity, we re-subscribe to get latest in callback
        # and store it. Let's add that storage:
        pass  # Handled below with stored coordinates

    def _face_callback(self, msg: PointStamped):
        """Store face position AND send tracking commands directly."""
        self._last_face_time = self.get_clock().now()

        x_err = msg.point.x - self.CAM_CENTER_X
        y_err = msg.point.y - self.CAM_CENTER_Y

        # --- PAN TRACKING ---
        if abs(x_err) >= self.DEADZONE_PX:
            if x_err > 0:
                self._send_command('Z', axis='pan')   # Face RIGHT → Head RIGHT
            else:
                self._send_command('Y', axis='pan')   # Face LEFT → Head LEFT
        # ✅ IN DEADZONE: Send NOTHING. ESP8266 stops pan via timeout.

        # --- TILT TRACKING ---
        if abs(y_err) >= self.DEADZONE_PX:
            tilt_pct = int(-y_err * self.TILT_GAIN)
            if tilt_pct > 0:
                self._send_command('U', axis='tilt')  # Face UP → Head UP
            else:
                self._send_command('D', axis='tilt')  # Face DOWN → Head DOWN
        # ✅ IN DEADZONE: Send NOTHING. ESP8266 stops tilt via timeout.

    def destroy_node(self):
        """On shutdown: just close serial. ESP8266 auto-stops on disconnect."""
        try:
            self.get_logger().info("Shutting down head controller...")
        except Exception:
            pass
        # ✅ Do NOT send any stop commands. Just close port.
        # ESP8266 detects serial closure/disconnect and stops motors.
        try:
            if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HeadController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
