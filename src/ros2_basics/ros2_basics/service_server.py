# -*- coding: utf-8 -*-
"""
==============================================================================
服务端（Service Server）示例 —— 演示 Service 通信
==============================================================================

【Service 和 Topic 的区别】

    Topic：   持续的数据流，发出去就不管了（像广播）
    Service： 一问一答，调用方会停下来等结果（像打电话）

判断标准很简单：
    - 这个数据是"一直在产生"的？       -> Topic
    - 我是"要做一件事并立刻要结果"？   -> Service
    - 这件事要干很久（几秒以上）？     -> Action（见 action_server.py）

【对应到你的导航场景】

    /clear_costmaps            清空代价地图（Nav2 服务）
    /reinitialize_global_localization   全局重定位

这些操作都是"发个指令，做完告诉我"，耗时极短，用 Service 正合适。
注意：Service 是同步阻塞的，调用期间调用方线程会被卡住，
所以绝对不要在 Service 里放耗时几秒的任务——那种要用 Action。

【怎么运行】

    # 终端 1：启动服务端
    ros2 run ros2_basics service_server

    # 终端 2：用客户端调用
    ros2 run ros2_basics service_client 3 5

    # 或者根本不用写代码，命令行直接调（调试时超好用）：
    ros2 service list
    ros2 service type /add_two_ints
    ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 10, b: 20}"
"""

import rclpy
from rclpy.node import Node

# AddTwoInts 是 ROS2 自带的示例服务类型（来自 example_interfaces 包）。
# 一个 .srv 文件分成两部分，用 --- 隔开：
#
#   int64 a        <- Request 部分：客户端填这些字段
#   int64 b
#   ---
#   int64 sum      <- Response 部分：服务端填这些字段
#
# 在 Python 里体现为：
#   AddTwoInts.Request()  有 .a 和 .b
#   AddTwoInts.Response() 有 .sum
from example_interfaces.srv import AddTwoInts


class AddServer(Node):
    def __init__(self):
        super().__init__('add_two_ints_server')

        # ------------------------------------------------------------------
        # 创建服务
        # ------------------------------------------------------------------
        # create_service(服务类型, 服务名, 处理回调)
        #
        # 服务名 'add_two_ints' -> 实际话题名 /add_two_ints
        #
        # 和 Topic 不同，Service 是唯一的服务端：
        # 如果有两个节点用同一个服务名 create_service，会冲突报错。
        # （Topic 则允许多个发布者同时往一个话题发）
        # ！！！这里有个真实踩过的坑，务必注意！！！
        #
        # 下面的回调方法名叫 add_callback，而不是更自然的 handle。
        # 原因：Node 基类本身就有一个名为 handle 的属性（底层 rcl_node_t 句柄），
        # 如果你把方法命名为 handle，它会覆盖基类的 handle 属性，
        # 于是 Node.__init__ 内部执行 `with self.handle:` 时拿到的
        # 是你的方法对象而不是节点句柄，直接报：
        #     AttributeError: __enter__
        #
        # 这个报错信息完全看不出原因，我debug的时候绕了很久。
        # 记住：给节点类起方法名/变量名时，避开这些 Node 已有成员：
        #     handle / name / namespace / logger / executor / context / clock
        self.srv = self.create_service(AddTwoInts, 'add_two_ints', self.add_callback)

        self.get_logger().info('服务端已就绪，服务名 /add_two_ints')

    def add_callback(self, request, response):
        """
        服务处理回调。（方法名不能叫 handle，原因见上面 create_service 处的注释）

        参数：
            request  - 客户端发来的请求对象，这里是 AddTwoInts.Request，有 .a .b
            response - 一个空的响应对象 AddTwoInts.Response，有 .sum
        返回：
            填好字段的 response，ROS2 会自动把它发回给客户端

        【关键约束】
        这个函数运行在 spin() 线程里，而且是同步的：
        在它返回之前，这个节点无法处理任何其他回调。
        所以这里只能放"毫秒级"的轻量操作。

        如果你的服务要干 3 秒的活，正确做法：
          1. 在 handle 里只记录请求、立刻返回
          2. 用另一个线程慢慢做
          3. 或者干脆改成 Action（见 action_server.py）
        """
        # 读请求字段
        a, b = request.a, request.b

        # 填响应字段
        response.sum = a + b

        self.get_logger().info(f'请求 {a} + {b} -> 返回 {response.sum}')

        # 必须 return response，不能返回 None
        return response


def main(args=None):
    rclpy.init(args=args)
    node = AddServer()
    try:
        # spin 等待服务请求到达，收到就调 handle
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
