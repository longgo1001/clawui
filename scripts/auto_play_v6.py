#!/usr/bin/env python3
"""Auto-play v6: gnome-screenshot based (~1 FPS), compensates with predictive movement."""

import subprocess, time, sys, os, math
sys.stdout.reconfigure(line_buffering=True)
import numpy as np

try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr = RapidOCR()
except Exception:
    _ocr = None

# Game canvas (screen coordinates)
CL, CR, CT, CB = 206, 450, 128, 650
CW, CH = CR - CL, CB - CT  # 244, 522
CX = (CL + CR) // 2  # 328
PY = CB - 60  # 590 - player Y in screen coords

def sh(c):
    return subprocess.run(['bash', '-lc', c], capture_output=True, text=True, timeout=5)

def xpref():
    return "DISPLAY=:0"

def xmove(x, y):
    sh(f'{xpref()} xdotool mousemove {x} {y}')

def xclick(x, y):
    sh(f'{xpref()} xdotool mousemove {x} {y}; sleep 0.08; {xpref()} xdotool click 1')

def grab():
    """Grab screenshot, crop to game canvas, return RGB numpy array."""
    path = '/dev/shm/_v6_frame.png'
    sh(f'gnome-screenshot -f {path}')
    try:
        from PIL import Image
        img = np.array(Image.open(path).convert('RGB'))
        canvas = img[CT:CB, CL:CR]
        return canvas
    except Exception as e:
        print(f'[v6] grab error: {e}')
        return None


