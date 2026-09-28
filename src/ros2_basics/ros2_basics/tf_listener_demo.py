# -*- coding: utf-8 -*-
"""
==============================================================================
TF 监听与查询 —— 演示 lookup_transform 的正确用法和三种典型报错
==============================================================================

【TF 的使用模式】

TF 分两半：
    广播端（前两个例子）：负责"发布"某条边
    监听端（本例）：订阅 /tf 和 /tf_static，把全网所有变换缓存在本地
                    （Buffer），然后随时查询任意两个坐标系的关系

监听端的标准三件套：
    buffer = Buffer()
    listener = TransformListener(buffer, self)   # 自动订阅并存入 buffer
    tf = buffer.lookup_transform(target, source, time)

注意 listener 只是往 buffer 里塞数据，真正干活的是 buffer。
查询永远查 buffer，而 buffer 里的数据来自后台订阅 ——
所以节点必须持续 spin，buffer 才有数据。

【lookup_transform 的语义（最容易搞反的地方）】

    lookup_transform(target_frame, source_frame, time)

返回：source 坐标系在 target 坐标系下的位姿
      （把 source 的点变换到 target 里怎么变）

例：lookup_transform('odom', 'laser', Time())
    = 「laser 坐标系在 odom 里处于什么位置和朝向」

【time 参数的三种用法】

    Time()                    -> 最新可用的变换（最常用，安全）
    node.get_clock().now()    -> "现在"的变换 —— 经常报错！因为最新的
                                 TF 消息时间戳总是略早于 now，查"未来"会失败
    某个具体时间戳             -> 查那一时刻的变换（用于把旧点云配到新位姿）

【怎么运行】

    # 必须先把广播端跑起来，否则查询失败
    ros2 launch ros2_basics tf_demo_launch.py

    # 本例已在 launch 里，也可以单独跑：
    ros2 run ros2_basics tf_listener_demo

    # 命令行等价版：
    ros2 run tf2_ros tf2_echo odom laser
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time

# Buffer：TF 数据的本地缓存（查询用它）
# TransformListener：订阅 /tf、/tf_static 并写入 buffer
from tf2_ros import Buffer, TransformListener

# 三种最常见的查询异常，排查 TF 问题时天天见：
from tf2_ros import (
    LookupException,           # 树上根本不存在这条边（比如断了一个节点）
    ConnectivityException,     # 两个坐标系在树上不连通（树断了）
    ExtrapolationException,    # 时间对不上（查了未来/太久的过去）
)

from geometry_msgs.msg import TransformStamped


class TFListenerDemo(Node):
    def __init__(self):
        super().__init__('tf_listener_demo')

        # ------------------------------------------------------------------
        # 三件套之一和之二：Buffer + Listener
        # ------------------------------------------------------------------
        # cache_time：buffer 保存多长时间的历史变换，默认 10 秒。
        # 如果你需要做"把 5 秒前的点云配到当前位姿"这类事，要加大它。
        self.buffer = Buffer(cache_time=Duration(seconds=10.0))
        self.listener = TransformListener(self.buffer, self)

        self.future_demo_done = False

        # 1Hz 定时查询
        self.timer = self.create_timer(1.0, self.on_timer)
        self.get_logger().info('TF 监听节点启动，每秒查询 odom -> laser')

    def on_timer(self):
        # ------------------------------------------------------------------
        # 查询 1：最新可用变换（最常用、最安全的写法）
        # ------------------------------------------------------------------
        try:
            # Time() 无参数 = 0 = 「给我这条边上最新的变换」
            # 内部会自动在树上找 odom 到 laser 的路径：
            #   odom -> base_link（动态） + base_link -> laser（静态）
            # 两段拼接成一条变换返回 —— 这就是 TF 树的意义：
            # 你不需要知道中间经过哪些边，直接查首尾即可。
            tf = self.buffer.lookup_transform('odom', 'laser', Time())

            pos = tf.transform.translation
            rot = tf.transform.rotation

            # 四元数转 yaw（只绕 z 轴的情况）：yaw = atan2(2(qw·qz), 1-2qz²)
            yaw = math.atan2(2.0 * (rot.w * rot.z), 1.0 - 2.0 * rot.z * rot.z)

            self.get_logger().info(
                f'laser 在 odom 中的位姿: x={pos.x:+.3f} y={pos.y:+.3f} '
                f'z={pos.z:+.3f} yaw={yaw:+.3f} rad')

        except LookupException:
            # 树上没有这两个坐标系之一。
            # 排查：ros2 run tf2_tools view_frames 看树全不全
            self.get_logger().warn(
                '查询失败(LookupException)：树上不存在 odom 或 laser，'
                '广播端没起来？')
        except ConnectivityException:
            # 两个坐标系都有，但中间断了边。
            # 排查：view_frames 的图里找断点（比如 base_link 没人广播）
            self.get_logger().warn(
                '查询失败(ConnectivityException)：两个坐标系不连通，树断了')
        except ExtrapolationException:
            # 时间戳对不上。常见原因：
            #   1. 广播频率太低，查的时刻超出了数据范围
            #   2. use_sim_time 不一致（一边用仿真时间一边用墙上时间）
            #   3. 多机之间时钟不同步
            self.get_logger().warn(
                '查询失败(ExtrapolationException)：时间越界，检查时间戳')

        # ------------------------------------------------------------------
        # 查询 2（只演示一次）：故意查"未来"，看典型报错
        # ------------------------------------------------------------------
        if not self.future_demo_done:
            self.future_demo_done = True
            try:
                # 用当前时刻查询 —— 看似合理，实际经常失败：
                # 因为最新一条 TF 消息的时间戳必然 <= now，
                # 查 now 相当于向未来外推了一点点。
                self.buffer.lookup_transform(
                    'odom', 'laser', self.get_clock().now())
                self.get_logger().info('用 now() 查询成功（这次运气好，时序刚好对上）')
            except ExtrapolationException:
                # 这就是为什么代码里应该用 Time() 而不是 now()
                self.get_logger().warn(
                    '用 now() 查询失败(ExtrapolationException) —— '
                    '这就是「查未来」的经典报错，记住要用 Time() 查最新')

        # ------------------------------------------------------------------
        # 查询 3（只演示一次）：带超时等待 —— 适合启动阶段
        # ------------------------------------------------------------------
        if not hasattr(self, '_wait_demo_done'):
            self._wait_demo_done = True
            try:
                # can_transform / lookup 带 timeout 参数时，会阻塞等待
                # 数据到达（最多等这么久），适合"刚启动、TF 还没就绪"的场景
                ok = self.buffer.can_transform(
                    'odom', 'laser', Time(),
                    timeout=Duration(seconds=2.0))
                self.get_logger().info(
                    f'can_transform(等待2秒) = {ok} —— '
                    f'{"树已连通" if ok else "2秒内没等到，树不完整"}')
            except Exception as e:
                self.get_logger().warn(f'can_transform 异常: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = TFListenerDemo()
    try:
        # 必须 spin，listener 才能把数据灌进 buffer
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
