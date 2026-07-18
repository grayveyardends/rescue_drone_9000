#!/bin/bash
set -e
source /opt/ros/humble/setup.bash

# The repo is bind-mounted over /sar, hiding the workspace built into the image.
# Build the mounted workspace once (results persist on the host via the mount).
if [ -d /sar/ros2_ws/src ] && [ ! -f /sar/ros2_ws/install/setup.bash ]; then
    echo "[entrypoint] building /sar/ros2_ws (first run)..."
    (cd /sar/ros2_ws && colcon build --symlink-install)
fi
[ -f /sar/ros2_ws/install/setup.bash ] && source /sar/ros2_ws/install/setup.bash

export GAZEBO_MODEL_PATH=/ardupilot_gazebo/models:/sar/sim/models:$GAZEBO_MODEL_PATH
export GAZEBO_RESOURCE_PATH=/ardupilot_gazebo/worlds:/sar/sim/worlds:$GAZEBO_RESOURCE_PATH
# never hit the (dead) online model database
export GAZEBO_MODEL_DATABASE_URI=""

# single-host stack: keep DDS on loopback so wifi/VPN changes can't break ROS
export ROS_LOCALHOST_ONLY=1
exec "$@"
