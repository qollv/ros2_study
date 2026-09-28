# -*- coding: utf-8 -*-
"""
==============================================================================
Launch 进阶 1：从 yaml 文件加载参数（练习 8）
==============================================================================

【为什么这课重要】

Nav2 的启动方式你一定见过：

    ros2 launch nav2_bringup navigation_launch.py params_file:=my_nav2.yaml

它干的事和本文件一模一样：把一个 yaml 文件里的几十个参数
一次性灌进十几个节点。学完这个，nav2_params.yaml 对你就不再是天书。

【参数优先级（从高到低）】

    1. ros2 param set 运行时修改          （最高）
    2. 命令行 -p tolerance:=0.5
    3. launch 文件里 parameters=[{...}]    （字典直接写死）
    4. launch 文件里 parameters=[yaml 文件] （本例）
    5. 节点代码里 declare_parameter 的默认值 （最低）

后面的来源先生效，前面的能覆盖它。所以 yaml 里写了 tolerance: 0.15，
代码里的默认 0.25 就被盖掉了。

【怎么运行】

    ros2 launch ros2_basics yaml_params_launch.py
    ros2 launch ros2_basics yaml_params_launch.py params_file:=别的.yaml

    # 验证参数确实来自 yaml（另开终端）：
    ros2 param get /param_demo tolerance      # 应该是 0.15，不是代码里的 0.25
    ros2 param get /param_demo robot_name     # 应该是 yaml_loaded_dog
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, ThisLaunchFileDir, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # ----------------------------------------------------------------------
    # yaml 文件路径：默认指向本 launch 文件旁边的 config/demo_params.yaml
    # ----------------------------------------------------------------------
    # ThisLaunchFileDir()    当前 launch 文件所在目录（运行时才解析）
    # PathJoinSubstitution() 把几段拼成一个路径（跨平台处理斜杠）
    #
    # 注意 default_value 里可以用列表拼 Substitution，
    # 这也是 launch 文件"延迟求值"的特点：写的时候只是占位符，跑的时候才算出真路径。
    #
    # 命令行可覆盖：
    #   ros2 launch ros2_basics yaml_params_launch.py params_file:=/abs/path/my.yaml
    params_file = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution(
            [ThisLaunchFileDir(), '..', 'config', 'demo_params.yaml']),
        description='yaml 参数文件路径')

    # 启动时把路径打出来，方便核对
    info = LogInfo(msg=['加载参数文件: ', LaunchConfiguration('params_file')])

    # ----------------------------------------------------------------------
    # 用 yaml 启动 param_demo
    # ----------------------------------------------------------------------
    # parameters 列表的三种玩法（可以混用，后面的覆盖前面的）：
    #   parameters=[{'rate': 2.0}]              字典：直接写死
    #   parameters=['/path/to/a.yaml']          yaml 文件路径
    #   parameters=[{'a': 1}, '/b.yaml']        先加载 b.yaml，再用 a 覆盖
    #
    # yaml 匹配规则见 config/demo_params.yaml 头部注释：
    #   /**: 匹配所有节点，/param_demo: 只匹配该名字的节点
    param_node = Node(
        package='ros2_basics',
        executable='param_demo',
        name='param_demo',          # 名字必须和 yaml 里的键对上（/** 除外）
        output='screen',
        parameters=[LaunchConfiguration('params_file')],
    )

    return LaunchDescription([params_file, info, param_node])
