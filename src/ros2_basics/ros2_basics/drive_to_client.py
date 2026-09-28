# -*- coding: utf-8 -*-
"""
==============================================================================
自定义动作客户端 —— 发 DriveTo 目标并跟踪进度（练习 7）
==============================================================================

【怎么运行】

    # 终端 1
    ros2 run ros2_basics drive_to_server
    # 终端 2
    ros2 run ros2_basics drive_to_client 3 4        # 开到 (3,4)
    ros2 run ros2_basics drive_to_client 5 0 1.5    # 开到 (5,0)，速度 1.5

    # 命令行版（注意 action 类型名的写法：包名/action/动作名）：
    ros2 action send_goal /drive_to ros2_basics_interfaces/action/DriveTo \
        "{target_x: 3, target_y: 4, max_speed: 1.0}" --feedback
"""

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from ros2_basics_interfaces.action import DriveTo


class DriveToClient(Node):
    def __init__(self):
        super().__init__('drive_to_client')
        self._client = ActionClient(self, DriveTo, 'drive_to')

    def send_goal(self, tx, ty, max_speed=1.0):
        self._client.wait_for_server()

        goal = DriveTo.Goal()
        goal.target_x = float(tx)
        goal.target_y = float(ty)
        goal.max_speed = float(max_speed)

        self.get_logger().info(f'发送目标：开到 ({tx}, {ty})，速度 {max_speed} m/s')

        future = self._client.send_goal_async(goal, feedback_callback=self.on_feedback)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('目标被拒绝（速度超范围？）')
            return

        # 想中途取消的话，在等结果期间调用：
        #   goal_handle.cancel_goal_async()
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result().result
        if result.reached:
            self.get_logger().info(
                f'✓ 到达目标，残余偏差 {result.final_distance:.3f} 米')
        else:
            self.get_logger().warn(
                f'未到达（被取消），停在距目标 {result.final_distance:.2f} 米处')

    def on_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        # 进度条打印，每收到一次 feedback 刷新一次
        bar = '#' * max(int((5 - fb.remaining_distance) / 5 * 30), 0)
        self.get_logger().info(
            f'剩余 {fb.remaining_distance:5.2f} 米 | 速度 {fb.current_speed:.1f} |{bar}')


def main(args=None):
    rclpy.init(args=args)
    tx = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    ty = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    v = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

    node = DriveToClient()
    node.send_goal(tx, ty, v)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
