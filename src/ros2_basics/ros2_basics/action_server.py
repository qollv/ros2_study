# -*- coding: utf-8 -*-
"""
==============================================================================
动作服务端（Action Server）示例 —— 演示 Action 通信
==============================================================================

【为什么需要 Action？它比 Service 多了什么】

Service 的局限：调用后只能干等，中途不知道进度、也不能取消。
如果任务要跑几十秒（比如"导航到 10 米外"），Service 完全不够用。

Action 在 Service 基础上加了三样东西：
    1. Feedback（反馈）  —— 执行过程中持续回传进度
    2. Cancel（取消）    —— 客户端可以中途喊停
    3. 异步             —— 发送后不用干等，可以干别的事

对比记忆：
    Topic   = 广播，单向，持续
    Service = 打电话，问一句答一句，中间不能挂断
    Action  = 点外卖，下单后能看配送进度，还能中途退单

【对应到你的导航场景 —— 这就是 NavigateToPose 的原型】

    goal     目标点      -> "去 (x=3.0, y=1.5, yaw=0.0)"
    feedback 实时反馈    -> "当前位置、剩余距离、已耗时"（Nav2 里就是这个）
    result   最终结果    -> "成功到达 / 失败 / 被取消"
    cancel   中途取消    -> 你说"别去了"，导航立刻停

你的路网导航（逐节点拆段行驶）本质上就是：
    循环发 NavigateToPose goal -> 监听 feedback -> 收到 succeed 再发下一个

【怎么运行】

    # 终端 1
    ros2 run ros2_basics action_server
    # 终端 2
    ros2 run ros2_basics action_client 5

    # 命令行版（不用写代码就能测）：
    ros2 action list
    ros2 action info /fibonacci
    ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 5}" --feedback

    # 试取消（在任务执行中，另开终端）：
    ros2 action cancel /fibonacci
"""

import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

# Fibonacci（斐波那契数列）是 ROS2 自带的示例 Action 类型。
# 一个 .action 文件有三部分，用两个 --- 隔开：
#
#   int32 order          <- Goal：客户端发的请求（算多少项）
#   ---
#   int32[] sequence     <- Result：最终结果
#   ---
#   int32[] sequence     <- Feedback：执行中的进度
#
# Python 里体现为：
#   Fibonacci.Goal()     有 .order
#   Fibonacci.Result()   有 .sequence
#   Fibonacci.Feedback() 有 .sequence
from example_interfaces.action import Fibonacci


