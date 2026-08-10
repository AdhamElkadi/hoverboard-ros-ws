import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction, Shutdown

def generate_launch_description():
    HOTSPOT_NAME = 'MyRobotHotspot' 
    EILIK_APP_DIR = os.path.expanduser('~/ros2_ws/src/hoverboard_control/eilik_app')

    return LaunchDescription([
        # 1. Enable the Hotspot immediately
        ExecuteProcess(
            cmd=['nmcli', 'connection', 'up', HOTSPOT_NAME],
            output='screen',
            name='enable_hotspot'
        ),

        # 2. Wait 5 seconds for Hotspot + Sensors to initialize
        TimerAction(
            period=5.0,
            actions=[
                # 3. Webcam - ✅ OPTIMIZED: 15 FPS instead of 30
                Node(
                    package='usb_cam',
                    executable='usb_cam_node_exe',
                    name='usb_cam',
                    parameters=[{
                        'video_device': '/dev/video2',
                        'image_width': 640,
                        'image_height': 480,
                        'framerate': 60.0,
                        'pixel_format': 'yuyv',
                        'io_method': 'mmap',
                        'autoexposure': True,
                        'focus_auto': True
                    }],
                    output='screen'
                ),
                
                # 4. Face Detector
                Node(
                    package='hoverboard_control',
                    executable='face_detector',
                    name='face_detector',
                    output='screen'
                ),

                # 5. Fusion Controller
                Node(
                    package='hoverboard_control',
                    executable='fusion_controller',
                    name='fusion_controller',
                    output='screen'
                ),

                # 6. Web Controller
                Node(
                    package='hoverboard_control',
                    executable='web_controller',
                    name='web_controller',
                    output='screen'
                ),

                # 7. Azure Kinect Depth Publisher
                Node(
                    package='hoverboard_control',
                    executable='azure_kinect_publisher',
                    name='kinect_depth',
                    output='screen'
                ),

                # 8. Eilik Eyes App - Master Switch
                ExecuteProcess(
                    cmd=['npm', 'start'],
                    cwd=EILIK_APP_DIR,
                    shell=True,
                    output='screen',
                    name='eilik_eyes',
                    on_exit=Shutdown() 
                )
            ]
        )
    ])
