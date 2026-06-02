#!/bin/bash
export DISPLAY=:0

while true; do
    python3 /root/stopmotion/stopmotion.py
    if [ $? -eq 42 ]; then
        cd /root/kiosk-ha && python3 -m http.server 8080 &
        HTTP_PID=$!
        sleep 2
        touchkio --no-sandbox \
            --web-url=http://localhost:8080/kiosk-display.html \
            --web-zoom=1.0 \
            --web-widget=false
        kill $HTTP_PID 2>/dev/null
        break
    fi
    sleep 2
done
