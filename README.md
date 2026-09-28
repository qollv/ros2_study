# ROS2 基础练习工作区（Humble）

本机已装 ROS2 Humble（`/opt/ros/humble`），这个包已经编译并冒烟测试通过，直接照着跑就行。

---

## 0. 每次开新终端都要先 source

```bash
cd ~/WorkBuddy/2026-09-28-15-48-09/ros2_basics_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

嫌麻烦就写进 `~/.bashrc`：

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/WorkBuddy/2026-09-28-15-48-09/ros2_basics_ws/install/setup.bash" >> ~/.bashrc
```

重新编译（改完 Python 代码后）：

```bash
colcon build --packages-select ros2_basics
source install/setup.bash
```

> 注意：改 Python 代码**必须重新 build**，因为 ament_python 是把代码拷贝到 install 目录的。

---

## 1. 概念速记

| 机制 | 特点 | 什么时候用 | 导航里的真实例子 |
|---|---|---|---|
| **Topic** | 异步、单向、可多对多 | 持续不断的数据流 | `/scan` `/odom` `/cmd_vel` `/map` |
| **Service** | 同步、一问一答、会阻塞 | 要做一件事并立刻要结果 | `/clear_costmaps` `/reinitialize_global_localization` |
| **Action** | 异步、有进度反馈、可取消 | 耗时长的任务 | `NavigateToPose`（你的导航就是它） |
| **Parameter** | 节点内的配置变量 | 需要在 yaml 里配、运行时能改 | `xy_goal_tolerance` `robot_radius` `max_vel_x` |

一句话记忆：**流式数据用 Topic，问一句答一句用 Service，跑很久要进度的用 Action，调数值用 Parameter。**

---

## 2. 动手练习（按顺序做）

### 练习 1：Topic — 发布与订阅

```bash
ros2 launch ros2_basics demo_launch.py rate:=2.0
```

应该看到 talker 发、listener 收，成对出现。改个频率试试：

```bash
ros2 launch ros2_basics demo_launch.py rate:=5.0
```

再开一个终端，用命令行工具观察同一件事：

```bash
ros2 node list                  # 有哪些节点在跑
ros2 topic list                 # 有哪些话题
ros2 topic echo /chatter        # 直接看消息内容
ros2 topic hz /chatter          # 实际发布频率是多少（验证 rate 参数生效）
ros2 topic info /chatter        # 谁在发、谁在收
ros2 node info /talker          # 这个节点的全部输入输出
```

**验收**：能说出 `ros2 topic hz` 显示的数字为什么和 `rate` 一致。

### 练习 2：Parameter — 运行时改配置

```bash
ros2 run ros2_basics param_demo
```

另开终端：

```bash
ros2 param list /param_demo
ros2 param get /param_demo tolerance
ros2 param set /param_demo tolerance 0.15     # 不用重启，日志立刻变
ros2 param dump /param_demo --output-dir .    # 导出成 yaml
```

**验收**：`set` 之后节点日志里的数字马上变了，并且你拿到了一份 yaml——这就是 Nav2 参数文件的雏形。

### 练习 3：Service — 一问一答

```bash
# 终端 1
ros2 run ros2_basics service_server
# 终端 2
ros2 run ros2_basics service_client 3 5
```

也能用命令行调（不需要客户端代码）：

```bash
ros2 service list
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 10, b: 20}"
```

**验收**：理解为什么客户端要 `wait_for_service`，以及为什么不能在定时器回调里调同步 Service。

### 练习 4：Action — 目标 / 反馈 / 结果 / 取消

```bash
# 终端 1
ros2 run ros2_basics action_server
# 终端 2
ros2 run ros2_basics action_client 5
```

观察：客户端每收到一次 feedback 就打印一次，最后拿 result。这就是 NavigateToPose 的完整形态。

命令行版：

```bash
ros2 action list
ros2 action info /fibonacci
ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 5}" --feedback
```

