#!/bin/bash
export DISPLAY=:0

while true; do
    python3 /root/stopmotion/stopmotion.py
    if [ $? -eq 42 ]; then
        touchkio --no-sandbox \
            --web-url=https://ha.local.pmjlab.org/home-display?kiosk \
            --web-zoom=1.0 \
            --web-widget=false
        break
    fi
    sleep 2
done
