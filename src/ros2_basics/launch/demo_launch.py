# -*- coding: utf-8 -*-
"""
==============================================================================
Launch 文件示例 —— 一条命令启动多个节点并注入参数
==============================================================================

【Launch 文件是干什么的】

不用开 N 个终端手动敲 N 条 ros2 run，一条 ros2 launch 全部搞定，
还能：
    - 给节点传参数
    - 给节点重命名、加命名空间
    - 控制启动顺序、设置环境变量
    - 根据条件决定启不启动某个节点

【为什么对你重要】

Nav2 导航系统有十几个节点（planner_server、controller_server、
bt_navigator、amcl、map_server、costmap 两层...），
全靠 launch 文件组织。你狗上的导航启动脚本就是个复杂版 launch 文件。

【怎么运行】

    ros2 launch ros2_basics demo_launch.py
    ros2 launch ros2_basics demo_launch.py rate:=5.0       # 覆盖默认参数
    ros2 launch ros2_basics demo_launch.py rate:=0.5 --debug

【Launch 文件是 Python】

所以可以写 if/for、读配置文件、拼字符串，非常灵活。
但注意：它不是节点，只是"描述要启动什么"，
真正启动后的节点是独立进程，和 launch 进程没关系了。
"""

# generate_launch_description 是唯一必须有的函数，
# ROS2 会调用它拿到一个 LaunchDescription 对象。
from launch import LaunchDescription

# 声明一个可以在命令行覆盖的参数
from launch.actions import DeclareLaunchArgument

# 用来引用上面声明的参数值（延迟求值：运行时才确定）
from launch.substitutions import LaunchConfiguration

# 启动一个 ROS2 节点
from launch_ros.actions import Node


def generate_launch_description():
    """组装并返回 LaunchDescription。"""

    # ----------------------------------------------------------------------
    # 1. 声明 launch 参数
    # ----------------------------------------------------------------------
    # DeclareLaunchArgument(参数名, 默认值, 描述)
    #
    # 声明后，命令行就能用 `参数名:=值` 覆盖：
    #     ros2 launch ros2_basics demo_launch.py rate:=5.0
    #
    # 如果不声明就直接用，命令行传 rate:=5.0 会报错"未知参数"。
    #
    # 这也是 Nav2 的标准做法，比如：
    #     ros2 launch nav2_bringup navigation_launch.py params_file:=my_params.yaml
    rate_arg = DeclareLaunchArgument(
        'rate',
        default_value='2.0',
        description='发布频率 Hz')

    # ----------------------------------------------------------------------
    # 2. 定义要启动的节点
    # ----------------------------------------------------------------------
    # Node() 的常用参数：
    #   package       功能包名（对应 package.xml 里的 <name>）
    #   executable    可执行文件名（对应 setup.py 里 entry_points 注册的名字）
    #   name          节点名，会覆盖代码里 super().__init__('talker') 的名字
    #   namespace     命名空间，话题会变成 /ns/chatter，用于多机器人区分
    #   output        'screen' 把日志打到终端（不加的话日志只进文件，看不到）
    #   parameters    参数列表，可以传 dict 或 yaml 文件路径
    #   remappings    话题重映射，比如把 /chatter 改成 /my_chatter
    #   arguments     传给节点的命令行参数
    #   respawn       节点挂了是否自动重启（真机上很有用）

    talker = Node(
        package='ros2_basics',
        executable='talker',
        name='talker',
        output='screen',

        # 传参：这里用 LaunchConfiguration('rate') 引用上面声明的 launch 参数。
        #
        # 注意 launch 参数的值本质上是字符串（'5.0'），
        # 但 ROS2 会根据节点里 declare_parameter 时默认值的类型自动转换，
        # 所以这里传字符串给 double 类型的 rate 是没问题的。
        #
        # parameters 是列表，可以传多个来源，后面的覆盖前面的：
        #   parameters=[{'rate': 2.0}, '/path/to/params.yaml']
        parameters=[{'rate': LaunchConfiguration('rate')}],
    )

    listener = Node(
        package='ros2_basics',
        executable='listener',
        name='listener',
        output='screen',

        # 演示话题重映射：
        # 如果打开下面这行，listener 会去订阅 /my_chatter 而不是 /chatter，
        # 而 talker 还在往 /chatter 发，于是就收不到了——
        # 这正好可以帮你理解"话题名必须一致"这件事。
        # remappings=[('chatter', 'my_chatter')],
    )

    # ----------------------------------------------------------------------
    # 3. 组装返回
    # ----------------------------------------------------------------------
    # 列表里的元素按顺序处理。
    # 注意：Node 的启动是并发的，列表顺序不代表启动完成的先后顺序。
    # 如果需要严格的启动顺序（比如必须先起 map_server 再起 amcl），
    # 需要用 RegisterEventHandler + OnProcessExit 等事件机制。
    return LaunchDescription([rate_arg, talker, listener])
