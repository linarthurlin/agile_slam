ARG BASE_IMAGE=agile_control_ros2:baseline-20261014
FROM ${BASE_IMAGE} AS renderer-build
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates python3 dpkg-dev patch cmake make g++ \
    libogre-next-dev=2.2.5+dfsg3-0ubuntu2 \
    libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev \
    libfreeimage-dev libfreetype6-dev libzzip-dev libtinyxml-dev rapidjson-dev \
    libxrandr-dev libxaw7-dev libxt-dev libxxf86vm-dev libpoco-dev \
    && rm -rf /var/lib/apt/lists/*
COPY third_party/ogre_next.json /source/ogre_next.json
COPY third_party/patches /source/patches
COPY containers/build_renderer.py /source/build_renderer.py
RUN python3 /source/build_renderer.py

FROM ${BASE_IMAGE} AS runtime
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
COPY --from=renderer-build /renderer/RenderSystem_GL3Plus.so /usr/lib/x86_64-linux-gnu/OGRE-Next/RenderSystem_GL3Plus.so
COPY --from=renderer-build /renderer/provenance.json /opt/agile_slam_metadata/renderer.json
COPY --from=renderer-build /renderer/copyright /opt/agile_slam_metadata/renderer-copyright
RUN test "$(dpkg-query -W -f='${Version}' libogre-next-dev)" = '2.2.5+dfsg3-0ubuntu2'
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
