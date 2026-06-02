#!/bin/bash
set -e
REPO=/root/stopmotion

cp $REPO/stopmotion.service /etc/systemd/system/stopmotion.service
cp $REPO/touchkiosk.service /etc/systemd/system/touchkiosk.service

# Protect sshd from OOM killer
mkdir -p /etc/systemd/system/ssh.service.d
cat > /etc/systemd/system/ssh.service.d/oom-protect.conf << 'EOF'
[Service]
OOMScoreAdjust=-500
EOF

systemctl daemon-reload
systemctl enable stopmotion.service
systemctl enable touchkiosk.service
echo "Done. Services installed."
