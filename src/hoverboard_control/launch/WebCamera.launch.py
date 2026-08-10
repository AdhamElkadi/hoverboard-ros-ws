# launch/manual_control.launch.py

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction


def generate_launch_description():
    # ⚠️ CHANGE THIS to match your actual hotspot connection name
    # Find it with: nmcli connection show | grep hotspot
    HOTSPOT_NAME = 'MyRobotHotspot'

    # Path to the Eilik Electron app
    EILIK_APP_DIR = os.path.expanduser('~/ros2_ws/src/hoverboard_control/eilik_app')

    return LaunchDescription([
        # ── 1. Enable Hotspot Immediately ──
        ExecuteProcess(
            cmd=['nmcli', 'connection', 'up', HOTSPOT_NAME],
            output='screen',
            name='enable_hotspot'
        ),

        # ── 2. Wait for Hotspot + Hardware Initialization ──
        TimerAction(
            period=5.0,
            actions=[
                # ── 3. Laptop Webcam (RGB for Face Detection → Eilik Gaze) ──
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

                # ── 5. Face Detector (Provides /face/center for Eilik gaze) ──
                Node(
                    package='hoverboard_control',
                    executable='face_detector',
                    name='face_detector',
                    output='screen'
                ),

                # ── 6. Manual Controller (Base + Head + Safety) ──
                Node(
                    package='hoverboard_control',
                    executable='manual_controller',
                    name='manual_controller',
                    parameters=[{
                        'manual_timeout': 2.0,
                        'front_stop_mm': 500,
                        'rear_stop_cm': 22.0,
                        'rear_backup_cm': 30.0,
                        'head_cmd_interval': 0.02,
                    }],
                    output='screen'
                ),

                # ── 7. Manual Web Controller (Phone App on Port 5000) ──
                Node(
                    package='hoverboard_control',
                    executable='manual_web_controller',
                    name='manual_web_controller',
                    output='screen'
                ),

                # ── 8. Eilik Emotion Display Bridge ──
                Node(
                    package='hoverboard_control',
                    executable='eilik_bridge',
                    name='eilik_bridge',
                    output='screen'
                ),

                # ── 9. Eilik Eyes App (Electron) ──
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
