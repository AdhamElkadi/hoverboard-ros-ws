import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
import serial
import time


class FaceSearchController(Node):
    def __init__(self):
        super().__init__('face_search_controller')

        self.sub = self.create_subscription(
            PointStamped, '/face/center', self.face_callback, 1
        )

        # Camera parameters
        self.img_width = 640
        self.center_x = self.img_width / 2.0

        # Search state
        self.last_face_x = self.center_x
        self.last_face_time = self.get_clock().now()
        self.search_timeout_sec = 5.0
        
        # ✅ FIXED: Separate flags prevent rapid-fire start/stop cycles
        self.is_searching = False          # Currently sending motor commands
        self.search_timed_out = False      # True after timeout fires ONCE
        
        try:
            self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)
            time.sleep(1)
            self.get_logger().info("Face Search Controller Ready (ASCII L/R/S Protocol)")
        except Exception as e:
            self.get_logger().error(f"Serial failed: {e}")
            self.ser = None

        self.timer = self.create_timer(0.033, self.control_loop)

    def face_callback(self, msg):
        """Update memory when face is visible"""
        self.last_face_x = msg.point.x
        self.last_face_time = self.get_clock().now()
        
        # ✅ RESET ALL SEARCH STATE WHEN FACE IS FOUND
        if self.is_searching or self.search_timed_out:
            self.is_searching = False
            self.search_timed_out = False
            self.get_logger().info("✅ FACE RE-DETECTED → Sending S (STOP)")
            self._send_char('S')

    def control_loop(self):
        """Continuously send L/R/S commands while searching"""
        if not self.ser or not self.ser.is_open:
            return

        now = self.get_clock().now()
        elapsed = (now - self.last_face_time).nanoseconds / 1e9

        # START SEARCH: Only if face lost >1.5s AND not already timed out
        if elapsed > 1.5 and not self.is_searching and not self.search_timed_out:
            self.is_searching = True
            last_error = self.last_face_x - self.center_x

            if last_error < 0:
                self.current_steer_cmd = 'R'

                direction = "RIGHT"
            else:
                self.current_steer_cmd = 'L'
                direction = "LEFT"

            self.get_logger().info(
                f"🔍 CONTINUOUS SEARCH STARTED: Last {direction} → Sending {self.current_steer_cmd}"
            )

        # TIMEOUT CHECK: Fires ONLY ONCE thanks to search_timed_out flag
        if self.is_searching and elapsed >= self.search_timeout_sec:
            self.is_searching = False
            self.search_timed_out = True  # Prevents re-triggering until face found
            self.current_steer_cmd = 'S'
            self.get_logger().warn(
                f"⏹️  SEARCH TIMEOUT ({self.search_timeout_sec}s) → Sending S (STOP)"
            )
            self._send_char('S')
            return

        # CONTINUOUSLY SEND ACTIVE COMMAND AT 30HZ
        if self.is_searching:
            self._send_char(self.current_steer_cmd)

    def _send_char(self, char):
        """Send single ASCII character command matching ESP32 readLaptopCommand()"""
        try:
            cmd = f'{char}\n'.encode()
            self.ser.write(cmd)
            self.ser.flush()
        except serial.SerialException as e:
            self.get_logger().error(f"Serial write failed: {e}")
            self.ser.close()
            self.ser = None
        except Exception as e:
            self.get_logger().warn(f"Write error: {e}", throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = FaceSearchController()
    try:
        rclpy.spin(node)  # ✅ FIXED: was rplpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.ser and node.ser.is_open:
            node.ser.close()
            node.get_logger().info("Serial port closed")
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

