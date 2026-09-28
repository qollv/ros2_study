# -*- coding: utf-8 -*-
"""
==============================================================================
自定义消息发布者 —— 使用自己定义的 RobotStatus.msg（练习 7）
==============================================================================

【接口生成的原理】

你在 msg/RobotStatus.msg 里写的字段定义，colcon build 时会被
rosidl_default_generators 翻译成各种语言的代码：
    Python:  ros2_basics_interfaces/msg/_robot_status.py
    C++:     ros2_basics_interfaces/msg/robot_status.hpp
所以 .msg 文件改了之后必须重新 colcon build，和改 Python 代码要 rebuild 是一样的道理。

【导入方式（注意嵌套结构）】

    from ros2_basics_interfaces.msg import RobotStatus

    包名.msg .消息名          <- .msg 生成到 msg 子模块
    包名.srv .服务名          <- .srv 生成到 srv 子模块
    包名.action .动作名       <- .action 生成到 action 子模块

【怎么运行】

    # 终端 1
    ros2 run ros2_basics status_publisher
    # 终端 2：看效果
    ros2 topic echo /robot_status
"""

import rclpy
from rclpy.node import Node

# 导入自己包生成的消息类型
from ros2_basics_interfaces.msg import RobotStatus


class StatusPublisher(Node):
    def __init__(self):
        super().__init__('status_publisher')

        self.pub = self.create_publisher(RobotStatus, 'robot_status', 10)

        self.count = 0
        # 剩余路网节点（呼应你狗上的 0/1/2/3 路网，模拟一个个走完）
        self.remaining_waypoints = [1, 2, 3]

        self.timer = self.create_timer(1.0, self.on_timer)
        self.get_logger().info('状态发布者已启动，话题 /robot_status')

    def on_timer(self):
        msg = RobotStatus()

        # header 是嵌套消息，先实例化再填字段
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'

        # 模拟数据：电压缓慢下降，速度按正弦波动
        msg.battery_voltage = 8.2 - 0.01 * self.count
        msg.speed = abs(0.5 * (1 + self.count % 2))  # 0 / 1 交替，模拟走走停停
        msg.current_task = 'navigating' if self.count % 2 else 'waiting'
        msg.is_navigating = bool(self.count % 2)

        # 变长数组直接用 Python list 赋值
        msg.waypoint_ids = self.remaining_waypoints.copy()

        # 模拟走完一个节点
        if self.count > 0 and self.count % 4 == 0 and self.remaining_waypoints:
            done = self.remaining_waypoints.pop(0)
            self.get_logger().info(f'已到达路网节点 {done}')

        self.pub.publish(msg)
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = StatusPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
