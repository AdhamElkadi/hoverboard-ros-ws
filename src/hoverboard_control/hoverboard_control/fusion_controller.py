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
        
        # Subscriptions
        self.face_sub = self.create_subscription(PointStamped, '/face/center', self.face_callback, 10)
        self.bridge = CvBridge()
        self.depth_sub = self.create_subscription(Image, '/depth/image_raw', self.depth_callback, 10)
        
        # Publisher for ultrasonic data
        self.pub_rear = self.create_publisher(Float32, '/sensor/ultrasonic/rear', 10)
        
        # ── Eilik Emotion Publisher ──
        self.eilik_pub = self.create_publisher(String, '/eilik/command', 10)
        self.last_emotion = ''
        self.first_lock_after_roam = True  # For "excited" on first face lock
        
        # Reactive Sensor State
        self.front_dist_mm = 0
        self.rear_dist_cm = 100.0
        
        # Stable State Machine
        self.state = "ROAMING"          
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

        # Synchronized timers
        self.control_timer = self.create_timer(0.1, self.control_loop)       
        self.sensor_timer = self.create_timer(0.08, self.read_sensor_data)   

        # ── Initial Eilik Emotion ──
        self.set_eilik_emotion('neutral')
        self.get_logger().info("🎭 Eilik emotion system ready")

    # ═══════════════════════════════════════════════════════════
    # EILIK EMOTION CONTROL (only publishes on change)
    # ═══════════════════════════════════════════════════════════

    def set_eilik_emotion(self, emotion: str):
        """Publish emotion to Eilik app only when it changes."""
        if emotion == self.last_emotion:
            return
        self.last_emotion = emotion
        msg = String()
        msg.data = emotion
        self.eilik_pub.publish(msg)
        self.get_logger().info(f"🎭 Eilik → {emotion}")

    # ═══════════════════════════════════════════════════════════
    # CALLBACKS (unchanged)
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
        """Non-blocking line accumulator that preserves all non-U: bytes"""
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
                                msg = Float32()
                                msg.data = dist
                                self.pub_rear.publish(msg)
                            except ValueError:
                                pass
                    elif ch == '\r':
                        continue
                    else:
                        self._serial_line_buf += ch
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # CONTROL LOOP (your exact logic + Eilik emotions)
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

        # SAFETY OVERRIDES (Always evaluated first)
        if self.rear_dist_cm <= STOP_THRESHOLD and self.rear_dist_cm > 0:
            cmd = 'S'
            reason = f"REAR_STOP({self.rear_dist_cm:.0f}cm)"
            self.set_eilik_emotion('surprised')  # 🎭
            self._send_command(cmd, reason, now)
            return  

        if 0 < self.front_dist_mm < 500:
            if self.rear_dist_cm <= STOP_THRESHOLD and self.rear_dist_cm > 0:
                cmd = 'S'
                reason = f"TRAPPED(F:{self.front_dist_mm}mm|R:{self.rear_dist_cm:.0f}cm)"
                self.set_eilik_emotion('danger')  # 🎭
            elif self.rear_dist_cm >= BACKUP_THRESHOLD:
                cmd = 'B'
                reason = f"BACKING_UP(Rear:{self.rear_dist_cm:.0f}cm>={BACKUP_THRESHOLD:.0f}cm)"
                self.set_eilik_emotion('surprised')  # 🎭
            else:
                cmd = 'S'
                reason = f"HOLDING(Rear:{self.rear_dist_cm:.0f}cm in buffer zone)"
                self.set_eilik_emotion('surprised')  # 🎭
            self._send_command(cmd, reason, now)
            return  

        # STABLE NAVIGATION STATE MACHINE
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
                self.set_eilik_emotion('confused')  # 🎭
                self.get_logger().info(f"🔍 Face lost → SEARCHING {self.search_direction} (last_x={self.last_face_x:.0f})")
            else:
                cmd = 'S'
                reason = f"TRACKING(x={self.last_face_x:.0f}|lost={self.face_lost_count}/{self.FACE_LOST_THRESHOLD})"
                self.set_eilik_emotion('happy')  # 🎭

        elif self.state == "SEARCHING":
            # ✅ IMMEDIATE STOP & TRACK IF FACE REAPPEARS DURING SEARCH
            if self.face_lost_count == 0:
                self.state = "TRACKING"
                self.set_eilik_emotion('happy')  # 🎭
                self.get_logger().info(f"✅ Face found during search → TRACKING (x={self.last_face_x:.0f})")
            elif elapsed_search >= 5.0:
                # Search complete without finding face → Return to roaming
                self.state = "ROAMING"
                self.face_lost_count = 0
                self.first_lock_after_roam = True  # 🎭 Reset for next "excited"
                self.set_eilik_emotion('neutral')  # 🎭
                self.get_logger().info("⏱️ 5s search complete → ROAMING")
            else:
                # Continue searching in set direction
                cmd = self.search_direction
                reason = f"SEARCHING({self.search_direction}|{elapsed_search:.1f}s/5.0s)"
                self.set_eilik_emotion('confused')  # 🎭

        elif self.state == "ROAMING":
            if self.face_lost_count == 0 and elapsed_since_face < 0.1:
                self.state = "TRACKING"
                # 🎭 Excited on FIRST face lock after roaming!
                if self.first_lock_after_roam:
                    self.set_eilik_emotion('excited')
                    self.first_lock_after_roam = False
                else:
                    self.set_eilik_emotion('happy')
                self.get_logger().info(f"✅ Face confirmed → TRACKING (x={self.last_face_x:.0f})")
            else:
                cmd = 'F'
                reason = "ROAMING"
                self.set_eilik_emotion('neutral')  # 🎭

        self._send_command(cmd, reason, now)

    def _send_command(self, cmd, reason, now):
        """Centralized command sending with debug logging"""
        with self.serial_lock:
            try:
                self.ser.write(f'{cmd}\n'.encode())
                self.ser.flush()
            except Exception as e:
                self.get_logger().error(f"Write failed: {e}")

        if int(now.nanoseconds / 1e9) % 1 == 0:
            self.get_logger().info(
                f"CMD:{cmd} | {reason} | Front:{self.front_dist_mm}mm | Rear:{self.rear_dist_cm:.1f}cm | State:{self.state}"
            )

def main(args=None):
    rclpy.init(args=args)
    node = FusionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 🎭 Show sleepy face on shutdown
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

if __name__ == '__main__':
    main()
