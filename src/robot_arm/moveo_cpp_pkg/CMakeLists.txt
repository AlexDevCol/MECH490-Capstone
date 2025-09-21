cmake_minimum_required(VERSION 3.8)
project(moveo_cpp_pkg)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(control_msgs REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

add_executable(simple_moveit_interface src/simple_moveit_interface.cpp)
ament_target_dependencies(simple_moveit_interface 
  rclcpp 
  moveit_ros_planning_interface 
  geometry_msgs 
  std_msgs 
  sensor_msgs
  control_msgs
)

add_executable(position_moveit_interface src/position_moveit_interface.cpp)
ament_target_dependencies(position_moveit_interface
  rclcpp 
  moveit_ros_planning_interface 
  geometry_msgs 
  std_msgs 
  sensor_msgs
  control_msgs
)

add_executable(hello_moveit src/hello_moveit.cpp)
ament_target_dependencies(hello_moveit 
  rclcpp 
  moveit_ros_planning_interface 
  geometry_msgs 
  std_msgs 
  sensor_msgs
  control_msgs
)

install(TARGETS
  simple_moveit_interface
  position_moveit_interface
  hello_moveit
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
