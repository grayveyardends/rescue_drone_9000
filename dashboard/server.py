"""SAR mission-control dashboard backend.

- Streams MAVLink telemetry (direct pymavlink link to SITL/Pixhawk) over /ws
- Relays ROS topics (model output, mission log, alerts, people) via rosbridge
- Accepts commands + rescue-image uploads from the browser
- Manages `ros2 bag record` sessions
Run:  uvicorn dashboard.server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import base64
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

MAVLINK_URL = os.environ.get('MAVLINK_URL', 'udp:127.0.0.1:14551')
ROSBRIDGE = os.environ.get('ROSBRIDGE', 'ws://127.0.0.1:9090')
LLM_HOST = os.environ.get('LLM_HOST', 'http://127.0.0.1:8080')
AGENT_FS = Path(os.environ.get('AGENT_FS', str(Path(__file__).resolve().parent.parent / 'agent_fs')))
BAGS_DIR = Path(os.environ.get('BAGS_DIR', str(Path(__file__).resolve().parent.parent / 'bags')))
SCRIPTS_DIR = Path(os.environ.get('SAR_SCRIPTS', str(Path(__file__).resolve().parent.parent / 'scripts')))

app = FastAPI(title='SAR Drone Mission Control')

clients: set = set()
telemetry = {'lat': 0.0, 'lon': 0.0, 'alt': 0.0, 'heading': 0, 'groundspeed': 0.0,
             'battery': -1, 'mode': '--', 'armed': False, 'connected': False}
event_loop = None


def broadcast(msg: dict):
    """Thread-safe push to all websocket clients."""
    if event_loop is None:
        return
    data = json.dumps(msg)
    for ws in list(clients):
        asyncio.run_coroutine_threadsafe(_send(ws, data), event_loop)


async def _send(ws, data):
    try:
        await ws.send_text(data)
    except Exception:
        clients.discard(ws)


# ---------------- MAVLink telemetry + command executor ----------------
mav_master = None
mav_lock = threading.Lock()

# commands executed over the direct MAVLink link (mavros service discovery is
# unreliable for the command plugin; COMMAND_LONG is what a GCS would send)
MAVLINK_CMDS = {'arm', 'disarm', 'mode', 'takeoff', 'land', 'rtl'}


def exec_mavlink(c: dict):
    from pymavlink import mavutil
    m = mav_master
    if m is None:
        broadcast({'type': 'alert', 'text': f'MAVLink not connected, dropped: {c}'})
        return
    cmd = c.get('cmd')

    def command_long(cmd_id, *params):
        p = list(params) + [0] * (7 - len(params))
        with mav_lock:
            m.mav.command_long_send(m.target_system, m.target_component,
                                    cmd_id, 0, *p)

    def set_mode(name):
        mapping = m.mode_mapping() or {}
        if name in mapping:
            with mav_lock:
                m.set_mode(mapping[name])

    if cmd == 'arm':
        command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
    elif cmd == 'disarm':
        command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0)
    elif cmd == 'mode':
        set_mode(c.get('mode', 'GUIDED'))
    elif cmd == 'land':
        set_mode('LAND')
    elif cmd == 'rtl':
        set_mode('RTL')
    elif cmd == 'takeoff':
        def seq():
            set_mode('GUIDED')
            time.sleep(1)
            command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
            for _ in range(20):          # wait for the FCU to report armed
                if telemetry['armed']:
                    break
                time.sleep(0.5)
            command_long(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                         0, 0, 0, 0, 0, 0, float(c.get('alt', 10.0)))
            broadcast({'type': 'mission_log',
                       'text': f"takeoff to {c.get('alt', 10)}m commanded"})
        threading.Thread(target=seq, daemon=True).start()


def mavlink_loop():
    global mav_master
    from pymavlink import mavutil
    while True:
        try:
            m = mavutil.mavlink_connection(MAVLINK_URL)
            m.wait_heartbeat(timeout=30)
            mav_master = m
            telemetry['connected'] = True
            broadcast({'type': 'ros_log', 'text': f'MAVLink connected: {MAVLINK_URL}'})
            while True:
                msg = m.recv_match(blocking=True, timeout=5)
                if msg is None:
                    continue
                t = msg.get_type()
                if t == 'GLOBAL_POSITION_INT':
                    telemetry.update(lat=msg.lat / 1e7, lon=msg.lon / 1e7,
                                     alt=msg.relative_alt / 1000.0,
                                     heading=msg.hdg / 100.0)
                elif t == 'VFR_HUD':
                    telemetry['groundspeed'] = msg.groundspeed
                elif t == 'SYS_STATUS':
                    telemetry['battery'] = msg.battery_remaining
                elif t == 'HEARTBEAT':
                    telemetry['armed'] = bool(msg.base_mode & 128)
                    telemetry['mode'] = mavutil.mode_string_v10(msg)
                broadcast({'type': 'telemetry', **telemetry})
        except Exception as e:
            telemetry['connected'] = False
            broadcast({'type': 'ros_log', 'text': f'MAVLink lost ({e}), retrying...'})
            time.sleep(3)
        finally:
            mav_master = None


# ---------------- rosbridge relay ----------------
ros = None


def ros_loop():
    global ros
    import roslibpy
    while True:
        try:
            client = roslibpy.Ros(host=ROSBRIDGE.split('//')[1].split(':')[0],
                                  port=int(ROSBRIDGE.rsplit(':', 1)[1]))
            client.run()
            ros = client
            broadcast({'type': 'ros_log', 'text': 'rosbridge connected'})

            def relay(topic, wtype):
                def cb(msg):
                    broadcast({'type': wtype, 'text': msg.get('data', '')})
                roslibpy.Topic(client, topic, 'std_msgs/String').subscribe(cb)

            relay('/sar/model_output', 'model_output')
            relay('/sar/mission_log', 'mission_log')
            relay('/sar/alerts', 'alert')
            relay('/sar/people', 'people')

            # execute MAVLink-class commands published by anyone (LLM agent, UI)
            def cmd_cb(msg):
                try:
                    c = json.loads(msg.get('data', '{}'))
                except json.JSONDecodeError:
                    return
                if c.get('cmd') in MAVLINK_CMDS:
                    exec_mavlink(c)
            roslibpy.Topic(client, '/sar/command', 'std_msgs/String').subscribe(cmd_cb)

            def rosout_cb(msg):
                broadcast({'type': 'ros_log',
                           'text': f"[{msg.get('name', '?')}] {msg.get('msg', '')}"})
            roslibpy.Topic(client, '/rosout', 'rcl_interfaces/Log').subscribe(rosout_cb)
            while client.is_connected:
                time.sleep(1)
        except Exception as e:
            ros = None
            broadcast({'type': 'ros_log', 'text': f'rosbridge lost ({e}), retrying...'})
            time.sleep(3)


def ros_publish(topic: str, data: str):
    if ros is None or not ros.is_connected:
        return False
    import roslibpy
    roslibpy.Topic(ros, topic, 'std_msgs/String').publish(roslibpy.Message({'data': data}))
    return True


@app.on_event('startup')
async def startup():
    global event_loop
    event_loop = asyncio.get_running_loop()
    AGENT_FS.joinpath('people').mkdir(parents=True, exist_ok=True)
    BAGS_DIR.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=mavlink_loop, daemon=True).start()
    threading.Thread(target=ros_loop, daemon=True).start()


# ---------------- websocket ----------------
@app.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    await ws.send_text(json.dumps({'type': 'telemetry', **telemetry}))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)


# ---------------- commands ----------------
@app.post('/api/command')
async def api_command(cmd: dict):
    ok = ros_publish('/sar/command', json.dumps(cmd))
    if not ok:
        # ROS stack down: MAVLink-class commands still work over the direct link
        if cmd.get('cmd') in MAVLINK_CMDS:
            exec_mavlink(cmd)
            broadcast({'type': 'mission_log', 'text': f'CMD via MAVLink only: {cmd}'})
            return {'ok': True, 'via': 'mavlink'}
        return JSONResponse({'ok': False, 'error': 'rosbridge not connected'}, status_code=503)
    broadcast({'type': 'mission_log', 'text': f'CMD sent: {cmd}'})
    return {'ok': True}


# ---------------- image upload -> LLM ----------------
@app.post('/api/upload')
async def api_upload(file: UploadFile, context: str = Form('')):
    raw = await file.read()
    # llama.cpp only decodes jpg/png/bmp — normalize everything to JPEG
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        img.thumbnail((1280, 1280))          # keep prompts small
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=88)
        raw = buf.getvalue()
    except Exception as e:
        return JSONResponse({'ok': False, 'error': f'cannot read image: {e}'},
                            status_code=422)
    b64 = base64.b64encode(raw).decode()
    payload = json.dumps({'image': b64, 'context': context})
    if ros_publish('/sar/analyze_b64', payload):
        return {'ok': True, 'via': 'ros', 'note': 'response arrives on model output panel'}
    # fallback: call the LLM directly if the ROS stack is down
    try:
        import requests
        r = requests.post(f'{LLM_HOST}/v1/chat/completions', json={
            'messages': [
                {'role': 'system', 'content':
                 'You are a SAR drone. Respond using [[personX]], <<action_start>>, '
                 '<<say>>, <<do>>, OBSERVATION:, PRIORITY: structure. Include '
                 'Malayalam translation in <<say>> blocks.'},
                {'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                    {'type': 'text', 'text': f'Analyze this drone frame. {context}'}]},
            ], 'temperature': 0.3, 'max_tokens': 1024}, timeout=120)
        text = r.json()['choices'][0]['message']['content']
        broadcast({'type': 'model_output', 'text': text})
        return {'ok': True, 'via': 'direct', 'response': text}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=502)


# ---------------- rosbag management ----------------
bag_procs: dict = {}


@app.get('/api/bags')
async def bags_list():
    recordings = [{'id': k, 'topics': v['topics'], 'started': v['started'],
                   'running': v['proc'].poll() is None} for k, v in bag_procs.items()]
    files = [{'name': p.name, 'size': sum(f.stat().st_size for f in p.rglob('*') if f.is_file())}
             for p in sorted(BAGS_DIR.iterdir()) if p.is_dir()]
    return {'recordings': recordings, 'files': files}


@app.post('/api/bags/start')
async def bags_start(body: dict):
    topics = body.get('topics') or ['/sar/model_output', '/sar/command',
                                    '/sar/mission_log', '/mavros/global_position/global']
    bag_id = f'bag_{int(time.time())}'
    cmd = ['ros2', 'bag', 'record', '-o', str(BAGS_DIR / bag_id)] + topics
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    bag_procs[bag_id] = {'proc': proc, 'topics': topics, 'started': time.time()}
    return {'ok': True, 'id': bag_id}


@app.post('/api/bags/{bag_id}/stop')
async def bags_stop(bag_id: str):
    entry = bag_procs.get(bag_id)
    if not entry:
        return JSONResponse({'ok': False, 'error': 'unknown bag'}, status_code=404)
    entry['proc'].send_signal(signal.SIGINT)
    return {'ok': True}


# ---------------- people registry ----------------
@app.get('/api/people')
async def people():
    f = AGENT_FS / 'people' / 'registry.json'
    return json.loads(f.read_text()) if f.exists() else {}


@app.post('/api/people/{pid}')
async def people_update(pid: str, body: dict):
    f = AGENT_FS / 'people' / 'registry.json'
    reg = json.loads(f.read_text()) if f.exists() else {}
    reg.setdefault(pid, {'id': pid})
    reg[pid].update(body, updated=time.time())
    f.write_text(json.dumps(reg, indent=2))
    broadcast({'type': 'people', 'text': json.dumps(reg)})
    return {'ok': True}


# ---------------- scripts ----------------
@app.get('/api/scripts')
async def scripts():
    return {'scripts': sorted(p.name for p in SCRIPTS_DIR.glob('*.py'))} if SCRIPTS_DIR.exists() else {'scripts': []}


@app.post('/api/scripts/{name}/run')
async def run_script(name: str):
    path = SCRIPTS_DIR / Path(name).name
    if not path.is_file():
        return JSONResponse({'ok': False, 'error': 'not found'}, status_code=404)
    subprocess.Popen(['python3', str(path)])
    broadcast({'type': 'mission_log', 'text': f'script launched: {path.name}'})
    return {'ok': True}


app.mount('/', StaticFiles(directory=str(Path(__file__).parent / 'static'), html=True), name='static')
