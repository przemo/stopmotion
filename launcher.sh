#!/bin/bash
export DISPLAY=:0
LOG=/tmp/launcher.log

while true; do
    python3 /root/stopmotion/stopmotion.py
    EXIT_CODE=$?
    echo "$(date): stopmotion exited with code $EXIT_CODE" >> $LOG
    if [ $EXIT_CODE -eq 42 ]; then
        echo "$(date): launching kiosk" >> $LOG
        cd /root/kiosk-ha && python3 -m http.server 8080 &
        HTTP_PID=$!
        sleep 2
        touchkio --no-sandbox \
            --web-url=http://localhost:8080/kiosk-display.html \
            --web-zoom=1.0 \
            --web-widget=false
        echo "$(date): touchkio exited with $?" >> $LOG
        kill $HTTP_PID 2>/dev/null
        break
    fi
    sleep 2
done
