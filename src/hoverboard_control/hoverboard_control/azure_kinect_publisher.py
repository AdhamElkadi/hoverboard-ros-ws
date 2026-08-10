import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import pyk4a
from pyk4a import Config, PyK4A
import threading
import time

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
        self.depth_pub = self.create_publisher(Image, '/depth/image_raw', DEPTH_QOS)

        # ✅ DEPTH-OPTIMIZED CONFIG
        self.config = Config(
            color_resolution=pyk4a.ColorResolution.RES_720P,
            depth_mode=pyk4a.DepthMode.NFOV_UNBINNED,
            camera_fps=pyk4a.FPS.FPS_15,
            synchronized_images_only=False,
            wired_sync_mode=pyk4a.WiredSyncMode.STANDALONE,
        )

        self.k4a = None
        self.running = False

        # Start stream in a daemon thread so it dies with the main process
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

        self.get_logger().info('Azure Kinect Depth-Only Publisher Started')

    def _stream_loop(self):
        try:
            self.k4a = PyK4A(self.config)
            self.k4a.start()
            self.running = True

            while self.running and rclpy.ok():
                capture = self.k4a.get_capture()

                if self.depth_pub.get_subscription_count() > 0 and capture.depth is not None:
                    depth_msg = self.bridge.cv2_to_imgmsg(capture.depth, 'mono16')
                    depth_msg.header.stamp = self.get_clock().now().to_msg()
                    depth_msg.header.frame_id = 'kinect_depth_link'
                    self.depth_pub.publish(depth_msg)

        except Exception as e:
            # Only log if we are actually running (ignore errors during shutdown)
            if self.running:
                self.get_logger().error(f'Stream error: {e}')
        finally:
            if self.k4a:
                try:
                    self.k4a.stop()
                except:
                    pass

    def destroy_node(self):
        self.running = False
        # Give the thread a moment to stop
        if self.stream_thread.is_alive():
            self.stream_thread.join(timeout=1.0)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = AzureKinectPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # Catch initialization errors silently if they happen during shutdown
        if "KeyboardInterrupt" not in str(e):
            print(f"Error: {e}")
    finally:
        if node:
            try:
                node.destroy_node()
            except:
                pass
        # ✅ TWEAK: Clean shutdown to suppress RCLError messages
        try:
            rclpy.shutdown()
        except rclpy._rclpy_pybind11.RCLError:
            pass

if __name__ == '__main__':
    main()
