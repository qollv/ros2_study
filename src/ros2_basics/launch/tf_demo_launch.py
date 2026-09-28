# -*- coding: utf-8 -*-
"""
==============================================================================
TF 演示 Launch —— 一条命令拉起一棵完整的 TF 树
==============================================================================

拉起三个节点，组成这棵树：

    odom --(动态 20Hz)--> base_link --(静态)--> laser

    odom_tf_broadcaster     模拟里程计，让 base_link 绕圆周运动
    static_tf_broadcaster   雷达安装位姿 base_link -> laser
    tf_listener_demo        每秒查询 odom -> laser 并打印

【怎么运行】

    ros2 launch ros2_basics tf_demo_launch.py
    ros2 launch ros2_basics tf_demo_launch.py radius:=0.5 speed:=1.0

    # 另开终端观察：
    ros2 run tf2_tools view_frames      # 生成 frames.pdf（整棵树的图）
    ros2 run tf2_ros tf2_echo odom laser
    ros2 topic echo /tf --once          # 看原始 TF 消息长什么样
    ros2 topic echo /tf_static --once   # 静态变换只在这里，且只发一次
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 圆周运动参数，可在命令行覆盖
    radius_arg = DeclareLaunchArgument('radius', default_value='1.0')
    speed_arg = DeclareLaunchArgument('speed', default_value='0.5')

    # 模拟里程计：动态边 odom -> base_link
    odom_tf = Node(
        package='ros2_basics',
        executable='odom_tf_broadcaster',
        name='odom_tf_broadcaster',
        output='screen',
        parameters=[{
            'radius': LaunchConfiguration('radius'),
            'speed': LaunchConfiguration('speed'),
        }],
    )

    # 雷达安装位姿：静态边 base_link -> laser
    # 参数含义见 static_tf_broadcaster.py，这里演示 launch 传参：
    # 雷达在车体前 0.2m、高 0.15m、朝前。
    static_tf = Node(
        package='ros2_basics',
        executable='static_tf_broadcaster',
        name='static_tf_broadcaster',
        output='screen',
        parameters=[{
            'x': 0.20,
            'y': 0.0,
            'z': 0.15,
            'yaw': 0.0,
        }],
    )

    # 查询端
    listener = Node(
        package='ros2_basics',
        executable='tf_listener_demo',
        name='tf_listener_demo',
        output='screen',
    )

    return LaunchDescription([radius_arg, speed_arg, odom_tf, static_tf, listener])
