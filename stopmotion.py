#!/usr/bin/env python3
"""
Stop Motion Animation Studio - Orange Pi Zero 2W
FINAL VERSION - All Buttons Working
"""

import cv2
import numpy as np
import subprocess
import time
import os
import json
from datetime import datetime
from collections import deque

# GPIO Configuration - FINAL WORKING
GPIOCHIP_NUM = 1
BTN_CAPTURE = 268  # Pin 11
BTN_PLAY = 256     # Pin 29
BTN_REWIND = 261   # Pin 15
BTN_CLEAR = 267    # Pin 32
BTN_SAVE = 271     # Pin 31

# Paths
PERSISTENT_DIR = "/mnt/dietpi_userdata/stopmotion"
SETTINGS_FILE = os.path.join(PERSISTENT_DIR, "settings.json")
os.makedirs(PERSISTENT_DIR, exist_ok=True)

# Settings
DEFAULT_SETTINGS = {
    "resolution": "800x600",
    "fps": 10,
    "max_frames": 300,
    "onion_skin_enabled": True,
    "onion_skin_opacity": 30,
    "onion_skin_count": 1
}

# Timing
MIN_BUTTON_INTERVAL = 0.5
CLEAR_HOLD_TIME = 2.0
REWIND_HOLD_TIME = 1.5
ONION_TOGGLE_HOLD_TIME = 1.0
MESSAGE_DISPLAY_TIME = 2.0
SETTINGS_COMBO_TIME = 2.0

ONION_SKIN_COLORS = [(0, 255, 0), (0, 200, 200)]

# Screen button definitions (fallback for physical buttons)
BUTTON_DEFS = [
    (BTN_CAPTURE, "CAPTURE", (0, 160, 0)),
    (BTN_PLAY,    "PLAY",    (180, 100, 0)),
    (BTN_REWIND,  "DELETE",  (0, 140, 200)),
    (BTN_CLEAR,   "CLEAR",   (0, 0, 180)),
    (BTN_SAVE,    "SAVE",    (160, 0, 130)),
]
BTN_HEIGHT = 55
BTN_MARGIN = 8
BTN_BOTTOM_PAD = 5

class GPIO:
    """Improved GPIO with debouncing"""
    
    # Debounce buffer - stores last N readings
    _history = {}
    _history_size = 3  # Require 3 consecutive same readings
    
    @staticmethod
    def read(chip_num, line):
        """Read GPIO with debouncing - INVERTED LOGIC"""
        # Initialize history for this pin
        if line not in GPIO._history:
            GPIO._history[line] = deque(maxlen=GPIO._history_size)
        
        try:
            result = subprocess.run(
                ['gpioget', '-c', str(chip_num), '--bias=pull-up', str(line)],
                capture_output=True, 
                text=True, 
                timeout=0.1
            )
            
            # INVERTED: inactive = pressed, active = not pressed
            pressed = 'inactive' in result.stdout.strip().lower()
            
            # Add to history
            GPIO._history[line].append(pressed)
            
            # Debounce: require all readings in history to agree
            if len(GPIO._history[line]) < GPIO._history_size:
                return False  # Not enough samples yet
            
            # All must be same
            if all(GPIO._history[line]):
                return True  # All pressed
            elif not any(GPIO._history[line]):
                return False  # All not pressed
            else:
                return False  # Mixed readings = bounce, return safe default
            
        except:
            return False

# Load settings
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = {**DEFAULT_SETTINGS, **json.load(f)}
    except:
        settings = DEFAULT_SETTINGS.copy()
else:
    settings = DEFAULT_SETTINGS.copy()

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Save error: {e}")

# Initialize camera
print("Opening camera...")
width, height = map(int, settings["resolution"].split('x'))
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("Trying camera 0...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No camera found")
        exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

for _ in range(10):
    cap.read()

print("Camera ready")

# Create window
print("Creating window...")
window_name = 'Stop Motion Studio'
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# Screen button regions
def calc_button_regions(w, h):
    n = len(BUTTON_DEFS)
    total_margin = BTN_MARGIN * (n + 1)
    btn_w = (w - total_margin) // n
    btn_y = h - BTN_HEIGHT - BTN_BOTTOM_PAD
    regions = {}
    for i, (gpio, label, color) in enumerate(BUTTON_DEFS):
        x1 = BTN_MARGIN + i * (btn_w + BTN_MARGIN)
        regions[gpio] = (x1, btn_y, x1 + btn_w, btn_y + BTN_HEIGHT, label, color)
    return regions

button_regions = calc_button_regions(width, height)
screen_btn_active = None

def mouse_callback(event, x, y, flags, param):
    global screen_btn_active
    if event == cv2.EVENT_LBUTTONDOWN:
        screen_btn_active = None
        for gpio, (x1, y1, x2, y2, _, _) in button_regions.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                screen_btn_active = gpio
                break
    elif event == cv2.EVENT_LBUTTONUP:
        screen_btn_active = None

cv2.setMouseCallback(window_name, mouse_callback)

