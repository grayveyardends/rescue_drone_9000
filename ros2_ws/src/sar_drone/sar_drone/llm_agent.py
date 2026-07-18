"""LLM agent node.

Listens for frames (sensor_msgs/CompressedImage on /sar/frame, or images pushed by
the dashboard via /sar/analyze_b64), sends them to the llama-server multimodal
endpoint, publishes the structured SAR response on /sar/model_output, and turns
<<action_start>> blocks into /sar/command messages the mission_bridge executes.

Also maintains the found-people registry in /agent_fs/people/registry.json.
"""
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import CompressedImage, NavSatFix
from rclpy.qos import QoSProfile, ReliabilityPolicy

import requests

AGENT_FS = Path(os.environ.get('AGENT_FS', '/agent_fs'))
SCRIPTS_DIR = Path(os.environ.get('SAR_SCRIPTS', '/sar/scripts'))
LLM_HOST = os.environ.get('LLM_HOST', 'http://127.0.0.1:8080')

SYSTEM_PROMPT = (
    "You are a SAR drone agent. Respond ONLY with the structured syntax: "
    "[[personX]] blocks, <<action_start>>...<<end>>, <<say>>...<<end>>, "
    "<<do>>...<<end>>, OBSERVATION: lines with GPS tags, PRIORITY: level. "
    "Include a Malayalam translation inside every <<say>> block. "
    "Available actions: call ambulance <lat> <lon> <severity>, "
    "notify <team> <details>, goto <lat> <lon> <alt>, takeoff <alt>, rtl, land, "
    "search_pattern <lat> <lon> <radius>, run_script <name>, "
    "register_person <id> <state> <needs>."
)


