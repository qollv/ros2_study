# -*- coding: utf-8 -*-
"""
setup.py —— ament_python 包的构建配置

这个文件告诉 colcon"这个包该怎么装"。最关键的是末尾的 entry_points，
它决定了 ros2 run 能调用哪些可执行文件。

【改了这个文件之后必须重新 build】
    colcon build --packages-select ros2_basics

【常见坑】
    加了新节点却忘了在 entry_points 里注册 -> ros2 run 报 "executable not found"
"""

from setuptools import setup

# 包名，必须和 package.xml 里的 <name> 一致
package_name = 'ros2_basics'

setup(
    name=package_name,
    version='0.0.1',

    # 要安装的 Python 模块目录。
    # 这里填 ['ros2_basics'] 表示安装 src/ros2_basics/ros2_basics/ 这个子目录
    # （外层目录名是包名，内层同名目录才是 Python 模块 —— ROS2 的约定）
    packages=[package_name],

    # 需要安装到系统的数据文件，三项都是必需的：
    #
    # 第 1 项：包的"索引标记"文件。
    #   内容为空即可，但文件必须存在，否则 ros2 pkg list 找不到这个包。
    #   路径固定：share/ament_index/resource_index/packages/<包名>
    #
    # 第 2 项：package.xml 本身，供其他工具查询依赖信息。
    #
    # 第 3 项：launch 文件。
    #   必须安装，否则 ros2 launch 找不到 demo_launch.py。
    #   这是新手最常漏的一项。
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/demo_launch.py']),
    ],

    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='qhr',
    maintainer_email='qhr@example.com',
    description='ROS2 Humble 基础练习集合',
    license='Apache-2.0',

    # ----------------------------------------------------------------------
    # 核心：注册可执行入口
    # ----------------------------------------------------------------------
    # 格式：'命令名 = 模块.文件:函数名'
    #
    #   ros2 run ros2_basics talker
    #              ^包名      ^这里注册的命令名
    #
    # 'talker = ros2_basics.talker:main' 的含义：
    #   导入 ros2_basics/talker.py，调用它的 main() 函数
    #
    # 新增节点时：
    #   1. 在 ros2_basics/ 下写 xxx.py，里面有 main()
    #   2. 在这里加一行 'xxx = ros2_basics.xxx:main'
    #   3. colcon build
    #   4. source install/setup.bash
    entry_points={
        'console_scripts': [
            'talker = ros2_basics.talker:main',
            'listener = ros2_basics.listener:main',
            'service_server = ros2_basics.service_server:main',
            'service_client = ros2_basics.service_client:main',
            'action_server = ros2_basics.action_server:main',
            'action_client = ros2_basics.action_client:main',
            'param_demo = ros2_basics.param_demo:main',
            'qos_demo = ros2_basics.qos_demo:main',
        ],
    },
)
