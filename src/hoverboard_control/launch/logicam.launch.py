from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Logitech BRIO 4K Optimized Publisher (Jazzy Type-Safe)
        Node(
            package='usb_cam',
            executable='usb_cam_node_exe',
            name='brio_4k',
            parameters=[{
                'video_device': '/dev/video2',
                'image_width': 640,             # ✅ 720p Width
                'image_height': 480,             # ✅ 720p Height
                'framerate': 30.0,               # ✅ MUST BE FLOAT
                'pixel_format': 'yuyv',          # Uncompressed YUV (zero-latency)
                'io_method': 'mmap',             # Zero-copy memory mapping
                'autoexposure': True,            # ✅ MUST BE BOOLEAN (not 1)
                'brightness': 128,
                'contrast': 128,
                'saturation': 128,
                'white_balance_temperature_auto': True,  # ✅ Boolean for auto WB
                'focus_auto': True                       # ✅ Boolean for auto focus
            }],
            remappings=[('/image_raw', '/image_raw')],
            output='screen'                  # ✅ Show camera errors in terminal
        ),
        # Shared Face Detector
        Node(
            package='hoverboard_control',
            executable='face_detector',
            name='face_detector',
            output='screen'
        ),
        # Shared Search Controller
        Node(
            package='hoverboard_control',
            executable='face_search_controller',
            name='face_search_controller',
            output='screen'
        )
    ])
