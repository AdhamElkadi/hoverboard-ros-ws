import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from std_msgs.msg import String
import serial
import time
import sys

class SerialBridge(Node):
    def __init__(self):
        super().__init__('serial_bridge')
        
        # Pre-create message objects to avoid allocation overhead
        self.msg_left = Range()
        self.msg_middle = Range()
        self.msg_right = Range()
        
        # Configure range metadata once
        for msg in [self.msg_left, self.msg_middle, self.msg_right]:
            msg.radiation_type = Range.ULTRASOUND
            msg.field_of_view = 0.1
            msg.min_range = 0.02
            msg.max_range = 4.0
            
        self.pub_left = self.create_publisher(Range, '/ultrasonic/left', 1)
        self.pub_middle = self.create_publisher(Range, '/ultrasonic/middle', 1)
        self.pub_right = self.create_publisher(Range, '/ultrasonic/right', 1)
        self.sub_cmd = self.create_subscription(String, '/motor_commands', self.cmd_cb, 1)
        
        try:
            # CRITICAL: Use timeout=0 for non-blocking reads
            self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0)
            time.sleep(1)
            self.get_logger().info("Serial bridge connected (low-latency mode)")
        except serial.SerialException as e:
            self.get_logger().error(f"Serial failed: {e}")
            sys.exit(1)
            
        # Run at 20Hz for snappier response
        self.timer = self.create_timer(0.05, self.read_sensors)

    def read_sensors(self):
        if self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                
                # Skip empty lines from non-blocking reads
                if not line or len(line.split(',')) != 3:
                    return
                
                l_val, m_val, r_val = line.split(',')
                
                # Validate all parts are numeric before converting
                if not (l_val and m_val and r_val):
                    return
                    
                self.msg_left.range = float(l_val) / 100.0 if float(l_val) < 999 else 4.0
                self.msg_middle.range = float(m_val) / 100.0 if float(m_val) < 999 else 4.0
                self.msg_right.range = float(r_val) / 100.0 if float(r_val) < 999 else 4.0
                
                self.pub_left.publish(self.msg_left)
                self.pub_middle.publish(self.msg_middle)
                self.pub_right.publish(self.msg_right)
                    
            except ValueError as e:
                self.get_logger().warn(f"Invalid data: {e}", throttle_duration_sec=5.0)
            except Exception as e:
                self.get_logger().warn(f"Parse error: {e}", throttle_duration_sec=5.0)

    def cmd_cb(self, msg):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((msg.data + '\n').encode())
            except serial.SerialException:
                pass

def main(args=None):
    rclpy.init(args=args)
    node = SerialBridge()
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
