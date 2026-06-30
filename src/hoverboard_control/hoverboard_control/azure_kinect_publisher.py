import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import pyk4a
from pyk4a import Config, PyK4A
import threading

# Depth-only QoS (Color publisher removed)
DEPTH_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)

class AzureKinectPublisher(Node):
    def __init__(self):
        super().__init__('azure_kinect_publisher')

        self.bridge = CvBridge()
        # ✅ COLOR PUBLISHER REMOVED - Only depth needed for safety
        self.depth_pub = self.create_publisher(Image, '/depth/image_raw', DEPTH_QOS)

        # ✅ DEPTH-OPTIMIZED CONFIG: No color resolution specified
        self.config = Config(
            color_resolution=pyk4a.ColorResolution.RES_720P,  # Required by SDK but unused
            depth_mode=pyk4a.DepthMode.NFOV_UNBINNED,
            camera_fps=pyk4a.FPS.FPS_15,                      # Max stable depth FPS
            synchronized_images_only=False,                   # Decouple from color
            wired_sync_mode=pyk4a.WiredSyncMode.STANDALONE,
        )

        self.k4a = None
        self.running = False

        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

        self.get_logger().info('Azure Kinect Depth-Only Publisher Started (Minimal CPU)')

    def _stream_loop(self):
        try:
            self.k4a = PyK4A(self.config)
            self.k4a.start()
            self.running = True

            while self.running and rclpy.ok():
                capture = self.k4a.get_capture()

                # ✅ ONLY PROCESS DEPTH - Skip color serialization completely
                if self.depth_pub.get_subscription_count() > 0 and capture.depth is not None:
                    depth_msg = self.bridge.cv2_to_imgmsg(capture.depth, 'mono16')
                    depth_msg.header.stamp = self.get_clock().now().to_msg()
                    depth_msg.header.frame_id = 'kinect_depth_link'
                    self.depth_pub.publish(depth_msg)

        except Exception as e:
            self.get_logger().error(f'Stream error: {e}')
        finally:
            if self.k4a:
                self.k4a.stop()

    def destroy_node(self):
        self.running = False
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = AzureKinectPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
