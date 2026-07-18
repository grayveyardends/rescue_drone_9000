# SAR Drone stack: ROS 2 Humble + Gazebo 11 + ArduPilot SITL + MAVROS + rosbridge
FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

# ---------- system + ROS packages ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    gazebo libgazebo-dev \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-mavros ros-humble-mavros-extras ros-humble-mavros-msgs \
    ros-humble-rosbridge-server \
    ros-humble-cv-bridge ros-humble-image-transport \
    ros-humble-rmw-cyclonedds-cpp \
    git wget curl ccache rapidjson-dev \
    python3-pip python3-dev g++ make cmake \
    && rm -rf /var/lib/apt/lists/*

# MAVROS needs geographiclib datasets
RUN /opt/ros/humble/lib/mavros/install_geographiclib_datasets.sh

# ---------- ArduPilot SITL (built from source) ----------
RUN git clone --depth 1 --recurse-submodules --shallow-submodules \
    https://github.com/ArduPilot/ardupilot.git /ardupilot

RUN pip3 install --no-cache-dir --retries 15 --timeout 120 \
    pymavlink MAVProxy empy==3.3.4 pexpect future dronecan \
    pyserial geocoder requests numpy opencv-python-headless \
    fastapi "uvicorn[standard]" python-multipart websockets roslibpy pillow

RUN cd /ardupilot && ./waf configure --board sitl && ./waf copter

ENV PATH=$PATH:/ardupilot/Tools/autotest:/ardupilot/build/sitl/bin

# ---------- ardupilot_gazebo plugin (Gazebo Classic 11) ----------
RUN for i in 1 2 3 4 5 6; do \
        git clone --depth 1 https://github.com/khancyr/ardupilot_gazebo /ardupilot_gazebo && break; \
        echo "clone failed, retry $i"; rm -rf /ardupilot_gazebo; sleep 15; \
    done \
    && test -d /ardupilot_gazebo \
    && cd /ardupilot_gazebo && mkdir build && cd build \
    && cmake .. && make -j"$(nproc)" && make install

ENV GAZEBO_MODEL_PATH=/ardupilot_gazebo/models:/sar/sim/models
ENV GAZEBO_RESOURCE_PATH=/ardupilot_gazebo/worlds:/sar/sim/worlds:/usr/share/gazebo-11
ENV GAZEBO_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/gazebo-11/plugins

# ---------- SAR workspace ----------
WORKDIR /sar
COPY ros2_ws /sar/ros2_ws
RUN source /opt/ros/humble/setup.bash \
    && cd /sar/ros2_ws \
    && colcon build --symlink-install || colcon build

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
