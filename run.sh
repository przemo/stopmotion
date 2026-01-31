#!/bin/bash
# Stop any existing X
pkill X
sleep 1

# Start X server
X :0 vt1 &
sleep 3

# Run app
export DISPLAY=:0
cd /root/stopmotion
python3 stopmotion.py
