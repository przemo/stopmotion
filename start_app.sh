#!/bin/bash

# Wait for LXDE to fully load
sleep 5

# Set display
export DISPLAY=:0

# Hide mouse cursor (optional)
unclutter -idle 1 -root &

# Run the app
cd /root/stopmotion
python3 stopmotion.py

# If app exits, restart after 3 seconds
while true; do
    sleep 3
    python3 stopmotion.py
done
