import os
from glob import glob
from setuptools import setup

package_name = 'hoverboard_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Include all launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        # Include all Eilik app files
        (os.path.join('share', package_name, 'eilik_app'), [
            'eilik_app/index.html',
            'eilik_app/style.css',
            'eilik_app/main.js',
            'eilik_app/renderer.js',
            'eilik_app/package.json',
            'eilik_app/roboeyes-dom.js',
            'eilik_app/script.js',
            'eilik_app/eilik-morph.js',
            'eilik_app/eilik-animations.js',
            'eilik_app/eilik-kiss.js',
            'eilik_app/eilik-love.js',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='adham',
    maintainer_email='adham@example.com',
    description='Hoverboard face tracking and Eilik expression control',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'face_detector = hoverboard_control.face_detector:main',
            'face_search_controller = hoverboard_control.face_search_controller:main',
             'azure_kinect_publisher = hoverboard_control.azure_kinect_publisher:main',
             'depth_esp_controller = hoverboard_control.depth_esp_controller:main',
             'face_stop_controller = hoverboard_control.face_stop_controller:main',
             'hybrid_controller = hoverboard_control.hybrid_controller:main',
            ],
    },
)
