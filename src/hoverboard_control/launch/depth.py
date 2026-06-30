from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='hoverboard_control',
            executable='azure_kinect_publisher',
            name='kinect_depth',
            output='screen',
            parameters=[{
                # Optional: You can override config here if needed, 
                # otherwise it uses the defaults in azure_kinect_publisher.py
            }]
        )
    ])
