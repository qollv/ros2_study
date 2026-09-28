# -*- coding: utf-8 -*-
"""
==============================================================================
参数（Parameter）示例 —— 演示声明、读取、运行时修改
==============================================================================

【Parameter 是什么】

节点内部的配置变量。和硬编码常量的区别在于：
    1. 可以在 launch 文件或 yaml 里预先配好
    2. 可以在节点运行时动态修改，不用重启
    3. 可以用 ros2 param 命令行查看和导出

【为什么这个对你特别重要】

你调的 xy_goal_tolerance = 0.15、yaw_goal_tolerance = 0.15，
本质上就是 Nav2 节点的 Parameter。

Nav2 的做法是：把几十上百个参数写在一个 yaml 文件里，launch 时加载：

    Node(
        package='nav2_bringup',
        executable='navigation_launch.py',
        parameters=[nav2_params_file]      # <- 就是这个 yaml
    )

理解了本例，你就能看懂 Nav2 那一大坨参数文件是怎么起作用的，
也就能自己写一份针对四足底盘调优的参数文件了。

【怎么运行】

    # 终端 1
    ros2 run ros2_basics param_demo

    # 终端 2（试试这些，观察终端 1 的日志变化）
    ros2 param list /param_demo
    ros2 param get /param_demo tolerance
    ros2 param set /param_demo tolerance 0.15       # 不重启，日志立刻变
    ros2 param set /param_demo robot_name 'dog2sw'
    ros2 param dump /param_demo --output-dir .      # 导出 yaml

    # 也可以启动时用命令行传参（注意 --ros-args 的用法）：
    ros2 run ros2_basics param_demo --ros-args -p tolerance:=0.15

【一个关键细节】

参数值在节点内部是「快照」还是「实时」？
取决于你怎么读：
    - 只在 __init__ 里读一次并存成 self.xxx  -> 之后 set 不生效
    - 每次用时重新 get_parameter()          -> 实时生效（本例做法）

很多 Nav2 参数之所以改了要重启才生效，就是因为它在初始化时
读了一次存成成员变量了。
"""

import rclpy
from rclpy.node import Node


class ParamDemo(Node):
    def __init__(self):
        super().__init__('param_demo')

        # ------------------------------------------------------------------
        # 声明参数
        # ------------------------------------------------------------------
        # declare_parameter(参数名, 默认值)
        #
        # 规则一：必须先 declare，才能 get。
        #         直接 get 一个未声明的参数会抛 ParameterNotDeclaredException。
        #
        # 规则二：默认值会被外部传入的值覆盖，优先级：
        #         命令行 --ros-args -p x:=1  >  launch 文件里的 parameters  >  这里的默认值
        #
        # 规则三：类型由默认值推断。这里分别是 string / double / double。
        #         如果 set 的时候类型不匹配（比如给 tolerance 传字符串），会报错。
        self.declare_parameter('robot_name', 'dog2')
        self.declare_parameter('tolerance', 0.25)
        self.declare_parameter('max_speed', 0.5)

        # 每 2 秒打印一次当前参数值
        self.timer = self.create_timer(2.0, self.on_timer)

        self.get_logger().info('参数节点已启动')

    def on_timer(self):
        """
        定时打印参数值。

        【重点】这里每次都重新调用 get_parameter()，
        所以外部用 ros2 param set 改了之后，日志里的值会立刻变。

        对比一下"错误"写法（改了不生效）：
            def __init__(self):
                self.tol = self.get_parameter('tolerance').value   # 只读一次
            def on_timer(self):
                print(self.tol)      # 永远是初始值，外部 set 无效

        实际项目中两种都有用：
            - 希望热更新（速度限制、容差）  -> 实时读
            - 启动后不应变（雷达端口、帧率）-> 读一次存起来
        """

        # 取字符串参数
        name = self.get_parameter('robot_name').get_parameter_value().string_value

        # 取浮点参数
        tol = self.get_parameter('tolerance').get_parameter_value().double_value
        spd = self.get_parameter('max_speed').get_parameter_value().double_value

        self.get_logger().info(f'{name}: tolerance={tol}, max_speed={spd}')

        # ------------------------------------------------------------------
        # 补充：常用类型对应的取值方法
        # ------------------------------------------------------------------
        #   .get_parameter_value().string_value     字符串
        #   .get_parameter_value().double_value     浮点
        #   .get_parameter_value().integer_value    整数
        #   .get_parameter_value().bool_value       布尔
        #   .get_parameter_value().string_array_value  字符串数组
        #
        # 更简洁的等价写法（Python 类型自动推断）：
        #   self.get_parameter('tolerance').value
        # 两种都可以，.value 更短但类型不明确，看个人习惯。


def main(args=None):
    rclpy.init(args=args)
    node = ParamDemo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
