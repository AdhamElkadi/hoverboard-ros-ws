from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction

def generate_launch_description():
    return LaunchDescription([
        # 1. USB Webcam Publisher (Color Stream)
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
            remappings=[('/image_raw', '/image_raw')],
            output='screen'
        ),
        
        # 2. Face Detector (Perception)
        Node(
            package='hoverboard_control',
            executable='face_detector',
            name='face_detector',
            output='screen'
        ),
    
    ])
