"""Mission bridge: JSON commands on /sar/command -> MAVROS calls.

Accepted commands (std_msgs/String, JSON payload):
  {"cmd": "arm"} | {"cmd": "disarm"}
  {"cmd": "mode", "mode": "GUIDED"}
  {"cmd": "takeoff", "alt": 15}
  {"cmd": "goto", "lat": 9.93, "lon": 76.26, "alt": 20}
  {"cmd": "rtl"} | {"cmd": "land"}
  {"cmd": "search_pattern", "lat": .., "lon": .., "radius": 40, "alt": 25}

Publishes progress/errors on /sar/mission_log.
"""
import json
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from std_msgs.msg import String
from geographic_msgs.msg import GeoPoseStamped
from mavros_msgs.msg import State
from sensor_msgs.msg import NavSatFix


class MissionBridge(Node):
    def __init__(self):
        super().__init__('mission_bridge')
        self.state = State()
        self.fix = NavSatFix()

        sensor_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        state_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL)

        self.create_subscription(String, '/sar/command', self.on_command, 10)
        self.create_subscription(State, '/mavros/state', self.on_state, state_qos)
        self.create_subscription(NavSatFix, '/mavros/global_position/global',
                                 self.on_fix, sensor_qos)

        self.log_pub = self.create_publisher(String, '/sar/mission_log', 10)
        self.setpoint_pub = self.create_publisher(
            GeoPoseStamped, '/mavros/setpoint_position/global', 10)

        self.get_logger().info('mission_bridge ready — listening on /sar/command')

    # ---------- state ----------
    def on_state(self, msg):
        self.state = msg

    def on_fix(self, msg):
        self.fix = msg

    def log(self, text):
        self.get_logger().info(text)
        self.log_pub.publish(String(data=text))

    # ---------- command handling ----------
    def on_command(self, msg):
        try:
            c = json.loads(msg.data)
        except json.JSONDecodeError:
            self.log(f'bad command JSON: {msg.data!r}')
            return
        cmd = c.get('cmd', '')
        handler = getattr(self, f'cmd_{cmd}', None)
        if handler is None:
            if cmd not in ('arm', 'disarm', 'mode', 'takeoff', 'land', 'rtl'):
                self.log(f'unknown command: {cmd}')
            return
        self.log(f'executing: {c}')
        try:
            handler(c)
        except Exception as e:  # keep the bridge alive on any failure
            self.log(f'command {cmd} failed: {e}')

    # arm/disarm/mode/takeoff/land/rtl are executed by the dashboard's direct
    # MAVLink link (mavros command-plugin service discovery is unreliable);
    # this bridge owns the topic-based commands below.
    def cmd_goto(self, c):
        sp = GeoPoseStamped()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.pose.position.latitude = float(c['lat'])
        sp.pose.position.longitude = float(c['lon'])
        sp.pose.position.altitude = float(c.get('alt', 20.0))
        self.setpoint_pub.publish(sp)
        self.log(f"goto {c['lat']:.6f},{c['lon']:.6f} alt {sp.pose.position.altitude}")

    def cmd_search_pattern(self, c):
        """Publish an expanding-square of global setpoints around a point."""
        lat0 = float(c.get('lat', self.fix.latitude))
        lon0 = float(c.get('lon', self.fix.longitude))
        radius = float(c.get('radius', 40.0))
        alt = float(c.get('alt', 25.0))
        # generate square-spiral waypoints (published as a plan on /sar/mission_log,
        # dashboard/agent step through them via goto)
        wps, step, leg = [], radius / 4.0, 1
        x = y = 0.0
        dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        d = 0
        while max(abs(x), abs(y)) < radius:
            dx, dy = dirs[d % 4]
            x += dx * step * leg
            y += dy * step * leg
            wps.append((lat0 + y / 111111.0,
                        lon0 + x / (111111.0 * math.cos(math.radians(lat0)))))
            if d % 2 == 1:
                leg += 1
            d += 1
        plan = {'type': 'search_pattern', 'alt': alt,
                'waypoints': [{'lat': la, 'lon': lo} for la, lo in wps]}
        self.log_pub.publish(String(data=json.dumps(plan)))
        if wps:
            self.cmd_goto({'lat': wps[0][0], 'lon': wps[0][1], 'alt': alt})


def main():
    rclpy.init()
    node = MissionBridge()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
