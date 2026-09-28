# -*- coding: utf-8 -*-
"""
==============================================================================
静态 TF 广播器 —— 广播 base_link -> laser（雷达在机器人上的安装位姿）
==============================================================================

【TF 是什么】

TF（Transform，坐标变换）是 ROS 的"空间账本"：
它回答的唯一问题是 —— 「坐标系 A 里的一个点，在坐标系 B 里是哪？」

整个系统维护一棵坐标系树（TF 树）：
    map -> odom -> base_link -> laser
每条边由某一个节点负责广播，其他所有节点都可以查询树上任意两点的变换。

【为什么这条边是"静态"的】

base_link -> laser 是雷达在机器人上的安装位姿——用螺丝拧死的，
机器人跑起来它也不会变。所以：
    - 只需要在启动时广播一次（StaticTransformBroadcaster 自动处理）
    - 底层用 TRANSIENT_LOCAL QoS 保留这条消息，
      后启动的节点也能拿到（呼应 qos_demo.py 里讲的 Durability）
    - 如果你发现"RViz 里激光数据位置不对/没有显示"，
      八成是这条边的数值和实际安装位姿不符

【数据从哪来】

实际项目中这个变换通常由 robot_state_publisher 解析 URDF 自动发布
（见学习路线第 7 阶段）。这里手动写一遍是为了让你看清 TF 消息长什么样。

【怎么运行】

    ros2 run ros2_basics static_tf_broadcaster

    # 验证（另开终端）：
    ros2 run tf2_ros tf2_echo base_link laser
    ros2 run tf2_tools view_frames      # 生成 frames.pdf 看整棵树
"""

import rclpy
from rclpy.node import Node

# StaticTransformBroadcaster：静态变换广播器
# 普通的 TransformBroadcaster 需要你以固定频率反复发送；
# Static 版本只需发送一次，底层自动用 latched（TRANSIENT_LOCAL）方式保留。
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

# TF 消息本质上是 geometry_msgs/TransformStamped：
#   header.stamp        时间戳（这条变换从何时生效）
#   header.frame_id     父坐标系（这条边"从哪出发"）
#   child_frame_id      子坐标系（"指向谁"）
#   transform           平移 + 旋转（四元数）
from geometry_msgs.msg import TransformStamped


class StaticTFBroadcaster(Node):
    def __init__(self):
        super().__init__('static_tf_broadcaster')

        # ------------------------------------------------------------------
        # 也可以用参数化方式广播多个静态变换
        # ------------------------------------------------------------------
        # 参数格式（和 ros2 run tf2_ros static_transform_publisher 一致）：
        #   --x 0.2 --y 0 --z 0.15 --yaw 0 --frame-id base_link --child-frame-id laser
        self.declare_parameter('x', 0.20)     # 雷达装在车体前方 20cm
        self.declare_parameter('y', 0.0)      # 装在中轴线上
        self.declare_parameter('z', 0.15)     # 装在离 base_link 高 15cm 处
        self.declare_parameter('yaw', 0.0)    # 雷达正朝前（不旋转）

        x = self.get_parameter('x').get_parameter_value().double_value
        y = self.get_parameter('y').get_parameter_value().double_value
        z = self.get_parameter('z').get_parameter_value().double_value
        yaw = self.get_parameter('yaw').get_parameter_value().double_value

        # 创建静态广播器
        self.br = StaticTransformBroadcaster(self)

        # 构造变换消息
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_link'     # 父：机器人本体
        t.child_frame_id = 'laser'          # 子：雷达

        # 平移：直接填米制的 xyz
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z

        # 旋转：必须用四元数，不能用欧拉角直接填！
        #
        # 常见错误：把 yaw 度数/弧度直接塞进 rotation.z —— 那是完全不同的含义。
        # 绕单一轴旋转时，四元数和欧拉角的换算很简单：
        #   绕 z 轴转 yaw：  qz = sin(yaw/2), qw = cos(yaw/2)，qx = qy = 0
        #   绕 x 轴转 roll： qx = sin(roll/2), qw = cos(roll/2)
        #
        # 这里只有偏航 yaw，所以只填 z 和 w 两个分量。
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = __import__('math').sin(yaw / 2.0)
        t.transform.rotation.w = __import__('math').cos(yaw / 2.0)

        # 发送一次即可，StaticTransformBroadcaster 会一直保留它
        self.br.sendTransform(t)

        self.get_logger().info(
            f'静态变换已广播: base_link -> laser '
            f'(x={x}, y={y}, z={z}, yaw={yaw})')


def main(args=None):
    rclpy.init(args=args)
    node = StaticTFBroadcaster()
    try:
        # 虽然只发了一次，但节点要保持活着：
        # 退出进程后，这个静态变换就随 DDS 会话一起消失了。
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
