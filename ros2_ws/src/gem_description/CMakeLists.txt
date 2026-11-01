cmake_minimum_required(VERSION 3.8)

project(gem_description)

# Default to C99 and C++14
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)

# Install directories
install(DIRECTORY
  config
  launch
  urdf
  meshes
  rviz
  DESTINATION share/${PROJECT_NAME}
)

# Keep the repository-level nominal transform registry as the Xacro runtime source.
install(FILES
  ${CMAKE_CURRENT_SOURCE_DIR}/../../../config/e6/simulation_nominal_transforms.yaml
  DESTINATION share/${PROJECT_NAME}/config/e6
)

ament_package()
