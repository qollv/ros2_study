# -*- coding: utf-8 -*-
"""
==============================================================================
发布者（Publisher）示例 —— 演示 Topic 通信 + Parameter 声明
==============================================================================

【这个例子在学什么】

1. Topic（话题）：ROS2 里最基础、最常用的通信方式。特点：
   - 单向：发布者只管发，不知道谁在收，也不需要收到回复
   - 异步：publish() 调用后立刻返回，不会等对方处理完
   - 多对多：一个话题可以有多个发布者、多个订阅者
   - 持续：像水流一样连续不断

2. Parameter（参数）：节点内部的配置变量，可以在 yaml 里预先配好，
   也可以在节点运行时动态修改。

【对应到你的导航场景】

雷达驱动节点持续发布 /scan 话题，就是典型的 Topic：
它不需要知道 Nav2 有没有在听，也不需要 Nav2 回复，只管按固定频率往外发。
而"发布频率"这种数值，就是用 Parameter 来配置的。

【怎么运行】

    ros2 run ros2_basics talker
    # 或者用 launch（推荐，会自动带参数）：
    ros2 launch ros2_basics demo_launch.py rate:=5.0

【运行后可以在另一个终端观察】

    ros2 topic echo /chatter      # 看消息内容
    ros2 topic hz /chatter        # 看实际频率，验证 rate 参数生效
    ros2 topic info /chatter      # 看谁在发、谁在收
    ros2 node info /talker        # 看这个节点所有的输入/输出/参数
    ros2 param set /talker rate 10.0   # 运行时改频率，不用重启节点
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    """
    一个最简单的发布者节点。

    继承 rclpy.node.Node 是使用 Python 写 ROS2 节点的标准做法：
    Node 基类已经帮我们处理了节点注册、参数服务、生命周期等一堆杂事，
    我们只需要关心业务逻辑。
    """

    def __init__(self):
        # 调用父类构造函数，参数 'talker' 是节点名（node name）。
        # 节点名在整个 ROS2 网络里必须尽量唯一，ros2 node list 看到的就是它。
        # 如果两个节点同名，后启动的会把先启动的踢掉。
        super().__init__('talker')

        # ------------------------------------------------------------------
        # 1. 声明参数
        # ------------------------------------------------------------------
        # declare_parameter(参数名, 默认值)
        #
        # 必须"先声明、后使用"。如果直接 get 一个没声明过的参数，会抛异常。
        # 这一步相当于告诉 ROS2："我这个节点有个叫 rate 的配置项，默认 2.0"。
        #
        # 声明之后，外部就能通过以下方式操作它：
        #   ros2 param get /talker rate
        #   ros2 param set /talker rate 5.0
        #   ros2 param dump /talker          导出成 yaml
        self.declare_parameter('rate', 2.0)

        # 读取参数值。注意读出来的是一个 Parameter 对象，不是裸数值，
        # 需要用 .value 或 .get_parameter_value().double_value 取出真实数据。
        # （两种写法等价，下面用 .value 更简洁）
        rate = self.get_parameter('rate').get_parameter_value().double_value

        # ------------------------------------------------------------------
        # 2. 创建发布者
        # ------------------------------------------------------------------
        # create_publisher(消息类型, 话题名, 队列长度)
        #
        # 消息类型：String，来自 std_msgs.msg。发布者和订阅者必须用完全相同的
        #           类型，哪怕字段名都一样、包名不同也不行——这是新手最常见的
        #           "明明在发却收不到"的原因。
        #
        # 话题名：'chatter'。这里写的是相对名，ROS2 会自动加上节点的命名空间，
        #         最终变成类似 /chatter。建议养成用 ros2 topic list 核对的习惯。
        #
        # 队列长度（QoS depth）= 10：
        #         如果订阅者处理不过来，最多缓存 10 条消息，超出的丢掉最旧的。
        #         对于传感器数据（/scan 这种），设 1 反而更好——你永远只想要
        #         最新的那帧，缓存一堆旧点云毫无意义。
        self.pub = self.create_publisher(String, 'chatter', 10)

        # ------------------------------------------------------------------
        # 3. 创建定时器
        # ------------------------------------------------------------------
        # create_timer(周期秒数, 回调函数)
        # 每 1.0/rate 秒触发一次 on_timer。
        #
        # 重要：ROS2 的定时器回调是在 spin() 的线程里串行执行的。
        # 也就是说，如果 on_timer 里做了耗时 5 秒的事，那么这个节点
        # 在这 5 秒内无法响应任何其他回调（参数修改、服务请求都会卡住）。
        # 这是 ROS2 初学者最容易踩的性能坑。
        self.count = 0
        self.timer = self.create_timer(1.0 / rate, self.on_timer)

        # get_logger() 是节点自带的日志器，比 print 好在：
        #   1. 自动带节点名和时间戳
        #   2. 有等级（info/warn/error），可以用参数设置显示级别
        #   3. 会同时写入 ~/.ros/log，方便事后排查
        self.get_logger().info(f'发布者已启动，频率 {rate} Hz，话题 /chatter')

    def on_timer(self):
        """定时器回调：构造一条消息并发出去。"""

        # ROS2 的消息类型是类，实例化后给字段赋值。
        # String 类型只有一个字段 data。
        msg = String()
        msg.data = f'hello ros2 {self.count}'

        # 发布。这个调用是异步的、非阻塞的，立刻返回。
        # 注意：publish 之后不要立刻修改 msg 的内容，因为底层可能还没拷贝完。
        self.pub.publish(msg)

        self.get_logger().info(f'发布: "{msg.data}"')
        self.count += 1


def main(args=None):
    """
    节点入口函数。

    每个 ROS2 Python 节点都遵循这个三段式结构：
        rclpy.init()  ->  创建节点 + spin()  ->  destroy + shutdown()
    """

    # 初始化 rclpy 库。一个进程只需要调用一次。
    # 它会解析命令行参数（比如 --ros-args -p rate:=5.0）。
    rclpy.init(args=args)

    node = Talker()

    try:
        # spin 让节点进入事件循环：不断检查有没有定时器到期、
        # 有没有新消息、有没有服务请求，有就调用对应回调。
        # 这一行会一直阻塞，直到节点被关闭。
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl+C 会抛 KeyboardInterrupt，这里静默处理，让流程走到 finally 正常收尾。
        pass
    finally:
        # 显式销毁节点并关闭 rclpy，释放资源。
        # 不写的话进程结束时也可能正常退出，但显式写是规范做法，
        # 尤其在写单元测试时（同一个进程里反复 init/shutdown）是必须的。
        node.destroy_node()
        rclpy.shutdown()


# Python 标准写法：只有直接运行这个文件时才执行 main()。
# 被 import 时不会自动启动节点——这样测试代码可以安全地 import 这个类。
if __name__ == '__main__':
    main()
