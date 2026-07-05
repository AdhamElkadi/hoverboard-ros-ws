import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge
import serial
import time
import numpy as np

class FusionController(Node):
    def __init__(self):
        super().__init__('fusion_controller')
        
        self.face_sub = self.create_subscription(PointStamped, '/face/center', self.face_callback, 10)
        self.bridge = CvBridge()
        self.depth_sub = self.create_subscription(Image, '/depth/image_raw', self.depth_callback, 10)
        self.rear_sub = self.create_subscription(Float32, '/sensor/ultrasonic/rear', self.rear_callback, 10)
        
        self.state = 'ROAMING'
        self.last_face_time = self.get_clock().now()
        self.front_dist_mm = 0
        self.rear_dist_cm = 100.0
        
        self.last_face_x = 320.0
        self.search_direction = 'R'
        self.search_start_time = self.get_clock().now()
        self.last_sent_cmd = 'S'
        
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
        except Exception as e:
            self.get_logger().error(f"Serial Error: {e}")

        self.timer = self.create_timer(0.1, self.control_loop)

    def face_callback(self, msg):
        self.last_face_time = self.get_clock().now()
        self.last_face_x = msg.point.x
        self.state = 'WAITING'

    def depth_callback(self, msg):
        try:
            depth_array = self.bridge.imgmsg_to_cv2(msg, 'mono16')
            h, w = depth_array.shape
            center_region = depth_array[h//2-5:h//2+5, w//2-5:w//2+5]
            valid_pixels = center_region[center_region > 0]
            self.front_dist_mm = int(np.median(valid_pixels)) if len(valid_pixels) > 0 else 0
        except:
            self.front_dist_mm = 0

    def rear_callback(self, msg):
        self.rear_dist_cm = msg.data

    def control_loop(self):
        if not self.ser: return

        now = self.get_clock().now()
        elapsed_face = (now - self.last_face_time).nanoseconds / 1e9
        elapsed_search = (now - self.search_start_time).nanoseconds / 1e9
        
        cmd = 'S'
        force_send = False

        # --- LOGIC HIERARCHY ---

        # 1. 🛑 REAR SAFETY (HIGHEST PRIORITY)
        if 0 < self.rear_dist_cm < 30:
            cmd = 'S'
            self.state = 'STOPPED_SAFETY'
            force_send = True # ✅ Force continuous sending
            self.get_logger().warn(f"🛑 REAR OBSTACLE! Dist: {self.rear_dist_cm}cm")

        # 2. FRONT OBSTACLE -> Try to Back Up
        elif 0 < self.front_dist_mm < 500:
            if 0 < self.rear_dist_cm < 30:
                cmd = 'S' 
                force_send = True
                self.get_logger().warn(f"🛑 TRAPPED! Rear: {self.rear_dist_cm}cm")
            else:
                cmd = 'B'
                self.state = 'ROAMING'

        # 3. FACE DETECTED -> Stop and Wait
        elif self.state == 'WAITING':
            if elapsed_face > 1.0:
                self.state = 'SEARCHING'
                self.search_start_time = now
                self.search_direction = 'L' if self.last_face_x < 320 else 'R'
            else:
                cmd = 'S'

        # 4. SEARCHING -> Turn Constantly
        elif self.state == 'SEARCHING':
            if elapsed_search >= 5.0:
                self.state = 'ROAMING'
                cmd = 'F'
            else:
                cmd = self.search_direction

        # 5. ROAMING -> Move Forward
        else:
            cmd = 'F'

        # --- SEND COMMAND ---
        if cmd != self.last_sent_cmd or force_send:
            try:
                self.ser.write(f'{cmd}\n'.encode())
                self.ser.flush()
                self.last_sent_cmd = cmd
            except Exception as e:
                self.get_logger().error(f"Write failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = FusionController()
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