试试取消（另开终端，在任务执行中发）：

```bash
ros2 action cancel /fibonacci
```

**验收**：能解释 Action 比 Service 多了哪三样东西（反馈、取消、异步）。

### 练习 5：QoS —— 为什么"明明在发却收不到"

一条命令看完全部四组对比实验：

```bash
ros2 run ros2_basics qos_demo     # 约 11 秒后自动打印结论并退出
```

实测输出：

| 实验 | 组合 | 结果 |
|---|---|---|
| 1 | BEST_EFFORT 发布 ← BEST_EFFORT 订阅 | 收到 21 条 ✅ |
| 2 | BEST_EFFORT 发布 ← **RELIABLE** 订阅 | 收到 **0 条** ❌ |
| 3 | TRANSIENT_LOCAL 发布 ← TRANSIENT_LOCAL 订阅（晚 5 秒） | 收到 1 条，补到了历史 ✅ |
| 4 | VOLATILE 发布 ← TRANSIENT_LOCAL 订阅（晚 5 秒） | 收到 **0 条** ❌ |

**核心规则（不对称）**：

```
可靠性：RELIABLE 订阅 ← BEST_EFFORT 发布  = 不兼容
持久性：TRANSIENT_LOCAL 订阅 ← VOLATILE 发布 = 不兼容
```

**唯一的排查线索** —— rclpy 会打这个警告，但很容易被日志淹没：

```
[WARN] New subscription discovered on topic 'xxx',
       requesting incompatible QoS. No messages will be sent to it.
       Last incompatible policy: RELIABILITY
```

**查看某个话题的 QoS**：

```bash
ros2 topic info /scan --verbose
```

**导航里的典型配置**：

| 话题 | Reliability | Durability | 为什么 |
|---|---|---|---|
| `/scan` `/odom` `/imu` | BEST_EFFORT | VOLATILE | 只要最新帧，丢一帧无所谓 |
| `/map` | RELIABLE | **TRANSIENT_LOCAL** | 只发一次，后启动的节点必须能拿到 |
| `/tf_static` | RELIABLE | **TRANSIENT_LOCAL** | 静态变换只广播一次，同理 |
| `/tf` | RELIABLE | VOLATILE | 高频动态，不需要历史 |
| `/cmd_vel` | RELIABLE | VOLATILE | 指令不能丢 |
| `/goal_pose`（RViz 下发） | RELIABLE | VOLATILE | 目标点必须送到 |

**RViz 里的坑**：添加话题时左侧有 QoS 下拉框。
"RViz 看不到激光/地图" 十有八九是这里没选对（`/scan` 选 Best Effort，`/map` 选 Reliable + Transient Local）。

**验收**：看到 `incompatible QoS` 警告能立刻反应过来去查 Reliability 和 Durability。

### 练习 6：TF 坐标系 —— 导航系统的骨架

一条命令拉起一棵完整的 TF 树（odom → base_link → laser）：

```bash
ros2 launch ros2_basics tf_demo_launch.py
ros2 launch ros2_basics tf_demo_launch.py radius:=0.5 speed:=1.0   # 改轨迹
```

里面有三个节点：

| 节点 | 广播的边 | 类型 |
|---|---|---|
| `odom_tf_broadcaster` | odom → base_link | 动态，20Hz，模拟里程计让机器人绕圆 |
| `static_tf_broadcaster` | base_link → laser | 静态，雷达安装位姿（0.2, 0, 0.15） |
| `tf_listener_demo` | 只查询不广播 | 每秒查 odom → laser 并打印 |

实测输出（base_link 在半径 1m 的圆上转，laser 恒定高 0.15m）：

```
laser 在 odom 中的位姿: x=+0.782 y=+0.655 z=+0.150 yaw=+2.071 rad
laser 在 odom 中的位姿: x=+0.372 y=+0.950 z=+0.150 yaw=+2.571 rad
...
用 now() 查询失败(ExtrapolationException) —— 这就是「查未来」的经典报错
can_transform(等待2秒) = 1 —— 树已连通
```

