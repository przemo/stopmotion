#!/bin/bash

echo "Stop Motion Studio Launcher"
echo "============================"

# Kill existing X and app
pkill stopmotion.py
pkill X
sleep 2

# Start X server
echo "Starting X server..."
X :0 vt1 -s 0 dpms &
sleep 3

# Verify X started
if ! pgrep -x "X" > /dev/null; then
    echo "ERROR: X server failed to start"
    exit 1
fi

echo "X server running"

# Run app
export DISPLAY=:0
cd /root/stopmotion
echo "Starting Stop Motion Studio..."
python3 stopmotion.py

# Cleanup on exit
pkill X
