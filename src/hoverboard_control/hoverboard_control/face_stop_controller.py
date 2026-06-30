import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
import serial
import time

class FaceStopController(Node):
    def __init__(self):
        super().__init__('face_stop_controller')
        
        self.sub = self.create_subscription(
            PointStamped, 
            '/face/center', 
            self.face_callback, 
            10
        )
        
        self.last_face_time = self.get_clock().now()
        self.timeout_sec = 2.0  # How long to wait after losing face before moving again
        self.last_cmd = ''
        
        try:
            # Try both common ports
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

        # Check logic at 10Hz
        self.timer = self.create_timer(0.1, self.control_loop)

    def face_callback(self, msg):
        """Update timer whenever a face is seen"""
        self.last_face_time = self.get_clock().now()

    def control_loop(self):
        if not self.ser:
            return

        now = self.get_clock().now()
        elapsed = (now - self.last_face_time).nanoseconds / 1e9

        cmd = ''
        if elapsed < self.timeout_sec:
            cmd = 'S' # Stop if face was seen recently
        else:
            cmd = 'F' # Forward if no face seen for a while

        if cmd != self.last_cmd:
            self.get_logger().info(f"Face Status: {'DETECTED' if cmd == 'S' else 'LOST'} → Sending: {cmd}")
            try:
                self.ser.write(f'{cmd}\n'.encode())
                self.ser.flush()
                self.last_cmd = cmd
            except Exception as e:
                self.get_logger().error(f"Write failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = FaceStopController()
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