另开终端做这些观察：

```bash
ros2 run tf2_ros tf2_echo odom laser     # 命令行版查询，实时刷新
ros2 topic echo /tf --once               # 看动态 TF 消息长什么样
ros2 topic echo /tf_static --once        # 静态 TF 只在这里，只发一次
ros2 run tf2_ros tf2_monitor             # 各条边的广播频率（核对 20Hz）
```

**三个必须掌握的点**：

1. **`lookup_transform(target, source, time)` 返回的是 source 在 target 下的位姿**，参数顺序别背反了；
2. **time 参数用 `Time()` 查最新，不要用 `now()`** —— `now()` 必然比最新 TF 消息的时间戳晚一点，会报 `ExtrapolationException`（本例实测复现了这个报错）；
3. **三种异常对应三种故障**：`LookupException`=坐标系不存在、`ConnectivityException`=树断了、`ExtrapolationException`=时间越界。真机定位飘时按这个顺序排查。

> 注：`view_frames` 生成的文件带时间戳，名字形如
> `frames_2026-09-28_18.21.15.pdf`（不是固定的 frames.pdf，别找不到就以为没生成）。

**验收**：能画出你机器狗的 TF 树（有几个 frame、每条边谁广播、频率多少），并能解释 map 和 odom 为什么要分成两层。

### 练习 7：自定义接口 —— .msg / .srv / .action

接口定义在独立包 `ros2_basics_interfaces`（**接口必须用 ament_cmake 包，Humble 下 Python 包不能生成接口**）：

```
src/ros2_basics_interfaces/
├── msg/RobotStatus.msg     话题消息：机器人状态（含 Header 和变长数组）
├── srv/ComputePath.srv     服务：起终点 -> 距离（用 --- 分隔请求/响应）
└── action/DriveTo.action   动作：目标/结果/反馈（用两个 --- 分三段）
```

三个演示：

```bash
# 1. 自定义话题消息
ros2 run ros2_basics status_publisher
ros2 topic echo /robot_status          # 另一终端

# 2. 自定义服务（服务端 + 命令行客户端，不用写客户端代码）
ros2 run ros2_basics path_server
ros2 service call /compute_path ros2_basics_interfaces/srv/ComputePath \
    "{start_x: 0.0, start_y: 0.0, goal_x: 3.0, goal_y: 4.0}"
# 实测返回：distance=5.0（勾股定理 3-4-5）

# 3. 自定义动作（你自己版本的 NavigateToPose）
ros2 run ros2_basics drive_to_server
ros2 run ros2_basics drive_to_client 3 4
# 实测：剩余距离从 4.80 米逐格递减，进入 0.10m 容差圈返回 reached=true
```

**必须记住的四点**：

1. **接口包和功能包是分开的**：接口放 `*_interfaces`（CMake 包），节点放 Python 包。Nav2 的接口就在 `nav2_msgs` 包里；
2. **改了 .msg/.srv/.action 必须重新 colcon build**，且依赖它的包也要重编（先编接口包，再编功能包）；
3. **导入路径有规律**：`.msg -> 包名.msg`、`.srv -> 包名.srv`、`.action -> 包名.action`；
4. **srv 用 `---` 分两段、action 用两个 `---` 分三段**，段错位置编译时报的字段错误很难看懂。

> 本机坑（已踩）：直接 `colcon build` 编接口包报 `No module named 'em'`。
> 原因：PATH 里 python3 是 WorkBuddy 托管的 3.13，ROS Humble 需要系统 3.10。
> 解决：编译命令加前缀 `PATH=/usr/bin:$PATH colcon build`。

---

## 3. 必会命令速查

