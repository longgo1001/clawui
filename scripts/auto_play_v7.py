#!/usr/bin/env python3
"""Auto-play v7: CDP screenshots + xdotool mouse control."""
import sys, asyncio, json, base64, time, subprocess, urllib.request
sys.stdout.reconfigure(line_buffering=True)
import numpy as np
from PIL import Image
from io import BytesIO
import websockets

GW, GH = 390, 844  # game viewport
# Screen coords of game area (from analysis)
SL, SR, ST, SB = 162, 394, 126, 646
SW, SH = SR - SL, SB - ST  # 244, 522
SCALE_X, SCALE_Y = SW / GW, SH / GH  # ~0.626, ~0.618
CDP_PORT = 9229

def game_to_screen(gx, gy):
    return int(SL + gx * SCALE_X), int(ST + gy * SCALE_Y)

def sh(cmd):
    subprocess.run(['bash', '-lc', cmd], capture_output=True, timeout=5)

XPRE = "DISPLAY=:0"

def xmove(sx, sy):
    sh(f'{XPRE} xdotool mousemove {sx} {sy}')

def xclick(sx, sy):
    sh(f'{XPRE} xdotool mousemove {sx} {sy}; sleep 0.08; {XPRE} xdotool click 1')

def xdown(sx, sy):
    sh(f'{XPRE} xdotool mousemove {sx} {sy}; sleep 0.05; {XPRE} xdotool mousedown 1')

def xup():
    sh(f'{XPRE} xdotool mouseup 1')

async def run_session(ws, dur_left):
    msg_id = 0
    async def cdp(method, params=None):
        nonlocal msg_id
        msg_id += 1
        m = {'id': msg_id, 'method': method}
        if params: m['params'] = params
        await ws.send(json.dumps(m))
        while True:
            r = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            if r.get('id') == msg_id:
                return r.get('result', {})

    async def screenshot():
        r = await cdp('Page.captureScreenshot', {'format': 'png'})
        if 'data' in r:
            return np.array(Image.open(BytesIO(base64.b64decode(r['data']))).convert('RGB'))
        return None

    # Initialize simulated player position
    gpx, gpy = GW//2, int(GH*0.88)
    sx, sy = game_to_screen(gpx, gpy)
    xdown(sx, sy)

    start = time.time()
    frames, restarts, restart_cooldown, prev_bytes = 0, 0, 0, None

    # Core game loop
    while time.time() - start < dur_left:
        canvas = await screenshot()
        if canvas is None:
            await asyncio.sleep(0.1)
            continue

        frames += 1

        if check_game_over(canvas) and time.time() > restart_cooldown:
            restarts += 1
            xup()
            bsx, bsy = game_to_screen(GW//2, int(GH*0.58))
            xclick(bsx, bsy)
            await asyncio.sleep(2.0)
            gpx, gpy = GW//2, int(GH*0.88)
            sx, sy = game_to_screen(gpx, gpy)
            xdown(sx, sy)
            restart_cooldown = time.time() + 10
            continue

        # AI-based movement
        tx = ai_decide(gpx, gpy, [], [], [])
        dx = tx - gpx

        if abs(dx) > 5:
            nsx, nsy = game_to_screen(tx, gpy)
            xmove(nsx, nsy)
            await asyncio.sleep(abs(dx) * 0.02)
            gpx = tx

    xup()

    return frames, restarts

async def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    print('[v7] Starting for', dur, 'seconds')
    while True:
        try:
            ws_url = 'ws://127.0.0.1:9229/devtools/page/1'
            asyncio.create_task(run_session(ws_url))
        except Exception:
            break

asyncio.run(main())