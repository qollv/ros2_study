# -*- coding: utf-8 -*-
"""
==============================================================================
客户端（Service Client）示例 —— 演示如何调用 Service
==============================================================================

【这个例子在学什么】

Service 的调用方。核心流程三步：
    1. 创建客户端，等服务上线
    2. 发请求（拿到一个 future）
    3. 等 future 完成，取结果

【一个必须记住的坑】

spin_until_future_complete() 会**阻塞当前线程**直到拿到结果。
所以：

    绝对不要在定时器回调 / 订阅回调 / 服务回调里调用同步 Service！

因为那些回调本身就运行在 spin 线程里，再同步等待就是自己等自己，
必然死锁（永远等不到结果）。

正确的两种写法：
    A. 异步：call_async() + add_done_callback()，不阻塞（推荐）
    B. 同步：spin_until_future_complete()，但只能在 main() 这种独立线程里用

本例是 B（简单直观，适合脚本），A 的写法见下面代码里的注释。

【怎么运行】

    # 终端 1
    ros2 run ros2_basics service_server
    # 终端 2
    ros2 run ros2_basics service_client 3 5      # 输出 8
    ros2 run ros2_basics service_client 10 20    # 输出 30
"""

import sys

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddClient(Node):
    def __init__(self):
        super().__init__('add_two_ints_client')

        # create_client(服务类型, 服务名)
        # 类型和服务名必须和服务端完全一致。
        #
        # 注意：create_client 是"惰性"的——即使服务端还没启动，
        # 这行也不会报错。所以必须显式等待（见下面）。
        self.cli = self.create_client(AddTwoInts, 'add_two_ints')

        # ------------------------------------------------------------------
        # 等服务上线
        # ------------------------------------------------------------------
        # wait_for_service(timeout_sec) 轮询服务是否可用，返回 True/False。
        # 用 while 循环一直等，并打日志提示——否则用户会以为程序卡死了。
        #
        # 为什么必须等：如果在服务端启动前就 call_async，
        # 请求会直接失败（future 立刻变成"已完成但失败"状态）。
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待服务 /add_two_ints ...')

    def send(self, a, b):
        """同步方式调用服务：发请求，等结果，返回结果值。"""

        # 1. 构造请求对象并填字段
        req = AddTwoInts.Request()
        req.a = a
        req.b = b

        # 2. 发请求。call_async 立刻返回一个 future（未来结果），不阻塞。
        #
        #    如果不想阻塞，这里可以改成异步写法：
        #        future = self.cli.call_async(req)
        #        future.add_done_callback(self.on_result)   # 结果好了自动回调
        #    然后继续干别的事，不要 spin_until_future_complete。
        future = self.cli.call_async(req)

        # 3. 阻塞等待，直到服务端返回结果（或超时/失败）。
        #    这一行期间，本节点的 spin 在跑，所以能收到服务端的回复。
        rclpy.spin_until_future_complete(self, future)

        # 4. 从 future 里取结果。
        #    future.result() 返回的是 AddTwoInts.Response，取 .sum 字段。
        return future.result().sum


def main(args=None):
    rclpy.init(args=args)

    # 从命令行读两个数，没传就用默认值 3 和 5
    # 用法：ros2 run ros2_basics service_client 10 20
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    node = AddClient()
    node.get_logger().info(f'结果: {node.send(a, b)}')

    # 注意：这个节点是一次性的，拿到结果就销毁退出，没有 spin 常驻。
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
