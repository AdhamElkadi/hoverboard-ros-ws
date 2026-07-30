import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction

def generate_launch_description():
    # Define the hotspot name here (Change 'MyRobotHotspot' to your actual connection name)
    HOTSPOT_NAME = 'MyRobotHotspot' 
    
    # Path to the Eilik Electron app
    EILIK_APP_DIR = os.path.expanduser('~/ros2_ws/src/hoverboard_control/eilik_app')

    return LaunchDescription([
        # 1. Enable the Hotspot immediately
        ExecuteProcess(
            cmd=['nmcli', 'connection', 'up', HOTSPOT_NAME],
            output='screen',
            name='enable_hotspot'
        ),

        # 2. Wait 5 seconds for the Hotspot to initialize and assign an IP
        TimerAction(
            period=5.0,
            actions=[
                # 3. Webcam (Color for Face Tracking)
                Node(
                    package='usb_cam',
                    executable='usb_cam_node_exe',
                    name='usb_cam',
                    parameters=[{
                        'video_device': '/dev/video2',
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
                
                # 4. Face Detector (Perception)
                Node(
                    package='hoverboard_control',
                    executable='face_detector',
                    name='face_detector',
                    output='screen'
                ),

                # 5. Fusion Controller (The Brain)
                Node(
                    package='hoverboard_control',
                    executable='fusion_controller',
                    name='fusion_controller',
                    output='screen'
                ),

                # 6. Web Controller (For Phone App)
                Node(
                    package='hoverboard_control',
                    executable='web_controller',
                    name='web_controller',
                    output='screen'
                ),

                # 7. ✅ Eilik Eyes App (Electron) - Starts after ROS nodes are ready
                ExecuteProcess(
                    cmd=['npm', 'start'],
                    cwd=EILIK_APP_DIR,
                    shell=True,
                    output='screen',
                    name='eilik_eyes'
                )
            ]
        )
    ])
