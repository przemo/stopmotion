#!/usr/bin/env python3
"""Stop Motion Studio - Simplified Working Version"""

import cv2
import numpy as np
import subprocess
import time
import os
import json
from datetime import datetime

GPIOCHIP_NUM = 1
BTN_CAPTURE = 75
BTN_PLAY = 77
BTN_SAVE = 66

PERSISTENT_DIR = "/mnt/dietpi_userdata/stopmotion"
os.makedirs(PERSISTENT_DIR, exist_ok=True)

class GPIO:
    @staticmethod
    def read(chip_num, line):
        try:
            result = subprocess.run(['gpioget', '-c', str(chip_num), str(line)],
                                   capture_output=True, text=True, timeout=0.1)
            return 'active' in result.stdout.strip().lower()
        except:
            return False

print("Opening camera...")
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("ERROR: Camera failed")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Creating window...")
cv2.namedWindow('Stop Motion', cv2.WINDOW_NORMAL)

print("Starting...")
frames = []
playing = False
last_button_time = 0

play_index = 0
last_play_time = time.time()

while True:
    current_time = time.time()
    
    # Check buttons
    if GPIO.read(GPIOCHIP_NUM, BTN_CAPTURE) and current_time - last_button_time > 0.5:
        if not playing:
            ret, frame = cap.read()
            if ret:
                frames.append(frame.copy())
                print(f"Captured frame {len(frames)}")
            last_button_time = current_time
    
    if GPIO.read(GPIOCHIP_NUM, BTN_PLAY) and current_time - last_button_time > 0.5:
        if len(frames) > 0:
            playing = not playing
            print(f"Playing: {playing}")
            play_index = 0
            last_button_time = current_time
    
    if GPIO.read(GPIOCHIP_NUM, BTN_SAVE) and current_time - last_button_time > 0.5:
        if len(frames) > 0:
            print("Saving...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = os.path.join(PERSISTENT_DIR, f"animation_{timestamp}.mp4")
            
            h, w = frames[0].shape[:2]
            out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 10, (w, h))
            for f in frames:
                out.write(f)
            out.release()
            print(f"Saved: {video_path}")
            last_button_time = current_time
    
    # Get display frame
    if playing and len(frames) > 0:
        if current_time - last_play_time >= 0.1:  # 10fps
            display_frame = frames[play_index].copy()
            play_index = (play_index + 1) % len(frames)
            last_play_time = current_time
        else:
            cv2.waitKey(1)
            continue
    else:
        ret, display_frame = cap.read()
        if not ret:
            continue
    
    # Add text overlay
    cv2.putText(display_frame, f"Frames: {len(frames)}", (20, 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    
    if playing:
        cv2.putText(display_frame, "PLAYING", (20, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    # Display
    cv2.imshow('Stop Motion', display_frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Done")
