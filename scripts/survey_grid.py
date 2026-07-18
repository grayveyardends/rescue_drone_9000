"""Sample agent script: fly a small survey grid via /sar/command.

The LLM can trigger this with:  <<action_start>> run_script survey_grid.py <<end>>
"""
import json
import subprocess
import time

WAYPOINT_ALT = 25.0
GRID = [
    (9.93140, 76.26710), (9.93140, 76.26760),
    (9.93110, 76.26760), (9.93110, 76.26710),
]


def send(cmd: dict):
    subprocess.run([
        'ros2', 'topic', 'pub', '--once', '/sar/command',
        'std_msgs/String', json.dumps({'data': json.dumps(cmd)}),
    ], check=False)


send({'cmd': 'takeoff', 'alt': WAYPOINT_ALT})
time.sleep(12)
for lat, lon in GRID:
    send({'cmd': 'goto', 'lat': lat, 'lon': lon, 'alt': WAYPOINT_ALT})
    time.sleep(15)
send({'cmd': 'rtl'})
