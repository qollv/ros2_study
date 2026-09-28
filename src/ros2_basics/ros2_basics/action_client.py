# -*- coding: utf-8 -*-
"""
==============================================================================
动作客户端（Action Client）示例 —— 发目标、收反馈、拿结果
==============================================================================

【这个例子在学什么】

Action 的调用方，完整流程：
    1. 创建客户端，等服务上线
    2. 发送 Goal，拿到 goal_handle
    3. 注册 feedback 回调（持续收进度）
    4. 等任务结束，拿 Result

【对应到你的路网导航 —— 这就是你的核心逻辑长什么样】

你现在做的"逐节点拆段行驶"，本质上就是把下面这段包在循环里：

    for node in route_nodes:              # 路网里的每个节点
        goal = 构造 NavigateToPose.Goal(node)
        handle = 发送 goal
        while 未完成:
            监听 feedback（距离、速度、剩余距离）
            如果超时/偏移太大 -> cancel
        if 成功: 继续下一个节点
        else:   处理失败（重试 / 重规划）

    你定的 xy/yaw tolerance = 0.15/0.15，就是 Goal 消息里的容差字段。

【怎么运行】

    # 终端 1
    ros2 run ros2_basics action_server
    # 终端 2
    ros2 run ros2_basics action_client 5

    观察：每 1 秒收到一次 feedback，最后拿到 result。
"""

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from example_interfaces.action import Fibonacci


class FibonacciClient(Node):
    def __init__(self):
        super().__init__('fibonacci_action_client')

        # create_client 的 Action 版本：ActionClient(self, 类型, 动作名)
        # 同样要和服务端的类型、名字完全对应。
        self._client = ActionClient(self, Fibonacci, 'fibonacci')

    def send_goal(self, order):
        """发送一个目标，跟踪进度，最后拿结果。"""

        # ------------------------------------------------------------------
        # 1. 等服务上线
        # ------------------------------------------------------------------
        # 和服务一样，必须先等服务端就绪，否则发送会失败。
        self._client.wait_for_server()

        # ------------------------------------------------------------------
        # 2. 构造 Goal
        # ------------------------------------------------------------------
        # 导航里这里就是填 pose（位置+朝向）、坐标系、行为树名称等。
        goal = Fibonacci.Goal()
        goal.order = order

        self.get_logger().info(f'发送目标: 计算 {order} 项')

        # ------------------------------------------------------------------
        # 3. 发送目标（异步）
        # ------------------------------------------------------------------
        # send_goal_async 立刻返回 future，不会阻塞在这里。
        # 第二个参数 feedback_callback 注册进度回调：
        # 服务端每次 publish_feedback，on_feedback 就会被自动调用一次。
        #
        # 这就是 Action 比 Service 强的地方：发出去之后你还能干别的，
        # 进度会自动推给你。
        future = self._client.send_goal_async(
            goal,
            feedback_callback=self.on_feedback)

        # 等服务端回复"接不接受这个目标"
        rclpy.spin_until_future_complete(self, future)

        # ------------------------------------------------------------------
        # 4. 检查目标是否被接受
        # ------------------------------------------------------------------
        goal_handle = future.result()

        if not goal_handle.accepted:
            # 被拒绝的情况：目标非法、服务端正忙、目标点不可达等
            self.get_logger().error('目标被服务端拒绝')
            return

        # ------------------------------------------------------------------
        # 5. 等待最终结果
        # ------------------------------------------------------------------
        # get_result_async 返回另一个 future，任务跑完时它才完成。
        # 在这之前，feedback 回调会持续被调用。
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        # 取出结果。注意是两级 .result：
        #   result_future.result()          -> 一个封装对象
        #   .result                         -> 真正的 Fibonacci.Result
        #   .sequence                       -> 里面的字段
        #
        # 另外 .status 是状态码，可以判断是否被取消/中止：
        #   GoalStatus.STATUS_SUCCEEDED / CANCELED / ABORTED
        self.get_logger().info(
            f'最终结果: {result_future.result().result.sequence}')

    def on_feedback(self, feedback_msg):
        """
        进度回调：服务端每发一次 feedback，这里被调用一次。

        参数 feedback_msg 是封装对象，真正的 Feedback 在
        feedback_msg.feedback 里，所以是两级访问。

        导航里的用途：
            - 打印"剩余距离 2.3 米"
            - 判断偏航是否过大，过大就 cancel 重规划
            - 累计行驶里程、判断超时
        """
        self.get_logger().info(f'进度反馈: {feedback_msg.feedback.sequence}')


def main(args=None):
    rclpy.init(args=args)

    # 从命令行读参数，默认算 5 项
    # 用法：ros2 run ros2_basics action_client 8
    order = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    node = FibonacciClient()
    node.send_goal(order)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