def is_pressed(btn):
    """Check if button is pressed via GPIO or on-screen click"""
    return GPIO.read(GPIOCHIP_NUM, btn) or screen_btn_active == btn

# State
frames = []
playing = False
onion_skin_enabled = settings["onion_skin_enabled"]

# Timing trackers
last_button_press = {BTN_CAPTURE: 0, BTN_PLAY: 0, BTN_REWIND: 0, BTN_CLEAR: 0, BTN_SAVE: 0}
clear_press_start = None
rewind_press_start = None
onion_toggle_start = None
settings_combo_start = None

# Message
current_message = ""
message_start_time = 0
message_color = (255, 255, 255)

def show_message(msg, color=(255, 255, 255)):
    global current_message, message_start_time, message_color
    current_message = msg
    message_start_time = time.time()
    message_color = color
    print(f"📢 {msg}")

def apply_onion_skin(frame):
    if not onion_skin_enabled or len(frames) == 0:
        return frame
    
    result = frame.copy()
    num_frames = min(settings["onion_skin_count"], len(frames))
    opacity = settings["onion_skin_opacity"] / 100.0
    
    for i in range(num_frames):
        idx = len(frames) - 1 - i
        if idx < 0:
            break
        
        prev = frames[idx]
        if prev.shape[:2] != result.shape[:2]:
            prev = cv2.resize(prev, (result.shape[1], result.shape[0]))
        
        color_idx = i % len(ONION_SKIN_COLORS)
        tinted = cv2.addWeighted(prev, 0.7, 
                                np.full_like(prev, ONION_SKIN_COLORS[color_idx]), 
                                0.3, 0)
        
        frame_opacity = opacity * (1.0 - i * 0.2)
        result = cv2.addWeighted(result, 1.0, tinted, frame_opacity, 0)
    
    return result

