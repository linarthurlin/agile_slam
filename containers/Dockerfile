ARG BASE_IMAGE=agile_control_ros2:baseline-20261014
FROM ${BASE_IMAGE}
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-ros-gz \
    ros-humble-ign-ros2-control \
    ros-humble-ros2-controllers \
    ros-humble-ackermann-msgs \
    ros-humble-cv-bridge \
    ros-humble-joint-state-publisher \
    python3-colcon-common-extensions python3-pytest \
    libgl1-mesa-dri libegl1-mesa mesa-utils xvfb xauth \
    && rm -rf /var/lib/apt/lists/*
COPY ros2_ws/src /opt/agile_slam_ws/src
WORKDIR /opt/agile_slam_ws
RUN source /opt/ros/humble/setup.bash && \
    if [[ -f /workspace/ros_ws/install/setup.bash ]]; then source /workspace/ros_ws/install/setup.bash; fi && \
    colcon build --event-handlers console_direct+ && \
    mkdir -p /opt/agile_slam_metadata && \
    dpkg-query -W > /opt/agile_slam_metadata/packages.tsv
COPY config/dds/cyclonedds.xml /etc/agile_slam/cyclonedds.xml
COPY containers/entrypoint.sh /agile_slam_entrypoint.sh
RUN chmod +x /agile_slam_entrypoint.sh
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    CYCLONEDDS_URI=file:///etc/agile_slam/cyclonedds.xml \
    ROS_DOMAIN_ID=42 \
    ROS_LOG_DIR=/tmp/ros_logs
ENTRYPOINT ["/agile_slam_entrypoint.sh"]
CMD ["bash"]
