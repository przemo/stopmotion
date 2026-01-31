#!/usr/bin/env python3
import cv2
import time

print("Opening camera...")
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("ERROR: Camera failed")
    exit(1)

print("Creating window...")
cv2.namedWindow('Test', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('Test', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("Starting loop...")
for i in range(300):  # 10 seconds at 30fps
    ret, frame = cap.read()
    if ret:
        # Draw something to verify it's working
        cv2.putText(frame, f"Frame {i}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
        cv2.imshow('Test', frame)
        print(f"Displayed frame {i}")
    else:
        print(f"Failed to read frame {i}")
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    time.sleep(0.033)

print("Cleanup...")
cap.release()
cv2.destroyAllWindows()