def draw_overlay(frame):
    h, w = frame.shape[:2]
    
    # Top bar
    cv2.rectangle(frame, (0, 0), (w, 70), (0, 0, 0), -1)
    
    # Frame count
    max_f = settings["max_frames"]
    color = (0, 255, 0) if len(frames) < max_f * 0.8 else (0, 0, 255)
    cv2.putText(frame, f"Frames: {len(frames)}/{max_f}", (20, 45), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    
    # Status
    status = "PLAYING" if playing else "LIVE"
    s_color = (0, 255, 0) if playing else (255, 255, 255)
    cv2.putText(frame, status, (w - 200, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, s_color, 2)
    
    # Onion indicator
    if onion_skin_enabled and len(frames) > 0 and not playing:
        cv2.putText(frame, "ONION", (w - 200, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Message
    if time.time() - message_start_time < MESSAGE_DISPLAY_TIME:
        text_size = cv2.getTextSize(current_message, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = (w - text_size[0]) // 2
        text_y = h // 2
        
        cv2.putText(frame, current_message, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 5)
        cv2.putText(frame, current_message, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, message_color, 3)
    
    # Clear hold progress
    if clear_press_start:
        hold_time = time.time() - clear_press_start
        progress = min(hold_time / CLEAR_HOLD_TIME, 1.0)
        
        bar_w = int(w * 0.6)
        bar_x = (w - bar_w) // 2
        bar_y = h - 120
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 40), (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * progress), bar_y + 40), (0, 0, 255), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 40), (255, 255, 255), 3)
        cv2.putText(frame, "HOLD TO CLEAR ALL", (bar_x, bar_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Screen buttons
    for gpio, (x1, y1, x2, y2, label, color) in button_regions.items():
        if screen_btn_active == gpio:
            draw_color = tuple(min(c + 80, 255) for c in color)
        else:
            draw_color = color
        cv2.rectangle(frame, (x1, y1), (x2, y2), draw_color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        tx = x1 + (x2 - x1 - text_size[0]) // 2
        ty = y1 + (y2 - y1 + text_size[1]) // 2
        cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return frame

# Main loop
print("Starting...")
print("GPIO Configuration:")
print(f"  CAPTURE: Pin 11 (GPIO {BTN_CAPTURE})")
print(f"  PLAY:    Pin 29 (GPIO {BTN_PLAY})")
print(f"  REWIND:  Pin 15 (GPIO {BTN_REWIND})")
print(f"  CLEAR:   Pin 32 (GPIO {BTN_CLEAR})")
print(f"  SAVE:    Pin 31 (GPIO {BTN_SAVE})")
show_message("Ready!", (0, 255, 0))

play_index = 0
last_play_time = time.time()

try:
    while True:
        current_time = time.time()
        
        # === BUTTON POLLING ===
        
        # Settings combo (PLAY + SAVE) - placeholder
        if is_pressed(BTN_PLAY) and is_pressed(BTN_SAVE):
            if settings_combo_start is None:
                settings_combo_start = current_time
            elif current_time - settings_combo_start >= SETTINGS_COMBO_TIME:
                show_message("Settings: N/A", (0, 255, 255))
                settings_combo_start = None
            continue
        else:
            settings_combo_start = None
        
        # CAPTURE with onion toggle
        capture_btn_pressed = is_pressed(BTN_CAPTURE)
        
        if capture_btn_pressed:
            if onion_toggle_start is None:
                onion_toggle_start = current_time
            elif current_time - onion_toggle_start >= ONION_TOGGLE_HOLD_TIME:
                # Long press - toggle onion
                if current_time - last_button_press[BTN_CAPTURE] > MIN_BUTTON_INTERVAL:
                    onion_skin_enabled = not onion_skin_enabled
                    settings["onion_skin_enabled"] = onion_skin_enabled
                    show_message(f"Onion: {'ON' if onion_skin_enabled else 'OFF'}", (0, 255, 255))
                    save_settings()
                    last_button_press[BTN_CAPTURE] = current_time
                    onion_toggle_start = None
        else:
            # Button released
            if onion_toggle_start is not None:
                hold_time = current_time - onion_toggle_start
                if hold_time < ONION_TOGGLE_HOLD_TIME and hold_time > 0.1:
                    # Quick press - capture frame
                    if not playing and current_time - last_button_press[BTN_CAPTURE] > MIN_BUTTON_INTERVAL:
                        if len(frames) < settings["max_frames"]:
                            ret, frame = cap.read()
                            if ret:
                                frames.append(frame.copy())
                                show_message(f"Frame {len(frames)}", (0, 255, 0))
                        else:
                            show_message(f"Max {settings['max_frames']}!", (0, 0, 255))
                        last_button_press[BTN_CAPTURE] = current_time
                onion_toggle_start = None
        
        # PLAY
        if is_pressed(BTN_PLAY):
            if current_time - last_button_press[BTN_PLAY] > MIN_BUTTON_INTERVAL:
                if len(frames) > 0:
                    playing = not playing
                    show_message("Playing" if playing else "Paused", 
                               (0, 255, 0) if playing else (255, 255, 0))
                    play_index = 0
                else:
                    show_message("No frames!", (0, 165, 255))
                last_button_press[BTN_PLAY] = current_time
        
        # REWIND (delete)
        if is_pressed(BTN_REWIND):
            if rewind_press_start is None:
                rewind_press_start = current_time
            elif current_time - rewind_press_start >= REWIND_HOLD_TIME:
                # Delete 5
                if len(frames) > 0:
                    deleted = min(5, len(frames))
                    frames = frames[:-deleted]
                    show_message(f"Deleted {deleted}!", (255, 255, 0))
                rewind_press_start = None
        else:
            if rewind_press_start and current_time - rewind_press_start < REWIND_HOLD_TIME:
                # Delete 1
                if len(frames) > 0:
                    frames.pop()
                    show_message(f"{len(frames)} left", (255, 255, 0))
            rewind_press_start = None
        
        # CLEAR (hold to clear all)
        if is_pressed(BTN_CLEAR):
            if clear_press_start is None:
                clear_press_start = current_time
            elif current_time - clear_press_start >= CLEAR_HOLD_TIME:
                count = len(frames)
                frames = []
                show_message(f"Cleared {count}!", (255, 0, 0))
                clear_press_start = None
        else:
            clear_press_start = None
        
        # SAVE
        if is_pressed(BTN_SAVE):
            if current_time - last_button_press[BTN_SAVE] > MIN_BUTTON_INTERVAL:
                if len(frames) > 0:
                    show_message("Saving...", (255, 255, 0))
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    video_path = os.path.join(PERSISTENT_DIR, f"animation_{timestamp}.mp4")
                    frames_dir = os.path.join(PERSISTENT_DIR, f"frames_{timestamp}")
                    
                    os.makedirs(frames_dir, exist_ok=True)
                    for i, f in enumerate(frames):
                        cv2.imwrite(os.path.join(frames_dir, f"frame_{i:04d}.jpg"), f,
                                   [cv2.IMWRITE_JPEG_QUALITY, 90])
                    
                    h, w = frames[0].shape[:2]
                    out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'),
                                         settings["fps"], (w, h))
                    for f in frames:
                        out.write(f)
                    out.release()
                    
                    show_message(f"Saved {len(frames)}!", (0, 255, 0))
                    print(f"✅ Saved: {video_path}")
                else:
                    show_message("No frames!", (0, 165, 255))
                last_button_press[BTN_SAVE] = current_time
        
        # === GET DISPLAY FRAME ===
        
        if playing and len(frames) > 0:
            if current_time - last_play_time >= (1.0 / settings["fps"]):
                display_frame = frames[play_index].copy()
                play_index = (play_index + 1) % len(frames)
                last_play_time = current_time
            else:
                cv2.waitKey(1)
                continue
        else:
            ret, display_frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            # Apply onion skin
            display_frame = apply_onion_skin(display_frame)
        
        # Draw overlay
        display_frame = draw_overlay(display_frame)
        
        # Display
        cv2.imshow(window_name, display_frame)
        
        # Check quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Done")
