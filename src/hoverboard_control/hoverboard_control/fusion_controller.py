import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, String
from cv_bridge import CvBridge
import serial
import time
import numpy as np
import threading

class FusionController(Node):
    def __init__(self):
        super().__init__('fusion_controller')

        # ── Parameters ──
        self.declare_parameter('manual_return_timeout', 15.0)  # sec before returning to autonomous

        # Subscriptions
        self.face_sub = self.create_subscription(PointStamped, '/face/center', self.face_callback, 10)
        self.bridge = CvBridge()
        self.depth_sub = self.create_subscription(Image, '/depth/image_raw', self.depth_callback, 10)
        # NEW: listen for manual commands from the phone (via web_controller)
        self.cmd_sub = self.create_subscription(String, '/app_command', self.manual_callback, 10)

        # Publishers
        self.pub_rear = self.create_publisher(Float32, '/sensor/ultrasonic/rear', 10)
        self.eilik_pub = self.create_publisher(String, '/eilik/command', 10)
        self.state_pub = self.create_publisher(String, '/robot/state', 10)  # NEW: mode feedback

        # ── Eilik Emotion ──
        self.last_emotion = ''
        self.love_start_time = None
        self.LOVE_DURATION = 3.0
        self.SAD_SEARCH_THRESHOLD = 3.0
        self.stop_start_time = None
        self.STOP_SLEEPY_THRESHOLD = 15.0

        # ── MANUAL override state ──
        self.manual_command = 'S'
        self.last_manual_time = self.get_clock().now()
        self.MANUAL_RETURN_TIMEOUT = self.get_parameter('manual_return_timeout').value

        # Reactive Sensor State
        self.front_dist_mm = 0
        self.rear_dist_cm = 100.0

        # Stable State Machine (now includes MANUAL)
        self.state = "ROAMING"
        self._last_published_state = None
        self.last_face_time = self.get_clock().now()
        self.last_face_x = 320.0
        self.search_direction = 'R'
        self.search_start_time = self.get_clock().now()
        self.face_lost_count = 0
        self.FACE_LOST_THRESHOLD = 5

        # Serial Connection
        self.ser = None
        self.serial_lock = threading.Lock()
        self._serial_line_buf = ""

        try:
            for port in ['/dev/ttyUSB0', '/dev/ttyACM0']:
                try:
                    self.ser = serial.Serial(port, 115200, timeout=0.02)
                    time.sleep(1)
                    self.get_logger().info(f"✅ Connected to ESP via {port}")
                    break
                except Exception:
                    continue
            if not self.ser:
                self.get_logger().error("❌ Could not connect to ESP32")
        except Exception as e:
            self.get_logger().error(f"Serial Init Error: {e}")

        # Timers
        self.control_timer = self.create_timer(0.1, self.control_loop)
        self.sensor_timer = self.create_timer(0.08, self.read_sensor_data)

        self.set_eilik_emotion('neutral')
        self.get_logger().info("🎭 Eilik + 🎮 Manual override ready")
        self.get_logger.info if False else None
        self.get_logger().info("   Phone movement → MANUAL | 'AUTO' or 15s idle → autonomous")

    # ═══════════════════════════════════════════════════════════
    # EILIK EMOTION
    # ═══════════════════════════════════════════════════════════
    def set_eilik_emotion(self, emotion: str):
        if emotion == self.last_emotion:
            return
        self.last_emotion = emotion
        msg = String()
        msg.data = emotion
        self.eilik_pub.publish(msg)
        self.get_logger().info(f"🎭 Eilik → {emotion}")

    def _track_stop_time(self, cmd: str):
        if cmd == 'S':
            if self.stop_start_time is None:
                self.stop_start_time = self.get_clock().now()
        else:
            self.stop_start_time = None

    def _is_sleepy(self) -> bool:
        if self.stop_start_time is None:
            return False
        elapsed = (self.get_clock().now() - self.stop_start_time).nanoseconds / 1e9
        return elapsed >= self.STOP_SLEEPY_THRESHOLD

    # ═══════════════════════════════════════════════════════════
    # STATE PUBLISHING (for phone display)
    # ═══════════════════════════════════════════════════════════
    def _publish_state(self):
        if self.state != self._last_published_state:
            self._last_published_state = self.state
            msg = String()
            msg.data = self.state
            self.state_pub.publish(msg)

    # ═══════════════════════════════════════════════════════════
    # MANUAL COMMAND CALLBACK (from phone via web_controller)
    # ═══════════════════════════════════════════════════════════
    def manual_callback(self, msg):
        cmd = msg.data.strip().upper()
        now = self.get_clock().now()

        # 'AUTO' releases manual control → back to autonomous
        if cmd == 'AUTO':
            if self.state == "MANUAL":
                self.state = "ROAMING"
                self.face_lost_count = 0
                self.set_eilik_emotion('neutral')
                self.get_logger().info("🤖 AUTO released → ROAMING (autonomous)")
            return

        # Movement commands engage manual override
        if cmd in ('F', 'B', 'L', 'R', 'S'):
            if self.state != "MANUAL":
                self.get_logger().info(f"🎮 Manual override engaged (was {self.state})")
                self.set_eilik_emotion('neutral')
            self.state = "MANUAL"
            self.manual_command = cmd
            self.last_manual_time = now

    # ═══════════════════════════════════════════════════════════
    # SENSOR CALLBACKS
    # ═══════════════════════════════════════════════════════════
    def face_callback(self, msg):
        self.last_face_time = self.get_clock().now()
        self.last_face_x = msg.point.x
        self.face_lost_count = 0

    def depth_callback(self, msg):
        try:
            depth_array = self.bridge.imgmsg_to_cv2(msg, 'mono16')
            h, w = depth_array.shape
            center_region = depth_array[h//2-5:h//2+5, w//2-5:w//2+5]
            valid_pixels = center_region[center_region > 0]
            self.front_dist_mm = int(np.median(valid_pixels)) if len(valid_pixels) > 0 else 0
        except Exception as e:
            self.get_logger().error(f"Depth processing failed: {e}")
            self.front_dist_mm = 0

    def read_sensor_data(self):
        if not self.ser:
            return
        with self.serial_lock:
            try:
                n = self.ser.in_waiting
                if n == 0:
                    return
                raw = self.ser.read(n).decode('utf-8', errors='ignore')
                for ch in raw:
                    if ch == '\n':
                        line = self._serial_line_buf.strip()
                        self._serial_line_buf = ""
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
                        self._serial_line_buf += ch
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # CONTROL LOOP
    # ═══════════════════════════════════════════════════════════
    def control_loop(self):
        if not self.ser:
            return

        now = self.get_clock().now()
        elapsed_search = (now - self.search_start_time).nanoseconds / 1e9

        cmd = 'S'
        reason = "DEFAULT_STOP"

        BACKUP_THRESHOLD = 30.0
        STOP_THRESHOLD = 22.0

        # ── 1. SAFETY OVERRIDES (always active, even in MANUAL) ──
        if self.rear_dist_cm <= STOP_THRESHOLD and self.rear_dist_cm > 0:
            cmd = 'S'
            reason = f"REAR_STOP({self.rear_dist_cm:.0f}cm)"
            self.set_eilik_emotion('surprised')
            self._track_stop_time(cmd)
            self._send_command(cmd, reason, now)
            return

        if 0 < self.front_dist_mm < 500:
            if self.rear_dist_cm <= STOP_THRESHOLD and self.rear_dist_cm > 0:
                cmd = 'S'
                reason = f"TRAPPED(F:{self.front_dist_mm}mm|R:{self.rear_dist_cm:.0f}cm)"
                self.set_eilik_emotion('surprised')
            elif self.rear_dist_cm >= BACKUP_THRESHOLD:
                cmd = 'B'
                reason = f"BACKING_UP(Rear:{self.rear_dist_cm:.0f}cm)"
                self.set_eilik_emotion('surprised')
            else:
                cmd = 'S'
                reason = f"HOLDING(Rear:{self.rear_dist_cm:.0f}cm)"
                self.set_eilik_emotion('surprised')
            self._track_stop_time(cmd)
            self._send_command(cmd, reason, now)
            return

        # ── 2. MANUAL OVERRIDE (phone in control) ──
        if self.state == "MANUAL":
            elapsed = (now - self.last_manual_time).nanoseconds / 1e9
            if elapsed < self.MANUAL_RETURN_TIMEOUT:
                # Honor the last command from the phone
                cmd = self.manual_command
                reason = f"MANUAL({cmd}|{elapsed:.0f}s)"
            else:
                # No phone activity for a while → hand back to autonomous
                self.state = "ROAMING"
                self.face_lost_count = 0
                self.set_eilik_emotion('neutral')
                self.get_logger().info("⏱️ Manual idle timeout → ROAMING (autonomous)")
                cmd = 'F'
                reason = "ROAMING"
            self._track_stop_time(cmd)
            self._send_command(cmd, reason, now)
            return

        # ── 3. AUTONOMOUS STATE MACHINE ──
        elapsed_since_face = (now - self.last_face_time).nanoseconds / 1e9
        if elapsed_since_face > 0.15:
            self.face_lost_count += 1
        else:
            self.face_lost_count = 0

        if self.state == "TRACKING":
            if self.face_lost_count >= self.FACE_LOST_THRESHOLD:
                self.state = "SEARCHING"
                self.search_start_time = now
                self.search_direction = 'R' if self.last_face_x < 320 else 'L'
                self.love_start_time = None
                self.set_eilik_emotion('confused')
                self.get_logger().info(f"🔍 Face lost → SEARCHING {self.search_direction}")
            else:
                cmd = 'S'
                reason = f"TRACKING(x={self.last_face_x:.0f}|lost={self.face_lost_count}/{self.FACE_LOST_THRESHOLD})"
                if self.love_start_time is not None:
                    love_elapsed = (now - self.love_start_time).nanoseconds / 1e9
                    self.set_eilik_emotion('love' if love_elapsed < self.LOVE_DURATION else 'smile')
                else:
                    self.set_eilik_emotion('smile')

        elif self.state == "SEARCHING":
            if self.face_lost_count == 0:
                self.state = "TRACKING"
                self.love_start_time = None
                self.set_eilik_emotion('smile')
                self.get_logger().info(f"✅ Face found during search → TRACKING")
            elif elapsed_search >= 5.0:
                self.state = "ROAMING"
                self.face_lost_count = 0
                self.love_start_time = None
                self.set_eilik_emotion('neutral')
                self.get_logger().info("⏱️ 5s search complete → ROAMING")
            else:
                cmd = self.search_direction
                reason = f"SEARCHING({self.search_direction}|{elapsed_search:.1f}s/5.0s)"
                self.set_eilik_emotion('sad' if elapsed_search >= self.SAD_SEARCH_THRESHOLD else 'confused')

        elif self.state == "ROAMING":
            if self.face_lost_count == 0 and elapsed_since_face < 0.1:
                self.state = "TRACKING"
                self.love_start_time = now
                self.set_eilik_emotion('love')
                self.get_logger().info(f"💕 Face confirmed → TRACKING + LOVE")
            else:
                cmd = 'F'
                reason = "ROAMING"
                self.set_eilik_emotion('sleepy' if self._is_sleepy() else 'neutral')

        self._track_stop_time(cmd)
        self._send_command(cmd, reason, now)

    def _send_command(self, cmd, reason, now):
        self._publish_state()  # publish mode whenever we act
        with self.serial_lock:
            try:
                self.ser.write(f'{cmd}\n'.encode())
                self.ser.flush()
            except Exception as e:
                self.get_logger().error(f"Write failed: {e}")

        if int(now.nanoseconds / 1e9) % 1 == 0:
            self.get_logger().info(
                f"CMD:{cmd} | {reason} | Front:{self.front_dist_mm}mm | Rear:{self.rear_dist_cm:.1f}cm | State:{self.state} | 🎭{self.last_emotion}"
            )


def main(args=None):
    rclpy.init(args=args)
    node = FusionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            msg = String()
            msg.data = 'sleepy'
            node.eilik_pub.publish(msg)
        except Exception:
            pass
        if node.ser and node.ser.is_open:
            try:
                node.ser.close()
            except Exception:
                pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
