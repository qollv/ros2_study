# -*- coding: utf-8 -*-
"""
==============================================================================
QoS（服务质量）演示 —— 亲眼看到「明明在发却收不到」
==============================================================================

【QoS 是什么】

ROS2 底层基于 DDS（数据分发服务），QoS 就是 DDS 层的"传输策略"。
ROS1 完全没有这个概念，所以从 ROS1 转过来的人经常在这里栽跟头。

发布者和订阅者建立连接时，会先协商 QoS。
**对不上就直接连不上**，而且不会报任何错误 ——
你只会看到订阅者的回调一次都没被调用，话题列表里却明明有这个话题。

【本演示做了什么】

一个节点里同时跑四组实验，跑完打印对比结果：

  1. /qos_match          发布 BEST_EFFORT  ←  订阅 BEST_EFFORT   -> 能收到
  2. /qos_mismatch       发布 BEST_EFFORT  ←  订阅 RELIABLE      -> 收不到（重点）
  3. /qos_late_local     发布 TRANSIENT_LOCAL（t=1s 发一次）
                         订阅 TRANSIENT_LOCAL（t=6s 才建立）      -> 能收到（补发）
  4. /qos_late_volatile  发布 VOLATILE（t=1s 发一次）
                         订阅 TRANSIENT_LOCAL（t=6s 才建立）      -> 收不到

【怎么运行】

    ros2 run ros2_basics qos_demo

    大约 11 秒后自动打印总结并退出。

【看完之后你应该记住的两条规则】

  可靠性 Reliability（不对称）：
      订阅 RELIABLE  ←  发布 BEST_EFFORT   = 不兼容（收不到）
      其余三种组合都兼容

  持久性 Durability（不对称）：
      订阅 TRANSIENT_LOCAL  ←  发布 VOLATILE       = 不兼容
      订阅 VOLATILE         ←  发布 TRANSIENT_LOCAL = 兼容（只是拿不到历史）

【实际排查技巧】

    ros2 topic info /scan --verbose      # 看这个话题上所有发布者/订阅者的 QoS

    rclpy 在 QoS 不匹配时其实会打警告，这是唯一的线索，但很容易被日志淹没：

        [WARN] [qos_demo]: New subscription discovered on topic 'qos_mismatch',
               requesting incompatible QoS. No messages will be sent to it.
               Last incompatible policy: RELIABILITY

    看到 "incompatible QoS" 就要立刻去查两边的 Reliability / Durability。

    RViz 里添加话题时，左侧有 QoS 设置下拉框。
    "RViz 里看不到激光 / 地图"十有八九是这里没选对：
        /scan      -> Best Effort
        /map       -> Reliable + Transient Local
        /tf_static -> Reliable + Transient Local

【运行时的噪音】

    可能会看到大量 "sequence size exceeds remaining buffer"。
    这是 FastDDS 底层的反序列化警告，与 QoS 演示无关，可忽略。
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import String


class QoSDemo(Node):
    def __init__(self):
        super().__init__('qos_demo')

        # 结束标志，供 main() 里的循环判断
        self.finished = False

        # ------------------------------------------------------------------
        # 构造两个对比用的 QoS 配置
        # ------------------------------------------------------------------
        # QoSProfile 有四个常用字段：
        #   history      KEEP_LAST / KEEP_ALL
        #   depth        配合 KEEP_LAST 的队列深度
        #   reliability  RELIABLE / BEST_EFFORT
        #   durability   VOLATILE / TRANSIENT_LOCAL
        #
        # 只写 depth 时，其余字段用 ROS2 默认值：
        #   reliability = RELIABLE, durability = VOLATILE, history = KEEP_LAST
        # 这就是很多人"没配 QoS 却出问题"的原因 —— 默认是 RELIABLE，
        # 而大多数传感器发布者用的是 BEST_EFFORT，于是连不上。

        # 尽力而为：丢了不重传。传感器数据的标准配置。
        self.qos_best_effort = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        # 可靠：丢包必重传，保证送达。控制指令、参数类数据用它。
        self.qos_reliable = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        # 持久本地：为"后加入的订阅者"保留最后一条消息。
        # 典型用途是 /map 和 /tf_static —— 它们只在启动时发一次，
        # 如果后启动的节点收不到，就永远拿不到地图/静态坐标变换了。
        self.qos_transient_local = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        # ------------------------------------------------------------------
        # 实验 1 & 2：可靠性对比（订阅方 QoS 不同，发布方都是 BEST_EFFORT）
        # ------------------------------------------------------------------
        # 计数器，用来最后对比
        self.match_count = 0
        self.mismatch_count = 0
        self.late_local_count = 0
        self.late_volatile_count = 0

        # 实验 1：发布 BEST_EFFORT，订阅也 BEST_EFFORT -> 兼容
        self.pub_match = self.create_publisher(String, 'qos_match', self.qos_best_effort)
        self.sub_match = self.create_subscription(
            String, 'qos_match', self.on_match, self.qos_best_effort)

        # 实验 2：发布 BEST_EFFORT，订阅却要求 RELIABLE -> 不兼容
        # 注意：创建订阅这行不会报错！QoS 不匹配是运行时才体现的，
        # 表现为回调永远不被调用。这正是它难排查的原因。
        self.pub_mismatch = self.create_publisher(String, 'qos_mismatch', self.qos_best_effort)
        self.sub_mismatch = self.create_subscription(
            String, 'qos_mismatch', self.on_mismatch, self.qos_reliable)

        # ------------------------------------------------------------------
        # 实验 3 & 4：持久性对比
        # ------------------------------------------------------------------
        # 这两个话题现在只发一次（t=1s），订阅者要到 t=6s 才创建，
        # 用来模拟"节点比发布者晚启动"的真实场景。
        self.pub_late_local = self.create_publisher(
            String, 'qos_late_local', self.qos_transient_local)
        self.pub_late_volatile = self.create_publisher(
            String, 'qos_late_volatile', self.qos_reliable)  # 默认 VOLATILE

        # t=1s：各发一条"历史消息"
        self.create_timer(1.0, self.publish_late_once)

        # t=6s：迟到 5 秒才建立订阅
        self.create_timer(6.0, self.create_late_subscriptions)

        # t=11s：打印总结并退出
        self.create_timer(11.0, self.print_summary)

        # 每 0.5 秒给实验 1、2 各发一条
        self.tick = 0
        self.create_timer(0.5, self.publish_periodic)

        self.get_logger().info('QoS 演示启动，约 11 秒后输出结论')

    # ----------------------------------------------------------------------
    # 定时发布
    # ----------------------------------------------------------------------
    def publish_periodic(self):
        self.tick += 1
        msg = String()
        msg.data = f'msg-{self.tick}'
        self.pub_match.publish(msg)
        self.pub_mismatch.publish(msg)

    def publish_late_once(self):
        """t=1s 发一次历史消息，之后订阅者才登场。"""
        # 这两个定时器是一次性的，触发后把自己销毁
        self._late_published = getattr(self, '_late_published', 0) + 1
        if self._late_published > 1:
            return

        m = String()
        m.data = '我在订阅者出现之前就发了'
        self.pub_late_local.publish(m)
        self.pub_late_volatile.publish(m)
        self.get_logger().info('[t=1s] 已发出"历史消息"（此时还没有订阅者）')

    # ----------------------------------------------------------------------
    # 迟到订阅
    # ----------------------------------------------------------------------
    def create_late_subscriptions(self):
        """t=6s 才建立订阅，此时历史消息早就发完了。"""
        if hasattr(self, '_late_sub_created'):
            return
        self._late_sub_created = True

        self.get_logger().info('[t=6s] 现在才创建订阅者')

        # 订阅方都要求 TRANSIENT_LOCAL（想要历史消息）
        latched = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        # 实验 3：发布方也是 TRANSIENT_LOCAL -> 兼容，能补收到历史消息
        self.create_subscription(
            String, 'qos_late_local', self.on_late_local, latched)

        # 实验 4：发布方是 VOLATILE -> 不兼容，历史消息永远拿不到
        self.create_subscription(
            String, 'qos_late_volatile', self.on_late_volatile, latched)

    # ----------------------------------------------------------------------
    # 回调：只计数，不打印，避免刷屏
    # ----------------------------------------------------------------------
    def on_match(self, msg):
        self.match_count += 1

    def on_mismatch(self, msg):
        self.mismatch_count += 1

    def on_late_local(self, msg):
        self.late_local_count += 1

    def on_late_volatile(self, msg):
        self.late_volatile_count += 1

    # ----------------------------------------------------------------------
    # 总结
    # ----------------------------------------------------------------------
    def print_summary(self):
        if hasattr(self, '_summary_printed'):
            return
        self._summary_printed = True

        line = '-' * 60
        self.get_logger().info(line)
        self.get_logger().info('QoS 实验结论')
        self.get_logger().info(line)
        self.get_logger().info(
            f'[1] BEST_EFFORT 发布 <- BEST_EFFORT 订阅  : 收到 {self.match_count:3d} 条   兼容')
        self.get_logger().info(
            f'[2] BEST_EFFORT 发布 <- RELIABLE    订阅  : 收到 {self.mismatch_count:3d} 条   '
            f'{"兼容" if self.mismatch_count else "不兼容（一条都没收到）"}')
        self.get_logger().info(
            f'[3] TRANSIENT_LOCAL 发布 <- TRANSIENT_LOCAL 订阅: 收到 {self.late_local_count:3d} 条   '
            f'{"补收到历史消息" if self.late_local_count else "没收到"}')
        self.get_logger().info(
            f'[4] VOLATILE 发布 <- TRANSIENT_LOCAL 订阅 : 收到 {self.late_volatile_count:3d} 条   '
            f'{"收到" if self.late_volatile_count else "不兼容（历史丢失）"}')
        self.get_logger().info(line)
        self.get_logger().info('记住：RELIABLE 订阅者连不上 BEST_EFFORT 发布者')
        self.get_logger().info(line)

        # 标记结束，让 main() 里的循环退出。
        #
        # 注意：不要在这里直接调 rclpy.shutdown()。
        # 在回调里关 context 是不可靠的（spinning 中的执行器状态未清理干净），
        # 实测会导致进程打印完总结却退不出去。
        # 正确做法是置标志位，回到 main() 的循环条件里退出。
        self.finished = True


def main(args=None):
    rclpy.init(args=args)
    node = QoSDemo()

    # 用 spin_once 循环而不是 spin()，这样才能通过标志位干净退出
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
