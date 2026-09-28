# -*- coding: utf-8 -*-
"""
==============================================================================
订阅者（Subscriber）示例 —— 演示 Topic 通信的接收端
==============================================================================

【这个例子在学什么】

Topic 的另一端：订阅者。特点：
  - 被动：不需要主动查询，有消息来的时候 ROS2 自动调用你的回调函数
  - 松耦合：订阅者完全不知道发布者是谁、在哪台机器上，
            只要话题名和消息类型对上就能收到
  - 回调驱动：收到一条消息就触发一次回调

【对应到你的导航场景】

Nav2 订阅 /scan（激光数据）和 /odom（里程计）就是这种模式。
Nav2 不需要知道雷达是思岚还是镭神、跑在哪个进程里，
它只关心"有没有人往 /scan 上发 sensor_msgs/LaserScan"。

【怎么运行】

    # 终端 1
    ros2 run ros2_basics talker
    # 终端 2
    ros2 run ros2_basics listener
    # 或者一条命令起两个：
    ros2 launch ros2_basics demo_launch.py

【调试技巧】

如果 listener 收不到消息，按这个顺序排查：
    1. ros2 topic list                 话题真的存在吗？名字拼写对吗？
    2. ros2 topic info /chatter        发布者和订阅者数量对吗？
    3. ros2 topic echo /chatter        话题上有数据吗？
    4. ros2 node info /listener        订阅的话题名有没有多一个斜杠/命名空间？
    5. rqt_graph                       看连线图，一眼就能发现断在哪
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    """一个最简单的订阅者节点。"""

    def __init__(self):
        super().__init__('listener')

        # ------------------------------------------------------------------
        # 创建订阅者
        # ------------------------------------------------------------------
        # create_subscription(消息类型, 话题名, 回调函数, 队列长度)
        #
        # 三个必须和发布者完全一致，否则收不到任何东西（而且不会报错！）：
        #   1. 消息类型 String
        #   2. 话题名 'chatter'
        #   3. QoS 设置（这里用默认的，队列长度 10）
        #
        # 第 4 个参数 10 的含义和发布者一样：最多缓存 10 条待处理消息。
        # 如果回调处理得慢，超出的旧消息会被丢弃。
        #
        # 注意：create_subscription 返回的对象必须保存成成员变量（self.sub）。
        # 如果写成局部变量 sub = self.create_subscription(...)，
        # 函数结束后对象会被 Python 垃圾回收，订阅立刻失效——这是个经典陷阱。
        self.sub = self.create_subscription(
            String, 'chatter', self.on_msg, 10)

        self.get_logger().info('订阅者已启动，监听 /chatter')

    def on_msg(self, msg):
        """
        收到消息时的回调。

        每收到一条消息被调用一次。参数 msg 就是发布者发的那个对象，
        这里是 std_msgs/String，用 msg.data 取内容。

        【重要约束】
        这个回调运行在 spin() 的线程里。如果这里做了耗时操作
        （比如 sleep、网络请求、大量计算），会阻塞这个节点的所有其他回调。

        如果处理确实很慢，正确做法是：
          - 把数据放进队列，交给另一个线程/进程处理
          - 或者用 MultiThreadedExecutor + 回调组
        导航里的点云处理、图像识别都是这么干的。
        """
        self.get_logger().info(f'收到: "{msg.data}"')


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    try:
        # spin 进入事件循环，等待消息到来并触发 on_msg
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
