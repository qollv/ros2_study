# -*- coding: utf-8 -*-
"""
==============================================================================
自定义动作服务端 —— DriveTo.action：驶向目标点（练习 7）
==============================================================================

这就是你自己版本的 NavigateToPose：
    Goal:     目标点和最大速度
    Feedback: 剩余距离、当前速度（每 0.2 秒一次）
    Result:   是否到达、停下时距目标多远

【怎么运行】

    # 终端 1
    ros2 run ros2_basics drive_to_server
    # 终端 2
    ros2 run ros2_basics drive_to_client 3 4
"""

import math
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

# .action 生成的类型在包的 action 子模块里
from ros2_basics_interfaces.action import DriveTo

# 到达容差：离目标多远算"到了"
# 对应你狗上 Nav2 的 xy_goal_tolerance = 0.15
GOAL_TOLERANCE = 0.10


class DriveToServer(Node):
    def __init__(self):
        super().__init__('drive_to_server')

        self._server = ActionServer(
            self,
            DriveTo,
            'drive_to',
            execute_callback=self.execute_cb,
            goal_callback=self.goal_cb,
            cancel_callback=self.cancel_cb,
            callback_group=ReentrantCallbackGroup())
        self.get_logger().info('DriveTo 动作服务端已就绪，动作名 /drive_to')

    def goal_cb(self, goal_request):
        """目标审核：速度非法就拒绝。"""
        if goal_request.max_speed < 0 or goal_request.max_speed > 2.0:
            self.get_logger().warn(f'拒绝目标：max_speed={goal_request.max_speed} 超范围')
            return GoalResponse.REJECT
        self.get_logger().info(
            f'接受目标：({goal_request.target_x}, {goal_request.target_y})，'
            f'速度上限 {goal_request.max_speed} m/s')
        return GoalResponse.ACCEPT

    def cancel_cb(self, goal_handle):
        return CancelResponse.ACCEPT

    async def execute_cb(self, goal_handle):
        """模拟开车：从原点出发，以固定速度直线逼近目标点。"""
        tx = goal_handle.request.target_x
        ty = goal_handle.request.target_y
        v = goal_handle.request.max_speed if goal_handle.request.max_speed > 0 else 0.5

        total = math.hypot(tx, ty)
        self.get_logger().info(f'开始执行：总路程 {total:.2f} 米')

        # 模拟的状态量
        travelled = 0.0       # 已经走了多远
        dt = 0.2              # 每步的仿真时间

        feedback = DriveTo.Feedback()

        while True:
            # ---- 取消检查：每步都要查（原因见 action_server.py）----
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = DriveTo.Result()
                result.reached = False
                result.final_distance = max(total - travelled, 0.0)
                self.get_logger().info(f'任务取消，距目标还剩 {result.final_distance:.2f} 米')
                return result

            # ---- 前进一步 ----
            travelled = min(travelled + v * dt, total)
            remaining = total - travelled

            # ---- 发反馈 ----
            feedback.remaining_distance = remaining
            feedback.current_speed = v
            goal_handle.publish_feedback(feedback)

            # ---- 到达判断：进入容差圈就算成功 ----
            # 真实机器人永远不会精确停在目标点上，所以必须定义容差。
            # 这就是你调 xy_goal_tolerance=0.15 时 Nav2 内部在做的事。
            if remaining <= GOAL_TOLERANCE:
                goal_handle.succeed()
                result = DriveTo.Result()
                result.reached = True
                result.final_distance = remaining
                self.get_logger().info(
                    f'到达！停在第 {GOAL_TOLERANCE}m 容差圈内，'
                    f'残余偏差 {remaining:.3f} 米')
                return result

            time.sleep(dt)


def main(args=None):
    rclpy.init(args=args)
    node = DriveToServer()
    executor = MultiThreadedExecutor()
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
