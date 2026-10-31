cmake_minimum_required(VERSION 3.8)
project(avl_bringup)
find_package(ament_cmake REQUIRED)
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/check_baseline.py
  scripts/check_commands.py
  scripts/spawn_sim_controllers.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
