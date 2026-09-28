# -*- coding: utf-8 -*-
"""
==============================================================================
自定义服务端 —— ComputePath.srv：给定起终点，算路径长度（练习 7）
==============================================================================

【怎么运行】

    # 终端 1
    ros2 run ros2_basics path_server

    # 终端 2：不需要写客户端代码，命令行直接调
    ros2 service call /compute_path ros2_basics_interfaces/srv/ComputePath \
        "{start_x: 0.0, start_y: 0.0, goal_x: 3.0, goal_y: 4.0}"

    # 应返回：success=true, distance=5.0（勾股定理 3-4-5）
"""

import math

import rclpy
from rclpy.node import Node

# .srv 生成的类型在包的 srv 子模块里
from ros2_basics_interfaces.srv import ComputePath


class PathServer(Node):
    def __init__(self):
        super().__init__('path_server')

        # 方法名不能叫 handle！原因见 service_server.py 里的踩坑记录
        self.srv = self.create_service(ComputePath, 'compute_path', self.compute_callback)
        self.get_logger().info('路径计算服务已就绪，服务名 /compute_path')

    def compute_callback(self, request, response):
        """算起终点直线距离（真实项目里这里会调 A* / Dijkstra）。"""

        dx = request.goal_x - request.start_x
        dy = request.goal_y - request.start_y
        distance = math.hypot(dx, dy)

        # 业务规则：起点终点几乎重合时拒绝，演示 response 里多字段的用法
        if distance < 0.05:
            response.success = False
            response.distance = 0.0
            response.message = '起点和终点太近，无需规划'
        else:
            response.success = True
            response.distance = distance
            response.message = f'直线距离 {distance:.2f} 米（实际项目这里换成 A*）'

        self.get_logger().info(
            f'({request.start_x},{request.start_y}) -> ({request.goal_x},{request.goal_y})'
            f' = {response.distance:.2f}m, success={response.success}')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = PathServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