class LLMAgent(Node):
    def __init__(self):
        super().__init__('llm_agent')
        for d in ('action', 'plans', 'people', 'logs'):
            (AGENT_FS / d).mkdir(parents=True, exist_ok=True)
        self.registry_file = AGENT_FS / 'people' / 'registry.json'
        if not self.registry_file.exists():
            self.registry_file.write_text('{}')
        self.fix = None

        sensor_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(CompressedImage, '/sar/frame', self.on_frame, sensor_qos)
        self.create_subscription(String, '/sar/analyze_b64', self.on_b64, 10)
        self.create_subscription(NavSatFix, '/mavros/global_position/global',
                                 self.on_fix, sensor_qos)

        self.out_pub = self.create_publisher(String, '/sar/model_output', 10)
        self.cmd_pub = self.create_publisher(String, '/sar/command', 10)
        self.alert_pub = self.create_publisher(String, '/sar/alerts', 10)
        self.people_pub = self.create_publisher(String, '/sar/people', 10)

        self.last_call = 0.0
        self.min_interval = float(os.environ.get('LLM_MIN_INTERVAL', '8'))
        self.get_logger().info(f'llm_agent ready, LLM at {LLM_HOST}')

    def on_fix(self, msg):
        self.fix = msg

    # ---------- frame intake ----------
    def on_frame(self, msg: CompressedImage):
        now = time.time()
        if now - self.last_call < self.min_interval:
            return
        self.last_call = now
        b64 = base64.b64encode(bytes(msg.data)).decode()
        self.analyze(b64, context='live camera frame')

    def on_b64(self, msg: String):
        try:
            payload = json.loads(msg.data)
            self.analyze(payload['image'], context=payload.get('context', ''))
        except (json.JSONDecodeError, KeyError) as e:
            self.get_logger().error(f'bad analyze_b64 payload: {e}')

    # ---------- LLM ----------
    def analyze(self, b64_img: str, context: str = ''):
        gps = ''
        if self.fix is not None:
            gps = f'Current drone GPS: {self.fix.latitude:.6f},{self.fix.longitude:.6f} alt {self.fix.altitude:.1f}m.'
        try:
            r = requests.post(f'{LLM_HOST}/v1/chat/completions', json={
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': [
                        {'type': 'image_url',
                         'image_url': {'url': f'data:image/jpeg;base64,{b64_img}'}},
                        {'type': 'text',
                         'text': f'Analyze this drone frame. {gps} {context}'},
                    ]},
                ],
                'temperature': 0.3, 'max_tokens': 1024,
            }, timeout=120)
            response = r.json()['choices'][0]['message']['content']
        except Exception as e:
            self.get_logger().error(f'LLM call failed: {e}')
            self.alert_pub.publish(String(data=f'LLM unreachable: {e}'))
            return
        self.out_pub.publish(String(data=response))
        (AGENT_FS / 'logs' / f'response_{int(time.time())}.txt').write_text(response)
        self.execute_actions(response)

    # ---------- action parsing / execution ----------
    def execute_actions(self, response: str):
        actions = [a.strip() for a in
                   re.findall(r'<<action_start>>(.*?)<<end>>', response, re.DOTALL)]
        ts = int(time.time())
        (AGENT_FS / 'action' / f'action_{ts}.json').write_text(
            json.dumps({'timestamp': ts, 'actions': actions}))
        for a in actions:
            self.dispatch(a)

    def dispatch(self, action: str):
        t = action.lower()
        nums = re.findall(r'-?\d+\.?\d*', action)

        def fnum(i, default=None):
            return float(nums[i]) if i < len(nums) else default

        if t.startswith('call ambulance') or t.startswith('notify'):
            self.alert_pub.publish(String(data=action))
        elif t.startswith('goto') and len(nums) >= 2:
            self.cmd_pub.publish(String(data=json.dumps(
                {'cmd': 'goto', 'lat': fnum(0), 'lon': fnum(1), 'alt': fnum(2, 20.0)})))
        elif t.startswith('takeoff'):
            self.cmd_pub.publish(String(data=json.dumps(
                {'cmd': 'takeoff', 'alt': fnum(0, 15.0)})))
        elif t.startswith('rtl'):
            self.cmd_pub.publish(String(data=json.dumps({'cmd': 'rtl'})))
        elif t.startswith('land'):
            self.cmd_pub.publish(String(data=json.dumps({'cmd': 'land'})))
        elif t.startswith('search_pattern') and len(nums) >= 2:
            self.cmd_pub.publish(String(data=json.dumps(
                {'cmd': 'search_pattern', 'lat': fnum(0), 'lon': fnum(1),
                 'radius': fnum(2, 40.0)})))
        elif t.startswith('run_script'):
            self.run_script(action.split()[-1])
        elif t.startswith('register_person'):
            self.register_person(action)
        else:
            self.alert_pub.publish(String(data=f'unhandled action: {action}'))

    def run_script(self, name: str):
        """Only scripts that already exist inside /sar/scripts may run."""
        safe = Path(name).name
        path = SCRIPTS_DIR / safe
        if not path.is_file():
            self.alert_pub.publish(String(data=f'script not found: {safe}'))
            return
        subprocess.Popen(['python3', str(path)],
                         stdout=open(AGENT_FS / 'logs' / f'{safe}.log', 'w'),
                         stderr=subprocess.STDOUT)
        self.get_logger().info(f'launched script {safe}')

    def register_person(self, action: str):
        parts = action.split(maxsplit=3)  # register_person <id> <state> <needs...>
        pid = parts[1] if len(parts) > 1 else f'p{int(time.time())}'
        reg = json.loads(self.registry_file.read_text())
        reg[pid] = {
            'id': pid,
            'state': parts[2] if len(parts) > 2 else 'unknown',
            'needs': parts[3] if len(parts) > 3 else '',
            'gps': [self.fix.latitude, self.fix.longitude] if self.fix else None,
            'updated': time.time(),
        }
        self.registry_file.write_text(json.dumps(reg, indent=2))
        self.people_pub.publish(String(data=json.dumps(reg)))


def main():
    rclpy.init()
    rclpy.spin(LLMAgent())


if __name__ == '__main__':
    main()
