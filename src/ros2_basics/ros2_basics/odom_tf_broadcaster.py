# -*- coding: utf-8 -*-
"""
==============================================================================
动态 TF 广播器 —— 模拟里程计，持续广播 odom -> base_link
==============================================================================

【这条边在真实系统里是谁发的】

odom -> base_link 由"里程计"提供，来源可能是：
    - 轮式编码器（四轮小车）
    - IMU + 编码器融合后的 EKF 输出（robot_localization 包）
    - 四足/腿式的关节状态估计

它的特点：**短时间内平滑连续，但会漂移**——走 10 米可能偏差 0.5 米。
所以才会有上面那条 map -> odom 边：定位节点（AMCL/Cartographer）
负责不断修正"里程计原点相对地图偏了多少"。

这就是为什么 TF 树要拆成 map 和 odom 两层，而不是合成一个：
    map -> odom 的跳变代表"定位修正"，不能让控制器直接看见
    odom -> base_link 平滑连续，控制器（Nav2 的 DWB/MPPI）在这层做控制

【本节点做什么】

让 base_link 绕一个半径 r 的圆匀速转圈：
    x(t) = r·cos(wt),  y(t) = r·sin(wt),  朝向 = 沿圆周切线
这样你在 tf2_echo 里能看到数字持续变化，直观感受"动态 TF"。

【怎么运行】

    # 单独跑（此时树不完整，查 base_link -> laser 会失败，正好演示报错）
    ros2 run ros2_basics odom_tf_broadcaster

    # 推荐：用 launch 把三个节点一起拉起来
    ros2 launch ros2_basics tf_demo_launch.py
"""

import math

import rclpy
from rclpy.node import Node

# TransformBroadcaster：动态变换广播器，和 Static 版本不同，
# 它需要你按固定频率（一般 20~50Hz）持续发送。
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class OdomTFBroadcaster(Node):
    def __init__(self):
        super().__init__('odom_tf_broadcaster')

        # 转圈半径（米）和角速度（弧度/秒），可从命令行覆盖：
        #   ros2 run ros2_basics odom_tf_broadcaster --ros-args -p radius:=0.5 -p speed:=1.0
        self.declare_parameter('radius', 1.0)
        self.declare_parameter('speed', 0.5)

        # 广播器
        self.br = TransformBroadcaster(self)

        # 仿真时间计数器
        self.t = 0.0

        # 20Hz 广播。频率选多少？
        #   太低（<10Hz）：控制器查 TF 时会用到过期数据，机器人抖动
        #   太高（>50Hz）：浪费 CPU，没有必要
        # Nav2 一般要求 >=20Hz。这在你调机器狗时也是个需要核对的点。
        self.timer = self.create_timer(0.05, self.on_timer)  # 0.05s = 20Hz

        r = self.get_parameter('radius').get_parameter_value().double_value
        w = self.get_parameter('speed').get_parameter_value().double_value
        self.get_logger().info(
            f'开始广播 odom -> base_link，半径 {r}m，角速度 {w}rad/s（20Hz）')

    def on_timer(self):
        r = self.get_parameter('radius').get_parameter_value().double_value
        w = self.get_parameter('speed').get_parameter_value().double_value

        # 推进仿真时间
        self.t += 0.05

        # 圆周运动的位置
        x = r * math.cos(w * self.t)
        y = r * math.sin(w * self.t)

        # 朝向：让机器人面向运动方向（圆周切线方向 = 圆心角 + 90°）
        yaw = w * self.t + math.pi / 2.0

        # ------------------------------------------------------------------
        # 构造 TF 消息
        # ------------------------------------------------------------------
        msg = TransformStamped()

        # 【重要】时间戳必须尽量用"当前时刻"。
        # TF 内部按时间排序存储变换，查询时按时间匹配。
        # 如果这里填 0 或者乱填，查询端就会报 ExtrapolationException。
        msg.header.stamp = self.get_clock().now().to_msg()

        # 父坐标系在前，子坐标系在后。方向别搞反：
        # 这条消息的含义是「base_link 的原点在 odom 坐标系里的位姿是 x,y,yaw」
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'

        # 平移
        msg.transform.translation.x = x
        msg.transform.translation.y = y
        msg.transform.translation.z = 0.0

        # 旋转 -> 四元数（只绕 z 轴，公式见 static_tf_broadcaster.py 的注释）
        msg.transform.rotation.x = 0.0
        msg.transform.rotation.y = 0.0
        msg.transform.rotation.z = math.sin(yaw / 2.0)
        msg.transform.rotation.w = math.cos(yaw / 2.0)

        # 发送。一次调用广播一条边；如果节点要维护多条边（比如还发 odom->foot），
        # 就在一个回调里连续 sendTransform 多次。
        self.br.sendTransform(msg)


def main(args=None):
    rclpy.init(args=args)
    node = OdomTFBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