```bash
# 环境
source /opt/ros/humble/setup.bash

# 包
ros2 pkg create --build-type ament_python <包名>
ros2 pkg list
ros2 pkg executables ros2_basics

# 节点 / 话题
ros2 node list / info <节点>
ros2 topic list / echo <话题> / hz <话题> / bw <话题> / info <话题>
ros2 topic pub /chatter std_msgs/msg/String "{data: 'hi'}"     # 命令行手动发

# 服务 / 动作
ros2 service list / call <服务> <类型> "{字段: 值}"
ros2 action list / info <动作> / send_goal <动作> <类型> "{...}" --feedback

# 参数
ros2 param list / get <节点> <参数> / set <节点> <参数> <值> / dump <节点>

# 可视化
rqt_graph            # 看节点和话题的连线图，遇到"数据没通"先看这个
ros2 run tf2_tools view_frames   # 导出 TF 树为 pdf，导航必备

# 录制回放（真机调试神器）
ros2 bag record /scan /odom /tf
ros2 bag play <目录>
```

---

## 4. 学习顺序建议（按你的情况裁剪）

| 阶段 | 内容 | 你的情况 |
|---|---|---|
| 1 | 工作空间 / 包 / colcon | 已会，跳过 |
| 2 | **Topic + 命令行工具** | 已会，但建议补 `rqt_graph` 和 `ros2 topic hz` |
| 3 | **Parameter + yaml** | **重点补** —— Nav2 调参全靠它 |
| 4 | Service / Action | **重点补** —— Action 是 NavigateToPose 的地基 |
| 5 | Launch 文件 | 已会，看一眼 `launch/demo_launch.py` 即可 |
| 6 | **QoS** | 练习 5，ROS1 转过来的必补 |
| 7 | **TF 坐标系** | 练习 6，导航系统骨架，已完成示例 |
| 8 | URDF / robot_state_publisher | 真机和仿真都要用到（下一课） |

---

## 5. 下一步

基础打完后来这套：

```bash
ros2 run tf2_tools view_frames      # 先把 TF 树搞明白
```

然后进仿真阶段（Gazebo + 小车 + SLAM 建图 + Nav2 导航），那部分另外搭。

---

## 6. 真实踩坑记录（这个包里实际遇到并修掉的）

### 坑 1：节点方法名不能叫 `handle`

**现象**：`ros2 run ros2_basics service_server` 启动时报

```
File ".../rclpy/node.py", line 194, in __init__
    with self.handle:
AttributeError: __enter__
```

报错指向 rclpy 内部，看起来像 ROS2 装坏了，实际是自己的代码问题。

**原因**：`rclpy.node.Node` 基类**自带一个名为 `handle` 的属性**（底层 `rcl_node_t` 句柄）。
如果在子类里定义了一个叫 `handle` 的方法，它会覆盖基类属性，
于是 `Node.__init__` 内部执行 `with self.handle:` 时拿到的是你的方法对象（没有 `__enter__`），直接崩。

**解决**：回调方法改名，比如 `add_callback`（见 `service_server.py`）。

**延伸**：给节点类起方法名 / 成员变量名时，避开 `Node` 已有的成员：

```
handle / name / namespace / logger / executor / context / clock / subscriptions / publishers
```

**排查思路**（值得记住）：同样的 `Node` 类，内联定义的子类能创建成功、
从文件里 import 的子类失败 —— 说明问题出在子类自身的定义上，而不是环境。

### 坑 2：改了 Python 代码没重新 build

ament_python 包是把源码**拷贝**到 `install/` 目录运行的，
改完 `src/` 里的 `.py` 必须重新 `colcon build`，否则运行的还是旧版本。

```bash
colcon build --packages-select ros2_basics
source install/setup.bash
```

### 坑 3：launch 文件没加进 `setup.py`

`data_files` 里必须显式列出 `launch/*.py`，否则 `ros2 launch` 找不到文件。

### 坑 4：非交互终端里 `ros2` 命令报 Python 错误

`ros2` 不在默认 PATH 的完整环境下会报 `load_entry_point` 相关异常。
每个新终端先执行：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

