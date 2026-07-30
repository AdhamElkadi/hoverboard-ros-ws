import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import requests # For HTTP
# OR import websockets # For WebSockets

class EilikAppBridge(Node):
    def __init__(self):
        super().__init__('eilik_app_bridge')
        self.sub = self.create_subscription(
            String, 
            '/eilik/command', 
            self.command_callback, 
            10
        )
        # Replace with the actual port/address your Eilik app uses
        self.app_url = "http://localhost:3000/api/expression" 

    def command_callback(self, msg):
        emotion = msg.data.lower()
        self.get_logger().info(f'Sending emotion to Eilik App: {emotion}')
        
        # Example: Sending an HTTP POST request to the app
        try:
            payload = {"expression": emotion}
            requests.post(self.app_url, json=payload)
        except Exception as e:
            self.get_logger().error(f'Failed to connect to Eilik App: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = EilikAppBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
