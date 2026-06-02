#!/bin/bash
set -e
REPO=/root/stopmotion

cp $REPO/stopmotion.service /etc/systemd/system/stopmotion.service
cp $REPO/touchkiosk.service /etc/systemd/system/touchkiosk.service
systemctl daemon-reload
systemctl enable stopmotion.service
systemctl enable touchkiosk.service
echo "Done. Services installed."
