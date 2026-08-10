#!/usr/bin/env python3
"""
Fusion Controller — The Brain of the Robot
Includes: Shin Detection, Global Pause, Manual Override, Clean Shutdown, Startup Warmup
"""
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
        self.declare_parameter('manual_return_timeout', 15.0)

        # Subscriptions
        self.face_sub = self.create_subscription(PointStamped, '/face/center', self.face_callback, 10)
        self.bridge = CvBridge()
        self.depth_sub = self.create_subscription(Image, '/depth/image_raw', self.depth_callback, 10)
        self.cmd_sub = self.create_subscription(String, '/app_command', self.manual_callback, 10)

        # Publishers
        self.pub_rear = self.create_publisher(Float32, '/sensor/ultrasonic/rear', 10)
        self.eilik_pub = self.create_publisher(String, '/eilik/command', 10)
        self.state_pub = self.create_publisher(String, '/robot/state', 10)
        self.face_center_pub = self.create_publisher(PointStamped, '/face/center', 10)

        # Eilik Emotion
        self.last_emotion = ''
        self.love_start_time = None
        self.LOVE_DURATION = 3.0
        self.SAD_SEARCH_THRESHOLD = 3.0
        self.stop_start_time = None
        self.STOP_SLEEPY_THRESHOLD = 15.0

        # Manual override state
        self.manual_command = 'S'
        self.last_manual_time = self.get_clock().now()
        self.MANUAL_RETURN_TIMEOUT = self.get_parameter('manual_return_timeout').value

        # Reactive Sensor State
        self.front_dist_mm = 0
        self.rear_dist_cm = 100.0

        # Stable State Machine
        self.state = "INITIALIZING" 
        self.startup_time = self.get_clock().now()
        self.WARMUP_DURATION = 5.0 
        
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
        self.get_logger().info(f"⏳ Waiting {self.WARMUP_DURATION}s for sensors to warm up...")

    def set_eilik_emotion(self, emotion: str):
        if emotion == self.last_emotion: return
        self.last_emotion = emotion
        msg = String(); msg.data = emotion
        self.eilik_pub.publish(msg)

    def _track_stop_time(self, cmd: str):
        if cmd == 'S':
            if self.stop_start_time is None: self.stop_start_time = self.get_clock().now()
        else: self.stop_start_time = None

    def _is_sleepy(self) -> bool:
        if self.stop_start_time is None: return False
        elapsed = (self.get_clock().now() - self.stop_start_time).nanoseconds / 1e9
        return elapsed >= self.STOP_SLEEPY_THRESHOLD

    def _publish_state(self):
        if self.state != self._last_published_state:
            self._last_published_state = self.state
            msg = String(); msg.data = self.state
            self.state_pub.publish(msg)

    def manual_callback(self, msg):
        cmd = msg.data.strip().upper()
        now = self.get_clock().now()
        if cmd == 'PAUSE':
            if self.state == "PAUSED":
                self.state = "ROAMING"; self.set_eilik_emotion('neutral')
            else:
                self.state = "PAUSED"; self.set_eilik_emotion('sleepy')
                center_msg = PointStamped(); center_msg.header.stamp = now.to_msg()
                center_msg.header.frame_id = 'camera_link'
                center_msg.point.x = 320.0; center_msg.point.y = 240.0
                self.face_center_pub.publish(center_msg)
            return
        if cmd == 'AUTO':
            if self.state == "MANUAL":
                self.state = "ROAMING"; self.face_lost_count = 0; self.set_eilik_emotion('neutral')
            return
        if cmd in ('F', 'B', 'L', 'R', 'S'):
            if self.state != "MANUAL":
                self.set_eilik_emotion('neutral')
            self.state = "MANUAL"; self.manual_command = cmd; self.last_manual_time = now

    def face_callback(self, msg):
        if self.state != "PAUSED":
            self.last_face_time = self.get_clock().now()
            self.last_face_x = msg.point.x
            self.face_lost_count = 0

    def depth_callback(self, msg):
        try:
            bridge = CvBridge()
            depth_array = bridge.imgmsg_to_cv2(msg, 'mono16')
            h, w = depth_array.shape
            
            # ✅ SHIN DETECTION LOGIC
            # 1. Check Center (Chest)
            center_region = depth_array[h//2-5:h//2+5, w//2-5:w//2+5]
            valid_center = center_region[center_region > 0]
            chest_dist = int(np.median(valid_center)) if len(valid_center) > 0 else 0
            
            # 2. Check Shins (Bottom 20%)
            bottom_strip = depth_array[int(h*0.8):h, :]
            valid_shins = bottom_strip[bottom_strip > 0]
            
            if len(valid_shins) > 0:
                shin_dist = int(np.median(valid_shins))
                
                # If shins see MUCH further than chest, it's an overhang!
                if shin_dist > chest_dist + 200 and chest_dist > 0:
                    self.front_dist_mm = 50 # Force stop
                    # self.get_logger().warn("⚠️ Overhang Detected!")
                else:
                    self.front_dist_mm = chest_dist
            else:
                # No data at shins? Assume obstacle/ledge.
                self.front_dist_mm = 50 
                
        except Exception as e:
            self.get_logger().error(f"Depth processing failed: {e}")
            self.front_dist_mm = 0

    def read_sensor_data(self):
        if not self.ser: return
        with self.serial_lock:
            try:
                n = self.ser.in_waiting
                if n == 0: return
                raw = self.ser.read(n).decode('utf-8', errors='ignore')
                for ch in raw:
                    if ch == '\n':
                        line = self._serial_line_buf.strip()
                        self._serial_line_buf = ""
                        if line.startswith('U:'):
                            try:
                                dist = float(line[2:])
                                self.rear_dist_cm = dist
                                m = Float32(); m.data = dist
                                self.pub_rear.publish(m)
                            except ValueError: pass
                    elif ch == '\r': continue
                    else: self._serial_line_buf += ch
            except Exception: pass

    def control_loop(self):
        if not self.ser: return
        now = self.get_clock().now()

        # ✅ Startup Warmup
        if self.state == "INITIALIZING":
            elapsed = (now - self.startup_time).nanoseconds / 1e9
            self._send_command('S', "WARMUP", now)
            if elapsed >= self.WARMUP_DURATION:
                self.state = "ROAMING"
                self.get_logger().info("✅ Sensors Ready! Starting Autonomous Mode.")
            return 

        # ✅ Global Pause
        if self.state == "PAUSED":
            self._send_command('S', "GLOBAL_PAUSE", now)
            self.set_eilik_emotion('sleepy')
            center_msg = PointStamped(); center_msg.header.stamp = now.to_msg()
            center_msg.header.frame_id = 'camera_link'
            center_msg.point.x = 320.0; center_msg.point.y = 240.0
            self.face_center_pub.publish(center_msg)
            return

        elapsed_search = (now - self.search_start_time).nanoseconds / 1e9
        cmd = 'S'; reason = "DEFAULT_STOP"
        BACKUP_THRESHOLD = 30.0; STOP_THRESHOLD = 22.0

        # Safety
        if self.rear_dist_cm <= STOP_THRESHOLD and self.rear_dist_cm > 0:
            cmd = 'S'; reason = f"REAR_STOP({self.rear_dist_cm:.0f}cm)"
            self.set_eilik_emotion('surprised'); self._track_stop_time(cmd)
            self._send_command(cmd, reason, now); return

        if 0 < self.front_dist_mm < 500:
            if self.rear_dist_cm <= STOP_THRESHOLD and self.rear_dist_cm > 0:
                cmd = 'S'; reason = f"TRAPPED"
                self.set_eilik_emotion('surprised')
            elif self.rear_dist_cm >= BACKUP_THRESHOLD:
                cmd = 'B'; reason = f"BACKING_UP"
                self.set_eilik_emotion('surprised')
            else:
                cmd = 'S'; reason = f"HOLDING"
                self.set_eilik_emotion('surprised')
            self._track_stop_time(cmd); self._send_command(cmd, reason, now); return

        # Manual
        if self.state == "MANUAL":
            elapsed = (now - self.last_manual_time).nanoseconds / 1e9
            if elapsed < self.MANUAL_RETURN_TIMEOUT:
                cmd = self.manual_command; reason = f"MANUAL({cmd})"
            else:
                self.state = "ROAMING"; self.face_lost_count = 0
                self.set_eilik_emotion('neutral'); cmd = 'F'; reason = "ROAMING"
            self._track_stop_time(cmd); self._send_command(cmd, reason, now); return

        # Autonomous
        elapsed_since_face = (now - self.last_face_time).nanoseconds / 1e9
        if elapsed_since_face > 0.15: self.face_lost_count += 1
        else: self.face_lost_count = 0

        if self.state == "TRACKING":
            if self.face_lost_count >= self.FACE_LOST_THRESHOLD:
                self.state = "SEARCHING"; self.search_start_time = now
                self.search_direction = 'R' if self.last_face_x < 320 else 'L'
                self.set_eilik_emotion('confused')
            else:
                cmd = 'S'; reason = f"TRACKING(x={self.last_face_x:.0f})"
                if self.love_start_time is not None:
                    love_elapsed = (now - self.love_start_time).nanoseconds / 1e9
                    self.set_eilik_emotion('love' if love_elapsed < self.LOVE_DURATION else 'smile')
                else: self.set_eilik_emotion('smile')

        elif self.state == "SEARCHING":
            if self.face_lost_count == 0:
                self.state = "TRACKING"; self.set_eilik_emotion('smile')
            elif elapsed_search >= 5.0:
                self.state = "ROAMING"; self.face_lost_count = 0; self.set_eilik_emotion('neutral')
            else:
                cmd = self.search_direction; reason = f"SEARCHING"
                self.set_eilik_emotion('sad' if elapsed_search >= self.SAD_SEARCH_THRESHOLD else 'confused')

        elif self.state == "ROAMING":
            if self.face_lost_count == 0 and elapsed_since_face < 0.1:
                self.state = "TRACKING"; self.love_start_time = now; self.set_eilik_emotion('love')
            else:
                cmd = 'F'; reason = "ROAMING"
                self.set_eilik_emotion('sleepy' if self._is_sleepy() else 'neutral')

        self._track_stop_time(cmd); self._send_command(cmd, reason, now)

    def _send_command(self, cmd, reason, now):
        self._publish_state()
        with self.serial_lock:
            try:
                self.ser.write(f'{cmd}\n'.encode()); self.ser.flush()
            except Exception as e: self.get_logger().error(f"Write failed: {e}")
        if int(now.nanoseconds / 1e9) % 1 == 0:
            self.get_logger().info(f"CMD:{cmd} | {reason} | Front:{self.front_dist_mm}mm | Rear:{self.rear_dist_cm:.1f}cm | State:{self.state} | 🎭{self.last_emotion}")

def main(args=None):
    rclpy.init(args=args)
    node = FusionController()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        try:
            msg = String(); msg.data = 'sleepy'; node.eilik_pub.publish(msg)
        except: pass
        if node.ser and node.ser.is_open:
            try: node.ser.close()
            except: pass
        node.destroy_node()
        try: rclpy.shutdown()
        except rclpy._rclpy_pybind11.RCLError: pass

if __name__ == '__main__':
    main()
