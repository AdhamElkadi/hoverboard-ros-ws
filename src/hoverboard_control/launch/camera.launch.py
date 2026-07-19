from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction

def generate_launch_description():
    return LaunchDescription([
        # 1. Webcam (Color for Face Tracking)
        Node(
            package='usb_cam',
            executable='usb_cam_node_exe',
            name='usb_cam',
            parameters=[{
                'video_device': '/dev/video0',
                'image_width': 640,
                'image_height': 480,
                'framerate': 30.0,
                'pixel_format': 'yuyv',
                'io_method': 'mmap',
                'autoexposure': True,
                'focus_auto': True
            }],
            output='screen'
        ),
        
        # 2. Azure Kinect (Depth for Safety) - Delayed to prevent USB lock
        TimerAction(
            period=3.0,
            actions=[
                Node(
                    package='hoverboard_control',
                    executable='azure_kinect_publisher',
                    name='kinect_depth',
                    output='screen'
                )
            ]
        ),
        
        # 3. Face Detector (Perception)
        Node(
            package='hoverboard_control',
            executable='face_detector',
            name='face_detector',
            output='screen'
        ),
        
        # 4. Hybrid Controller (The Brain)
        Node(
            package='hoverboard_control',
            executable='fusion_controller',
            name='fusion_controller',
            output='screen'
        )
    ])
