# 
# Generate RTT subsystem ports from ROS .msg messages
#

cmake_minimum_required(VERSION 2.8.3)

macro(rtt_master_destinations)
  if(ORO_USE_ROSBUILD)
    #message(STATUS "[ros_generate_rtt_master] Generating ROS typekit for ${PROJECT_NAME} with ROSBuild destinations.")
    set(rtt_master_GENERATED_HEADERS_OUTPUT_DIRECTORY    "${PROJECT_SOURCE_DIR}/include")
    set(rtt_master_GENERATED_HEADERS_INSTALL_DESTINATION)
  elseif(ORO_USE_CATKIN)
    #message(STATUS "[ros_generate_rtt_master] Generating ROS typekit for ${PROJECT_NAME} with Catkin destinations.")
    catkin_destinations()
    set(rtt_master_GENERATED_HEADERS_OUTPUT_DIRECTORY    "${CATKIN_DEVEL_PREFIX}/include")
    set(rtt_master_GENERATED_HEADERS_INSTALL_DESTINATION "${CATKIN_GLOBAL_INCLUDE_DESTINATION}")
  else()
    #message(STATUS "[ros_generate_rtt_master] Generating ROS typekit for ${PROJECT_NAME} with normal CMake destinations.")
    set(rtt_master_GENERATED_HEADERS_OUTPUT_DIRECTORY    "${PROJECT_BINARY_DIR}/include")
    set(rtt_master_GENERATED_HEADERS_INSTALL_DESTINATION "${CMAKE_INSTALL_PREFIX}/include")
  endif()

  if(DEFINED ENV{VERBOSE_CONFIG})
    message(STATUS "[ros_generate_rtt_master]   Generating headers in: ${rtt_master_GENERATED_HEADERS_OUTPUT_DIRECTORY}")
    message(STATUS "[ros_generate_rtt_master]   Installing headers to: ${rtt_master_GENERATED_HEADERS_INSTALL_DESTINATION}")
  endif()
endmacro()

macro(msgs_from_ec_config_destinations)
  if(ORO_USE_ROSBUILD)
    #message(STATUS "[ros_generate_msgs_from_ec_config] Generating ROS typekit for ${PROJECT_NAME} with ROSBuild destinations.")
#    set(msgs_from_ec_config_GENERATED_MSGS_OUTPUT_DIRECTORY    "${PROJECT_SOURCE_DIR}/msg")
#    set(msgs_from_ec_config_GENERATED_MSGS_INSTALL_DESTINATION)

    set(msgs_from_ec_config_GENERATED_HEADERS_OUTPUT_DIRECTORY    "${PROJECT_SOURCE_DIR}/include")
    set(msgs_from_ec_config_GENERATED_HEADERS_INSTALL_DESTINATION)
  elseif(ORO_USE_CATKIN)
    #message(STATUS "[ros_generate_msgs_from_ec_config] Generating ROS typekit for ${PROJECT_NAME} with Catkin destinations.")
    catkin_destinations()
#    set(msgs_from_ec_config_GENERATED_MSGS_OUTPUT_DIRECTORY    "${CATKIN_DEVEL_PREFIX}/msg")
#    set(msgs_from_ec_config_GENERATED_MSGS_INSTALL_DESTINATION "${CATKIN_PACKAGE_SHARE_DESTINATION}/msg")

    set(msgs_from_ec_config_GENERATED_HEADERS_OUTPUT_DIRECTORY    "${CATKIN_DEVEL_PREFIX}/include")
    set(msgs_from_ec_config_GENERATED_HEADERS_INSTALL_DESTINATION "${CATKIN_GLOBAL_INCLUDE_DESTINATION}")
  else()
    #message(STATUS "[ros_generate_msgs_from_ec_config] Generating ROS typekit for ${PROJECT_NAME} with normal CMake destinations.")
#    set(msgs_from_ec_config_GENERATED_MSGS_OUTPUT_DIRECTORY    "${PROJECT_BINARY_DIR}/msg")
#    set(msgs_from_ec_config_GENERATED_MSGS_INSTALL_DESTINATION "${CATKIN_PACKAGE_SHARE_DESTINATION}/msg")

    set(msgs_from_ec_config_GENERATED_HEADERS_OUTPUT_DIRECTORY    "${PROJECT_BINARY_DIR}/include")
    set(msgs_from_ec_config_GENERATED_HEADERS_INSTALL_DESTINATION "${CMAKE_INSTALL_PREFIX}/include")
  endif()

#  if(DEFINED ENV{VERBOSE_CONFIG})
#    message(STATUS "[ros_generate_msgs_from_ec_config]   Generating headers in: ${msgs_from_ec_config_GENERATED_HEADERS_OUTPUT_DIRECTORY}")
#    message(STATUS "[ros_generate_msgs_from_ec_config]   Installing headers to: ${msgs_from_ec_config_GENERATED_HEADERS_INSTALL_DESTINATION}")
#  endif()
endmacro()

macro(ros_generate_rtt_master)
  set(_package ${PROJECT_NAME})
  add_subdirectory(${rtt_subsystem_DIR}/../src/templates/master ${PROJECT_NAME}_master)
  include_directories(${PROPAGATED_UP_INCLUDE_DIRECTORIES})
endmacro(ros_generate_rtt_master)

