# 自定义话题消息：机器人状态（练习 7）
#
# .msg 文件语法：每行一个字段，格式为「类型 字段名」
# 生成后的 Python 用法：msg.battery_voltage = 12.5
#
# 常用类型：
#   bool / int32 / int64 / float32 / float64 / string
#   float64[]        变长数组（如点云的坐标列表）
#   float64[9]       定长数组
#   string[<=5]      有上限的变长数组
#   std_msgs/Header  带时间戳和 frame_id 的标准头（强烈建议顶层消息都加）
#
# 对应导航场景：这就是 /odom、/battery_state 这类状态话题的自定义版本

# 时间戳 + 坐标系名，传感器/状态类消息的标准开头
std_msgs/Header header

float64 battery_voltage      # 电池电压（V），狗上一般 7.4V 双节锂电
float64 speed                # 当前线速度（m/s）
string current_task          # 当前任务描述，如 "navigating to node_2"
bool is_navigating           # 是否正在执行导航
int32[] waypoint_ids         # 剩余路网节点编号（演示变长数组用法）
