cmake_minimum_required(VERSION 3.8)
project(moveo_remote)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(moveo_interfaces REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(control_msgs REQUIRED)
find_package(action_msgs REQUIRED)

add_library(task_server SHARED src/task_server.cpp)
target_include_directories(task_server
  PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_compile_definitions(task_server
  PRIVATE
  "TASK_SEVER_CPP_BUILDING_DLL"
)
ament_target_dependencies(task_server
  "moveo_interfaces"
  "rclcpp" 
  "moveit_ros_planning_interface" 
  "geometry_msgs"
  "std_msgs"
  "sensor_msgs"
  "control_msgs"
  "action_msgs"
)
rclcpp_components_register_node(task_server
  PLUGIN "moveo_remote::TaskServer"
  EXECUTABLE task_server_node
)

install(TARGETS
  task_server
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib
)

install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
