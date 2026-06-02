#!/bin/bash
export DISPLAY=:0
exec chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --no-sandbox \
  file:///root/kiosk-ha/kiosk-display.html
