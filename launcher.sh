#!/bin/bash
export DISPLAY=:0

while true; do
    python3 /root/stopmotion/stopmotion.py
    if [ $? -eq 42 ]; then
        firefox --kiosk --no-remote file:///root/kiosk-ha/kiosk-display.html
        break
    fi
    sleep 2
done
