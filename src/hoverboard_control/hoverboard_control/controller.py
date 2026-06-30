import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from std_msgs.msg import String

class HoverboardController(Node):
    def __init__(self):
        super().__init__('hoverboard_brain')
        
        # Subscribers for ultrasonic sensors
        self.sub_left = self.create_subscription(
            Range, '/ultrasonic/left', self.left_cb, 10)
        self.sub_middle = self.create_subscription(
            Range, '/ultrasonic/middle', self.middle_cb, 10)
        self.sub_right = self.create_subscription(
            Range, '/ultrasonic/right', self.right_cb, 10)
        
        # Publisher for motor commands
        self.cmd_pub = self.create_publisher(String, '/motor_commands', 10)
        
        # Initialize distances to 10.0m (No Object Detected)
        self.left_dist = 10.0
        self.middle_dist = 10.0
        self.right_dist = 10.0
        
        # Run decision logic at 10Hz
        self.timer = self.create_timer(0.1, self.decide_movement)
        self.get_logger().info("Hoverboard Controller Started")

    def left_cb(self, msg):
        self.left_dist = msg.range

    def middle_cb(self, msg):
        self.middle_dist = msg.range

    def right_cb(self, msg):
        self.right_dist = msg.range

    def decide_movement(self):
        cmd_msg = String()
        
        # Thresholds
        emergency_limit = 0.1  # 10cm
        obstacle_limit = 0.3   # 30cm
        
        # Determine if sensors are actually seeing an object
        # We ignore values >= 3.5m or <= 0.01m (which includes our 10.0m default)
        l_seen = (0.01 < self.left_dist < 3.5)
        m_seen = (0.01 < self.middle_dist < 3.5)
        r_seen = (0.01 < self.right_dist < 3.5)

        # --- DECISION LOGIC ---
        
        # 1. Emergency Stop: Any sensor sees something very close
        if (l_seen and self.left_dist < emergency_limit) or \
           (m_seen and self.middle_dist < emergency_limit) or \
           (r_seen and self.right_dist < emergency_limit):
            cmd_msg.data = "EMERGENCY_STOP"
            
        # 2. Middle Obstacle: Turn toward the more open side
        elif m_seen and self.middle_dist < obstacle_limit:
            if self.left_dist > self.right_dist:
                cmd_msg.data = "GO_LEFT"
            else:
                cmd_msg.data = "GO_RIGHT"
                
        # 3. Left + Middle Blocked: Only Right is open
        elif l_seen and self.left_dist < obstacle_limit and \
             m_seen and self.middle_dist < obstacle_limit:
            cmd_msg.data = "GO_RIGHT"
            
        # 4. Right + Middle Blocked: Only Left is open
        elif r_seen and self.right_dist < obstacle_limit and \
             m_seen and self.middle_dist < obstacle_limit:
            cmd_msg.data = "GO_LEFT"
            
        # 5. All Three Blocked: Dead end
        elif l_seen and self.left_dist < obstacle_limit and \
             m_seen and self.middle_dist < obstacle_limit and \
             r_seen and self.right_dist < obstacle_limit:
            cmd_msg.data = "MOVE_BACKWARDS"
            
        # 6. Default: Path is clear
        else:
            cmd_msg.data = "FORWARD"

        # Publish command to ESP32
        self.cmd_pub.publish(cmd_msg)
        
        # --- TERMINAL DASHBOARD ---
        # Prints a single updating line instead of scrolling logs
        print(f"\r L:{self.left_dist:.2f}m | M:{self.middle_dist:.2f}m | R:{self.right_dist:.2f}m  =>  CMD: {cmd_msg.data:<15}", 
              end='', flush=True)

def main(args=None):
    rclpy.init(args=args)
    controller = HoverboardController()
    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        pass
    controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
