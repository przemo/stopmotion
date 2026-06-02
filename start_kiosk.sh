#!/bin/bash
export DISPLAY=:0
exec firefox --kiosk --no-remote file:///root/kiosk-ha/kiosk-display.html
