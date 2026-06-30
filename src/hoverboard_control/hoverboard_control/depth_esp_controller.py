import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import serial
import time
import numpy as np

class DepthESPController(Node):
    def __init__(self):
        super().__init__('depth_esp_controller')
        
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, 
            '/depth/image_raw', 
            self.depth_callback, 
            10
        )
        
        self.safe_distance_mm = 500
        self.last_cmd = ''
        self.current_distance = 0
        
        # ✅ TRY BOTH COMMON PORTS
        ports_to_try = ['/dev/ttyUSB0', '/dev/ttyACM0']
        self.ser = None
        
        for port in ports_to_try:
            try:
                self.ser = serial.Serial(port, 115200, timeout=0.1)
                time.sleep(1) # Wait for ESP reset
                self.get_logger().info(f"✅ Connected to ESP32 via {port}")
                break
            except Exception:
                continue
                
        if not self.ser:
            self.get_logger().error("❌ Could not connect to ESP on USB0 or ACM0. Check dmesg!")

        self.timer = self.create_timer(0.1, self.control_loop)

    def depth_callback(self, msg):
        try:
            depth_array = self.bridge.imgmsg_to_cv2(msg, 'mono16')
            h, w = depth_array.shape
            center_region = depth_array[h//2-5:h//2+5, w//2-5:w//2+5]
            valid_pixels = center_region[center_region > 0]
            
            if len(valid_pixels) > 0:
                self.current_distance = int(np.median(valid_pixels))
            else:
                self.current_distance = 0
        except Exception as e:
            self.get_logger().error(f"Depth error: {e}")

    def control_loop(self):
        if not self.ser:
            return

        cmd = 'S' # Default to Stop
        if self.current_distance > self.safe_distance_mm:
            cmd = 'F' # Forward
        elif 0 < self.current_distance < self.safe_distance_mm:
            cmd = 'B' # Back

        if cmd != self.last_cmd:
            self.get_logger().info(f"Dist: {self.current_distance}mm → CMD: {cmd}")
            try:
                self.ser.write(f'{cmd}\n'.encode())
                self.ser.flush()
                self.last_cmd = cmd
            except Exception as e:
                self.get_logger().error(f"Write failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = DepthESPController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.ser: node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
