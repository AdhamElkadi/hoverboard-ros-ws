import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import serial
import time
import numpy as np

class AdvancedHybridController(Node):
    def __init__(self):
        super().__init__('advanced_hybrid_controller')
        
        # Subscriptions
        self.face_sub = self.create_subscription(
            PointStamped, '/face/center', self.face_callback, 10
        )
        self.bridge = CvBridge()
        self.depth_sub = self.create_subscription(
            Image, '/depth/image_raw', self.depth_callback, 10
        )
        
        # State Variables
        self.state = 'ROAMING' # ROAMING, WAITING, SEARCHING
        self.last_face_time = self.get_clock().now()
        self.current_distance_mm = 0
        self.safe_distance_mm = 500
        
        # Tracking Memory
        self.last_face_x = 320.0 # Center of 640px width
        self.search_direction = 'R' 
        self.search_start_time = self.get_clock().now()
        self.last_sent_cmd = 'S' 
        
        # Serial Setup
        try:
            self.ser = None
            for port in ['/dev/ttyUSB0', '/dev/ttyACM0']:
                try:
                    self.ser = serial.Serial(port, 115200, timeout=0.1)
                    time.sleep(1)
                    self.get_logger().info(f"✅ Connected to ESP via {port}")
                    break
                except:
                    continue
            if not self.ser:
                self.get_logger().error("❌ Could not connect to ESP")
        except Exception as e:
            self.get_logger().error(f"Serial Error: {e}")

        self.timer = self.create_timer(0.1, self.control_loop)

    def face_callback(self, msg):
        """Update tracking data when face is seen"""
        self.last_face_time = self.get_clock().now()
        self.last_face_x = msg.point.x
        self.state = 'WAITING' # ✅ Face found! Stop searching immediately.

    def depth_callback(self, msg):
        """Extract center pixel distance"""
        try:
            depth_array = self.bridge.imgmsg_to_cv2(msg, 'mono16')
            h, w = depth_array.shape
            center_region = depth_array[h//2-5:h//2+5, w//2-5:w//2+5]
            valid_pixels = center_region[center_region > 0]
            self.current_distance_mm = int(np.median(valid_pixels)) if len(valid_pixels) > 0 else 0
        except Exception:
            self.current_distance_mm = 0

    def control_loop(self):
        if not self.ser:
            return

        now = self.get_clock().now()
        elapsed_since_face = (now - self.last_face_time).nanoseconds / 1e9
        elapsed_searching = (now - self.search_start_time).nanoseconds / 1e9
        
        cmd = 'S' # Default to Stop
        log_msg = None

        # --- STATE MACHINE ---

        # 1. OBSTACLE AVOIDANCE (Highest Priority)
        if 0 < self.current_distance_mm < self.safe_distance_mm:
            cmd = 'B'
            # Only log every 1 second to avoid spam, but SEND every 100ms
            if int(now.nanoseconds / 1e9 * 10) % 10 == 0:
                log_msg = f"🛑 OBSTACLE ({self.current_distance_mm}mm) → Backing Up"
        
        # 2. FACE DETECTED -> STOP AND WAIT
        elif self.state == 'WAITING':
            if elapsed_since_face > 1.0: 
                self.state = 'SEARCHING'
                self.search_start_time = now 
                
                if self.last_face_x < 320:
                    self.search_direction = 'R'
                else:
                    self.search_direction = 'L'
                log_msg = f"🔍 Face lost → Starting 5s Search {self.search_direction}"
            else:
                cmd = 'S' 

        # 3. SEARCHING -> CONSTANT TURN FOR 5 SECONDS
        elif self.state == 'SEARCHING':
            if elapsed_searching >= 5.0:
                self.state = 'ROAMING'
                log_msg = "⏱️ Search timeout → Resuming Forward Roam"
                cmd = 'F'
            else:
                cmd = self.search_direction 
                # Only log every 1 second
                if int(elapsed_searching * 10) % 10 == 0:
                    log_msg = f"🔄 Searching ({elapsed_searching:.1f}s/5.0s) → {cmd}"

        # 4. ROAMING -> MOVE FORWARD
        else:
            cmd = 'F'

        # ✅ LOGGING (Throttled)
        if log_msg:
            self.get_logger().info(log_msg)

        # ✅ UNIVERSAL HEARTBEAT LOGIC
        # We MUST send if we are NOT waiting. 
        # Waiting is the only state where silence is acceptable.
        # This ensures B, F, L, R are sent every 100ms to keep ESP alive.
        if self.state != 'WAITING' or cmd != self.last_sent_cmd:
            try:
                self.ser.write(f'{cmd}\n'.encode())
                self.ser.flush()
                self.last_sent_cmd = cmd 
            except Exception as e:
                self.get_logger().error(f"Write failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = AdvancedHybridController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.ser and node.ser.is_open:
            node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
