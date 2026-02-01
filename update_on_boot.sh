#!/bin/bash
# Pull latest code from main branch at boot.
# Install: sudo cp stopmotion-update.service /etc/systemd/system/
#          sudo systemctl enable stopmotion-update.service

REPO_DIR="$(dirname "$(readlink -f "$0")")"
BRANCH="main"
LOG="/var/log/stopmotion-update.log"
MAX_RETRIES=5
RETRY_DELAY=10

exec >> "$LOG" 2>&1
echo "=== $(date) ==="

cd "$REPO_DIR" || { echo "Repo dir not found: $REPO_DIR"; exit 1; }

# Wait for network
for i in $(seq 1 $MAX_RETRIES); do
    if ping -c 1 -W 3 github.com > /dev/null 2>&1; then
        break
    fi
    echo "Waiting for network (attempt $i/$MAX_RETRIES)..."
    sleep $RETRY_DELAY
done

git fetch origin "$BRANCH" && git checkout "$BRANCH" && git pull origin "$BRANCH"
echo "Update complete (exit code: $?)"