def _cluster(mask, min_px=6):
    ys, xs = np.where(mask)
    if len(xs) < min_px:
        return []
    g = {}
    cell = 20
    for x, y in zip(xs, ys):
        k = (x // cell, y // cell)
        if k not in g:
            g[k] = [0, 0, 0]
        g[k][0] += x
        g[k][1] += y
        g[k][2] += 1
    return [(s[0] // s[2], s[1] // s[2]) for s in g.values() if s[2] >= min_px]


def detect(canvas):
    """Detect enemies and powerups. Returns canvas-relative coordinates."""
    r, g, b = canvas[:,:,0].astype(np.int16), canvas[:,:,1].astype(np.int16), canvas[:,:,2].astype(np.int16)
    
    # Enemies: red/pink (R>180, G<100, B<130), orange (R>180, G 80-180, B<100), purple (R>150, B>150, G<100)
    red = (r > 180) & (g < 100) & (b < 130)
    orange = (r > 180) & (g > 80) & (g < 180) & (b < 100)
    purple = (r > 150) & (b > 150) & (g < 100)
    enemies = _cluster(red | orange | purple, 6)
    
    # Player: blue (B>150, R<80, G<140)
    blue = (b > 150) & (r < 80) & (g < 140)
    player_pts = np.where(blue)
    player = None
    if len(player_pts[0]) > 20:
        player = (int(np.mean(player_pts[1])), int(np.mean(player_pts[0])))
    
    # Powerups: bright cyan/green/yellow
    green = (g > 130) & (r < 120) & (b < 120)
    cyan = (b > 150) & (g > 130) & (r < 100)
    yellow = (r > 180) & (g > 180) & (b < 100)
    powerups = _cluster(green | cyan | yellow, 6)
    
    # Enemy bullets: small bright pink
    pink = (r > 200) & (b > 80) & (b < 150) & (g < 80)
    bullets = _cluster(pink, 3)
    
    return enemies, player, powerups, bullets


def check_game_over(canvas):
    """Check for game over - fast color check only (no OCR per frame)."""
    # Game over screen has large red "GAME OVER" text and white score text in center
    center = canvas[CH//3:CH*2//3, CW//4:CW*3//4]
    gray = np.mean(center, axis=2)
    white_ratio = np.sum(gray > 200) / max(gray.size, 1)
    # Also check for red text
    r, g, b = center[:,:,0], center[:,:,1], center[:,:,2]
    red_text = np.sum((r > 200) & (g < 80) & (b < 80)) / max(center[:,:,0].size, 1)
    return (white_ratio > 0.03) or (red_text > 0.02)


def ai_decide(px, py, enemies, powerups, bullets, prev_enemies):
    """Decide target X position. Returns canvas-relative X."""
    close_line = CH * 0.55
    
    # Predict enemy movement (enemies move down)
    predicted_enemies = []
    for ex, ey in enemies:
        # Estimate speed ~4px per frame, at 1 FPS that's ~60px between frames
        predicted_enemies.append((ex, ey + 40))  # where they'll be when we get there
    
    all_threats = predicted_enemies + [(bx, by + 20) for bx, by in bullets]
    
    best_x, best_s = CW // 2, -999999
    
    # 20 candidate positions for finer resolution
    for i in range(20):
        cx = int(CW * (i + 0.5) / 20)
        s = 0.0
        
        for ex, ey in all_threats:
            dx = abs(cx - ex)
            if ey >= close_line:
                # Danger zone
                closeness = max(0.0, 1.0 - dx / 80.0)
                danger = max(0.0, (ey - close_line) / (CH - close_line + 1))
                s -= closeness * (300 + 600 * danger)
                if dx < 30:
                    s -= 500
            else:
                # Scoring zone - align with enemies for auto-fire hits
                align = max(0.0, 1.0 - dx / 90.0)
                far_bonus = max(0.0, (close_line - ey) / close_line)
                s += align * (100 + 150 * far_bonus)
        
        # Powerup attraction
        for ppx, ppy in powerups:
            dist = abs(cx - ppx)
            if dist < 100 and ppy > CH * 0.2:
                safe = True
                for ex, ey in all_threats:
                    if abs(ppx - ex) < 50 and abs(ppy - ey) < 50:
                        safe = False
                        break
                if safe:
                    s += max(0, 120 - dist) * 2
        
        # Smoothness penalty
        s -= abs(cx - px) * 0.15
        # Center bias (mild)
        s -= abs(cx - CW // 2) * 0.05
        
        if s > best_s:
            best_s = s
            best_x = cx
    
    return best_x


def smooth_move(current_sx, target_sx, steps=5, delay=0.04):
    """Move mouse smoothly from current to target screen X."""
    for i in range(1, steps + 1):
        frac = i / steps
        x = int(current_sx + (target_sx - current_sx) * frac)
        xmove(x, PY)
        time.sleep(delay)


def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    print(f'[v6] gnome-screenshot mode, {dur}s')
    
    # Grab mouse and start
    xmove(CX, PY)
    time.sleep(0.1)
    sh(f'{xpref()} xdotool mousedown 1')
    time.sleep(0.2)
    
    start = time.time()
    frames = 0
    restarts = 0
    px = CW // 2  # canvas-relative player X
    sx = CX       # screen X
    prev_enemies = []
    scores_seen = []
    
    try:
        while time.time() - start < dur:
            t0 = time.time()
            canvas = grab()
            grab_time = time.time() - t0
            
            if canvas is None:
                time.sleep(0.5)
                continue
            
            frames += 1
            enemies, player, powerups, bullets = detect(canvas)
            
            # Update player position from detection
            if player:
                px, py = player
            else:
                py = int(CH * 0.75)
            
            # Check game over
            go = check_game_over(canvas)
            if go:
                restarts += 1
                el = time.time() - start
                print(f'[v6] t={el:.0f}s GAME OVER #{restarts}, restarting...')
                sh(f'{xpref()} xdotool mouseup 1')
                time.sleep(0.3)
                
                if isinstance(go, tuple):
                    _, rx, ry = go
                    xclick(rx + CL, ry + CT)
                else:
                    # Click "重新开始" button area (roughly center-bottom of canvas)
                    xclick(CX, CT + int(CH * 0.82))
                
                time.sleep(1.5)
                xmove(CX, PY)
                time.sleep(0.1)
                sh(f'{xpref()} xdotool mousedown 1')
                time.sleep(0.3)
                px = CW // 2
                sx = CX
                prev_enemies = []
                continue
            
            # AI decision
            tx = ai_decide(px, py, enemies, powerups, bullets, prev_enemies)
            target_sx = tx + CL
            
            # Smooth move
            dx = target_sx - sx
            if abs(dx) > 3:
                steps = min(8, max(2, abs(dx) // 10))
                smooth_move(sx, target_sx, steps=steps, delay=0.03)
                sx = target_sx
                px = tx
            
            prev_enemies = enemies
            
            if frames % 5 == 0:
                el = time.time() - start
                print(f'[v6] t={el:.0f}s f={frames} enemies={len(enemies)} pups={len(powerups)} '
                      f'bullets={len(bullets)} px={px} grab={grab_time:.2f}s restarts={restarts}')
    
    except KeyboardInterrupt:
        pass
    finally:
        sh(f'{xpref()} xdotool mouseup 1')
        el = time.time() - start
        print(f'[v6] Done! {frames} frames in {el:.0f}s ({frames/max(el,1):.1f} fps), {restarts} restarts')


if __name__ == '__main__':
    main()
