"""Launch MAVROS + rosbridge + SAR agent nodes."""
import os
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    fcu_url = os.environ.get('FCU_URL', 'udp://:14550@')
    return LaunchDescription([
        Node(
            package='mavros', executable='mavros_node', name='mavros',
            output='screen',
            parameters=[{'fcu_url': fcu_url, 'gcs_url': '', 'system_id': 255}],
        ),
        Node(
            package='rosbridge_server', executable='rosbridge_websocket',
            name='rosbridge', output='screen',
            parameters=[{'port': 9090}],
        ),
        Node(package='sar_drone', executable='mission_bridge', output='screen'),
        Node(package='sar_drone', executable='llm_agent', output='screen'),
    ])
