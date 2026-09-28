# -*- coding: utf-8 -*-
"""
==============================================================================
Launch 进阶 2：条件启动 / 命名空间 / 话题重映射 / 事件（练习 8）
==============================================================================

【这四个东西分别在解决什么问题】

    IfCondition      按开关决定某个节点启不启动（仿真/真机二选一）
    GroupAction+命名空间  一套代码跑多个机器人（/robot1/... /robot2/...）
    remappings       节点代码不改，话题名按需改（复用别人的包时必需）
    RegisterEventHandler 监听进程事件（谁启动了/谁退出了），控制启动顺序

【对应导航场景】

你狗上的导航启动脚本 = 下面所有东西的组合：
    - IfCondition 条件加载 Cartographer 建图配置 or 定位配置
      （正是你那两份 car_2d.lua / car_2d_loc.lua 的切换）
    - IncludeLaunchDescription 嵌套官方 nav2_bringup
    - GroupAction+命名空间扩展到多机编队

【怎么运行】

    ros2 launch ros2_basics advanced_launch.py
    ros2 launch ros2_basics advanced_launch.py robot_namespace:=dog2
    ros2 launch ros2_basics advanced_launch.py use_group:=false

    # 观察命名空间效果（另开终端）：
    ros2 node list         # 应看到 /robot1/talker、/robot1/listener
    ros2 topic list        # 应看到 /robot1/status_text（被重映射过）
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    LogInfo,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    # ----------------------------------------------------------------------
    # 1. 开关参数 + 条件启动
    # ----------------------------------------------------------------------
    # 命令行传的是字符串 'true'/'false'，IfCondition 负责把它当布尔用：
    #   ros2 launch ... use_group:=false     -> 整组节点都不启动
    use_group = DeclareLaunchArgument('use_group', default_value='true')
    ns = DeclareLaunchArgument('robot_namespace', default_value='robot1')

    # ----------------------------------------------------------------------
    # 2. GroupAction + PushRosNamespace：批量命名空间
    # ----------------------------------------------------------------------
    # GroupAction 把若干节点打包，统一施加条件、命名空间等属性。
    # PushRosNamespace 让组内所有节点/话题都挂上前缀：
    #   /talker  ->  /robot1/talker
    #   /chatter ->  /robot1/chatter
    #
    # 这就是"同一套代码跑多台机器人"的标准做法：
    # 起两个 GroupAction，命名空间分别 robot1 / robot2 即可，代码零修改。
    #
    # 单个节点也可以直接用 Node(namespace='robot1')，但组内多节点时
    # GroupAction 明显更干净。
    # 先把组内节点定义成独立变量（事件处理器要引用它们，
    # 注意 GroupAction 对象本身没有 .actions 属性可以取）
    talker_node = Node(
        package='ros2_basics',
        executable='talker',
        name='talker',
        output='screen',
        remappings=[('chatter', 'status_text')],
        parameters=[{'rate': 2.0}],
    )
    listener_node = Node(
        package='ros2_basics',
        executable='listener',
        name='listener',
        output='screen',
        remappings=[('chatter', 'status_text')],
    )

    group = GroupAction(
        condition=IfCondition(LaunchConfiguration('use_group')),
        actions=[
            PushRosNamespace(LaunchConfiguration('robot_namespace')),
            talker_node,
            listener_node,
        ],
    )

    # ----------------------------------------------------------------------
    # 4. 事件：监听进程的启动/退出
    # ----------------------------------------------------------------------
    # Nav2 的启动顺序控制全靠这个：
    #   "map_server 退出后自动拉起 amcl 重试" 之类的行为都是事件驱动。
    #
    # OnProcessStart：目标进程一启动就触发回调（注意是"进程启动"，
    #                 不是"节点初始化完成"——ROS2 没有后者的事件）
    # OnProcessExit： 目标进程退出后触发，常用来做"挂了自动重启/报错提示"
    on_talker_started = RegisterEventHandler(
        OnProcessStart(
            target_action=talker_node,
            on_start=[
                LogInfo(msg='[事件] talker 进程已启动，正在发布...'),
            ],
        )
    )

    on_listener_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=listener_node,
            on_exit=[
                LogInfo(msg='[事件] listener 退出了！生产环境这里应该报警或重启'),
            ],
        )
    )

    return LaunchDescription([
        use_group,
        ns,
        LogInfo(msg='=== Launch 进阶演示：条件 + 命名空间 + 重映射 + 事件 ==='),
        group,
        on_talker_started,
        on_listener_exit,
    ])
