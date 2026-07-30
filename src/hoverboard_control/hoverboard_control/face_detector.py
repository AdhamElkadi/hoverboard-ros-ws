import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped
from cv_bridge import CvBridge
import mediapipe as mp
import numpy as np
import cv2 
import warnings

# Suppress MediaPipe Protobuf warning
warnings.filterwarnings("ignore", message=".*SymbolDatabase.GetPrototype.*")

class FaceDetector(Node):
    def __init__(self):
        super().__init__('face_detector')
        self.min_confidence = 0.5
        self.min_face_size_ratio = 0.06
        self.max_pixel_jump = 150
        self.smoothing_factor = 0.50
        self.last_x = None
        self.last_y = None
        self.consecutive_valid = 0
        self.required_valid_frames = 2
        
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=self.min_confidence,
            min_tracking_confidence=0.5
        )
        
        self.bridge = CvBridge()
        self.pub = self.create_publisher(PointStamped, '/face/center', 10)
        self.sub = self.create_subscription(Image, '/image_raw', self.image_callback, 10)
        self.get_logger().info('Mask-Robust Face Detector Ready')

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            h, w = cv_image.shape[:2]
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            results = self.mp_face_mesh.process(rgb_image)
            
            if not results.multi_face_landmarks:
                self._handle_no_face()
                return
            
            landmarks = results.multi_face_landmarks[0]
            upper_indices = [10, 338, 299, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
            unique_indices = list(set([i for i in upper_indices if i < len(landmarks.landmark)]))
            
            if not unique_indices:
                self._handle_no_face()
                return

            xs = [landmarks.landmark[i].x for i in unique_indices]
            ys = [landmarks.landmark[i].y for i in unique_indices]
            cx = int(np.mean(xs) * w)
            cy = int(np.mean(ys) * h)
            
            if len(landmarks.landmark) > 263:
                eye_l = landmarks.landmark[33]
                eye_r = landmarks.landmark[263]
                eye_dist = abs(eye_r.x - eye_l.x) * w
            else:
                eye_dist = w * 0.1
            
            if eye_dist < w * self.min_face_size_ratio:
                self._handle_no_face()
                return
            
            if self.last_x is not None:
                dx = abs(cx - self.last_x)
                dy = abs(cy - self.last_y)
                if dx > self.max_pixel_jump or dy > self.max_pixel_jump:
                    self._handle_no_face()
                    return
            
            self.consecutive_valid += 1
            if self.consecutive_valid < self.required_valid_frames:
                return 
            
            if self.last_x is not None:
                smooth_cx = int(self.last_x * (1 - self.smoothing_factor) + cx * self.smoothing_factor)
                smooth_cy = int(self.last_y * (1 - self.smoothing_factor) + cy * self.smoothing_factor)
            else:
                smooth_cx, smooth_cy = cx, cy
            
            self.last_x = smooth_cx
            self.last_y = smooth_cy
            
            point_msg = PointStamped()
            point_msg.header.stamp = self.get_clock().now().to_msg()
            point_msg.header.frame_id = 'camera_link'
            point_msg.point.x = float(smooth_cx)
            point_msg.point.y = float(smooth_cy)
            point_msg.point.z = 0.0
            self.pub.publish(point_msg)
            
        except Exception as e:
            self.get_logger().error(f'Detection error: {e}')
            self._handle_no_face()

    def _handle_no_face(self):
        self.consecutive_valid = 0
        self.last_x = None
        self.last_y = None

def main(args=None):
    rclpy.init(args=args)
    node = FaceDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # ✅ Clean Shutdown Fix
        try:
            node.destroy_node()
            rclpy.shutdown()
        except rclpy._rclpy_pybind11.RCLError:
            pass

if __name__ == '__main__':
    main()
