# CMakeLists.txt —— 接口包的构建配置（练习 7）
#
# 接口包的 CMakeLists 都长这样，几乎不需要改：
# 核心就一件事：把 .msg/.srv/.action 交给 rosidl_generate_interfaces 去生成代码
cmake_minimum_required(VERSION 3.8)
project(ros2_basics_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

# 代码生成器
find_package(rosidl_default_generators REQUIRED)
# 用了 std_msgs/Header，生成器需要知道这个依赖
find_package(std_msgs REQUIRED)

# 列出所有接口文件。新增 .msg/.srv/.action 后在这里补一行，然后重新 colcon build
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotStatus.msg"
  "srv/ComputePath.srv"
  "action/DriveTo.action"
  DEPENDENCIES std_msgs   # RobotStatus.msg 里用了 std_msgs/Header
)

ament_package()