class FibonacciServer(Node):
    def __init__(self):
        super().__init__('fibonacci_action_server')

        # ------------------------------------------------------------------
        # 创建 Action 服务端
        # ------------------------------------------------------------------
        # 比 create_service 多了几个回调，因为 Action 的生命周期更复杂：
        #
        #   goal_callback      -> 收到新目标，决定接不接受
        #   cancel_callback    -> 收到取消请求，决定同不同意
        #   execute_callback   -> 真正干活（耗时长），可以发 feedback
        self._server = ActionServer(
            self,
            Fibonacci,                          # Action 类型
            'fibonacci',                        # Action 名 -> /fibonacci
            execute_callback=self.execute_cb,   # 执行（必须）
            goal_callback=self.goal_cb,         # 目标审核（可选）
            cancel_callback=self.cancel_cb,     # 取消审核（可选）

            # --------------------------------------------------------------
            # 回调组：这一行非常重要，是 Action 能不能正常工作的关键
            # --------------------------------------------------------------
            # 默认情况下，一个节点的所有回调都在同一个线程里串行执行。
            # 而 execute_cb 是个长时间任务（这里要跑好几秒），
            # 如果它占着线程，发布 feedback 的调用就会被阻塞，
            # 结果就是客户端收不到任何进度反馈，直到任务结束才一次性收到。
            #
            # ReentrantCallbackGroup 允许多个回调并发执行，
            # 配合下面的 MultiThreadedExecutor，才能真正实现"边干边报进度"。
            #
            # 另一种选择：MutuallyExclusiveCallbackGroup（默认），
            # 适合需要互斥访问共享数据的场景。
            callback_group=ReentrantCallbackGroup())

        self.get_logger().info('动作服务端已就绪，动作名 /fibonacci')

    # ----------------------------------------------------------------------
    # 回调 1：目标审核
    # ----------------------------------------------------------------------
    def goal_cb(self, goal_request):
        """
        客户端发来目标时先经过这里，你可以拒绝不合理的要求。

        实际用途：导航时检查目标点是否在地图边界内、是否可达，
        不合理就直接 REJECT，客户端立刻知道失败了，不用白等。
        """
        order = goal_request.order

        # 拒绝非法请求（比如负数或 0）
        if order < 1:
            self.get_logger().warn(f'拒绝目标：order={order} 非法')
            return GoalResponse.REJECT

        self.get_logger().info(f'接受目标：计算 {order} 项')
        return GoalResponse.ACCEPT

    # ----------------------------------------------------------------------
    # 回调 2：取消审核
    # ----------------------------------------------------------------------
    def cancel_cb(self, goal_handle):
        """
        客户端请求取消时经过这里。

        实际用途：导航中有些状态不允许立刻停（比如正在做紧急避障），
        可以在这里返回 REJECT，要求客户端等待。
        """
        self.get_logger().info('收到取消请求')
        return CancelResponse.ACCEPT

    # ----------------------------------------------------------------------
    # 回调 3：真正执行（核心）
    # ----------------------------------------------------------------------
    async def execute_cb(self, goal_handle):
        """
        执行任务。注意这是 async def —— 必须是异步函数。

        goal_handle 是这次任务的句柄，通过它可以：
            goal_handle.publish_feedback(fb)   发进度
            goal_handle.is_cancel_requested    查有没有人喊停
            goal_handle.succeed()              标记成功
            goal_handle.canceled()             标记被取消
            goal_handle.abort()                标记异常终止

        返回值必须是 Action 类型的 Result 对象。
        """

        # 初始化反馈消息：斐波那契数列前两项
        feedback = Fibonacci.Feedback()
        feedback.sequence = [0, 1]

        # 逐项计算。range(1, order) 表示一共算 order 项。
        for i in range(1, goal_handle.request.order):

            # ---- 检查取消 ----
            # 每一轮循环都要查一次，否则取消请求永远得不到响应。
            # 这是 Action 编程最容易漏的一步：
            # 只在循环外查一次的话，用户点取消后要等整个任务跑完才生效。
            if goal_handle.is_cancel_requested:
                # 通知客户端"已取消"，然后返回一个空的 Result
                goal_handle.canceled()
                self.get_logger().info('任务已取消')
                return Fibonacci.Result()

            # ---- 干活：追加下一项 ----
            feedback.sequence.append(
                feedback.sequence[i] + feedback.sequence[i - 1])

            # ---- 发进度反馈 ----
            # 对应导航里的"已行驶 3.2 米，剩余 1.8 米"
            self.get_logger().info(f'反馈进度: {feedback.sequence}')
            goal_handle.publish_feedback(feedback)

            # 故意 sleep 1 秒，模拟真实任务的耗时。
            #
            # 【重要】这里用的是 time.sleep() 而不是 rclpy 的定时器，
            # 因为它会阻塞当前线程。之所以没问题，是因为我们配了
            # MultiThreadedExecutor + ReentrantCallbackGroup，
            # execute 跑在独立线程里，不会卡住节点其他功能。
            #
            # 真实项目里，如果是等 I/O（网络、串口），应该用
            # await 异步等待，而不是阻塞 sleep。
            time.sleep(1.0)

        # ---- 标记成功并返回结果 ----
        goal_handle.succeed()

        result = Fibonacci.Result()
        result.sequence = feedback.sequence

        self.get_logger().info(f'任务完成: {result.sequence}')
        return result


def main(args=None):
    rclpy.init(args=args)
    node = FibonacciServer()

    # ----------------------------------------------------------------------
    # 必须用多线程执行器
    # ----------------------------------------------------------------------
    # 默认的 SingleThreadedExecutor 只有一个线程，
    # 配了 ReentrantCallbackGroup 也白搭——因为根本没有第二个线程可用。
    # 这两个必须成对出现，缺一个 feedback 就发不出去。
    executor = MultiThreadedExecutor()

    try:
        # 注意把 executor 传给 spin
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
