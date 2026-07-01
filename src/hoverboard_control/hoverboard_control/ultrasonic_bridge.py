import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import serial
import time

class UltrasonicBridge(Node):
    def __init__(self):
        super().__init__('ultrasonic_bridge')
        
        # Publisher for the rear ultrasonic sensor
        self.pub_rear = self.create_publisher(Float32, '/sensor/ultrasonic/rear', 10)
        
        # Serial Setup
        try:
            # Ensure this matches your ESP32 port (check with 'ls /dev/tty*')
            self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)
            time.sleep(1) # Wait for connection to stabilize
            self.get_logger().info("✅ ESP32 Sensor Bridge Connected")
        except Exception as e:
            self.get_logger().error(f"❌ Serial Error: {e}")
            
        # Timer to read serial data at 20Hz (every 0.05 seconds)
        self.timer = self.create_timer(0.05, self.read_loop)

    def read_loop(self):
        if not self.ser: 
            return
            
        try:
            # Check if there is data waiting in the buffer
            if self.ser.in_waiting > 0:
                # Read a full line until newline character
                line = self.ser.readline().decode('utf-8').strip()
                
                # Check if the line starts with our identifier 'U:'
                if line.startswith('U:'):
                    # Extract the number part after 'U:'
                    dist_str = line[2:]
                    
                    # Convert to float and publish
                    dist = float(dist_str)
                    msg = Float32()
                    msg.data = dist
                    self.pub_rear.publish(msg)
                    
        except Exception as e:
            # Ignore occasional parse errors or disconnected sensors
            pass 

def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
