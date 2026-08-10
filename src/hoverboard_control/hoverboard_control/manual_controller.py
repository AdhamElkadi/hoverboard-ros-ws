#!/usr/bin/env python3
"""
manual_controller.py - Web Controller for Base + Head with Safety Overrides
ESP32 Base: /dev/ttyUSB0 | ESP8266 Head: /dev/ttyUSB1
Safety-only sensors. No autonomous behavior.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, String
from cv_bridge import CvBridge
import serial
import time
import numpy as np
import threading


class ManualController(Node):
    BASE_SERIAL_PORT = '/dev/ttyUSB0'
    HEAD_SERIAL_PORT = '/dev/ttyUSB1'

    def __init__(self):
        super().__init__('manual_controller')
        self.declare_parameter('manual_timeout', 2.0)
        self.declare_parameter('front_stop_mm', 500)
        self.declare_parameter('rear_stop_cm', 22.0)
        self.declare_parameter('rear_backup_cm', 30.0)
        self.declare_parameter('head_cmd_interval', 0.02)

        self.bridge = CvBridge()
        self.cmd_sub = self.create_subscription(String, '/app_command', self.base_callback, 10)
        self.head_sub = self.create_subscription(String, '/head/command', self.head_callback, 10)
        self.depth_sub = self.create_subscription(Image, '/depth/image_raw', self.depth_callback, 10)

        self.pub_rear = self.create_publisher(Float32, '/sensor/ultrasonic/rear', 10)
        self.eilik_pub = self.create_publisher(String, '/eilik/command', 10)
        self.state_pub = self.create_publisher(String, '/robot/state', 10)

        self.last_emotion = ''
        self.stop_start_time = None
        self.STOP_SLEEPY_THRESHOLD = 15.0
        self.base_command = 'S'
        self.last_base_time = self.get_clock().now()
        self.MANUAL_TIMEOUT = self.get_parameter('manual_timeout').value
        self._last_head_pan_send = 0.0
        self._last_head_tilt_send = 0.0
        self.HEAD_CMD_INTERVAL = self.get_parameter('head_cmd_interval').value
        self.front_dist_mm = 0
        self.rear_dist_cm = 100.0
        self.base_serial_lock = threading.Lock()
        self.head_serial_lock = threading.Lock()
        self._base_line_buf = ""

        self.base_ser = None
        try:
            self.base_ser = serial.Serial(self.BASE_SERIAL_PORT, 115200, timeout=0.02)
            time.sleep(1)
            self.get_logger().info(f"Base ESP32 connected via {self.BASE_SERIAL_PORT}")
        except serial.SerialException as e:
            self.get_logger().error(f"Base ESP32 failed on {self.BASE_SERIAL_PORT}: {e}")

        self.head_ser = None
        try:
            self.head_ser = serial.Serial(self.HEAD_SERIAL_PORT, 115200, timeout=0.1)
            time.sleep(1)
            self.get_logger().info(f"Head ESP8266 connected via {self.HEAD_SERIAL_PORT}")
        except serial.SerialException as e:
            self.get_logger().error(f"Head ESP8266 failed on {self.HEAD_SERIAL_PORT}: {e}")

        self.control_timer = self.create_timer(0.1, self.control_loop)
        self.sensor_timer = self.create_timer(0.08, self.read_sensor_data)
        self.set_eilik_emotion('neutral')
        self.get_logger().info("Manual Controller Ready")

    def set_eilik_emotion(self, emotion):
        if emotion == self.last_emotion:
            return
        self.last_emotion = emotion
        msg = String()
        msg.data = emotion
        self.eilik_pub.publish(msg)

    def _track_stop_time(self, cmd):
        if cmd == 'S':
            if self.stop_start_time is None:
                self.stop_start_time = self.get_clock().now()
        else:
            self.stop_start_time = None

    def _is_sleepy(self):
        if self.stop_start_time is None:
            return False
        elapsed = (self.get_clock().now() - self.stop_start_time).nanoseconds / 1e9
        return elapsed >= self.STOP_SLEEPY_THRESHOLD

    def _publish_state(self, state):
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)

    def base_callback(self, msg):
        cmd = msg.data.strip().upper()
        if cmd in ('F', 'B', 'L', 'R', 'S'):
            self.base_command = cmd
            self.last_base_time = self.get_clock().now()

    def head_callback(self, msg):
        if not self.head_ser or not self.head_ser.is_open:
            self.get_logger().warn("Head command received but head serial port is not open!")
            return
        cmd = msg.data.strip()
        if len(cmd) != 1:
            return
        now = time.time()
        axis = None
        if cmd in ('Y', 'Z', 'y', 'z'):
            axis = 'pan'
        elif cmd in ('U', 'D', 'u', 'd'):
            axis = 'tilt'
        else:
            return
        if axis == 'pan':
            if now - self._last_head_pan_send < self.HEAD_CMD_INTERVAL:
                return
            self._last_head_pan_send = now
        elif axis == 'tilt':
            if now - self._last_head_tilt_send < self.HEAD_CMD_INTERVAL:
                return
            self._last_head_tilt_send = now
        with self.head_serial_lock:
            try:
                self.head_ser.write(cmd.encode('ascii'))
                self.get_logger().info(f"HEAD CMD:{cmd} sent to {self.HEAD_SERIAL_PORT}")
            except serial.SerialException as e:
                self.get_logger().warn(f"Head serial error: {e}")

    def depth_callback(self, msg):
        try:
            depth_array = self.bridge.imgmsg_to_cv2(msg, 'mono16')
            h, w = depth_array.shape
            center_region = depth_array[h//2-5:h//2+5, w//2-5:w//2+5]
            valid_pixels = center_region[center_region > 0]
            self.front_dist_mm = int(np.median(valid_pixels)) if len(valid_pixels) > 0 else 0
        except Exception as e:
            self.get_logger().error(f"Depth failed: {e}")
            self.front_dist_mm = 0

    def read_sensor_data(self):
        if not self.base_ser:
            return
        with self.base_serial_lock:
            try:
                n = self.base_ser.in_waiting
                if n == 0:
                    return
                raw = self.base_ser.read(n).decode('utf-8', errors='ignore')
                for ch in raw:
                    if ch == '\n':
                        line = self._base_line_buf.strip()
                        self._base_line_buf = ""
                        if line.startswith('U:'):
                            try:
                                dist = float(line[2:])
                                self.rear_dist_cm = dist
                                m = Float32()
                                m.data = dist
                                self.pub_rear.publish(m)
                            except ValueError:
                                pass
                    elif ch == '\r':
                        continue
                    else:
                        self._base_line_buf += ch
            except Exception:
                pass

    def control_loop(self):
        if not self.base_ser:
            return
        now = self.get_clock().now()
        elapsed_since_cmd = (now - self.last_base_time).nanoseconds / 1e9
        front_stop = self.get_parameter('front_stop_mm').value
        rear_stop = self.get_parameter('rear_stop_cm').value
        rear_backup = self.get_parameter('rear_backup_cm').value
        cmd = 'S'
        reason = "DEFAULT_STOP"

        if self.rear_dist_cm <= rear_stop and self.rear_dist_cm > 0:
            cmd = 'S'
            reason = f"REAR_SAFETY({self.rear_dist_cm:.0f}cm)"
            self.set_eilik_emotion('surprised')
            self._track_stop_time(cmd)
            self._send_base_command(cmd, reason, now)
            return

        if 0 < self.front_dist_mm < front_stop:
            if self.rear_dist_cm >= rear_backup:
                cmd = 'B'
                reason = f"FRONT_BACKUP(F:{self.front_dist_mm}mm|R:{self.rear_dist_cm:.0f}cm)"
            else:
                cmd = 'S'
                reason = f"TRAPPED(F:{self.front_dist_mm}mm|R:{self.rear_dist_cm:.0f}cm)"
            self.set_eilik_emotion('surprised')
            self._track_stop_time(cmd)
            self._send_base_command(cmd, reason, now)
            return

        if elapsed_since_cmd < self.MANUAL_TIMEOUT:
            cmd = self.base_command
            reason = f"MANUAL({cmd}|{elapsed_since_cmd:.1f}s)"
            self.set_eilik_emotion('sleepy' if cmd == 'S' and self._is_sleepy() else ('happy' if cmd != 'S' else 'neutral'))
        else:
            cmd = 'S'
            reason = f"TIMEOUT({elapsed_since_cmd:.1f}s)"
            self.base_command = 'S'
            self.set_eilik_emotion('sleepy' if self._is_sleepy() else 'neutral')

        self._track_stop_time(cmd)
        self._send_base_command(cmd, reason, now)

    def _send_base_command(self, cmd, reason, now):
        self._publish_state("MANUAL")
        with self.base_serial_lock:
            try:
                self.base_ser.write((cmd + '\n').encode())
                self.base_ser.flush()
            except Exception as e:
                self.get_logger().error(f"Base write failed: {e}")
        if int(now.nanoseconds / 1e9) % 1 == 0:
            self.get_logger().info(
                f"CMD:{cmd} | {reason} | F:{self.front_dist_mm}mm | R:{self.rear_dist_cm:.1f}cm"
            )

    def destroy_node(self):
        try:
            self.get_logger().info("Shutting down...")
        except Exception:
            pass
        try:
            if self.base_ser and self.base_ser.is_open:
                self.base_ser.write(b'S\n')
                self.base_ser.flush()
                time.sleep(0.1)
                self.base_ser.close()
        except Exception:
            pass
        try:
            if self.head_ser and self.head_ser.is_open:
                self.head_ser.close()
        except Exception:
            pass
        try:
            msg = String()
            msg.data = 'sleepy'
            self.eilik_pub.publish(msg)
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ManualController()
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
