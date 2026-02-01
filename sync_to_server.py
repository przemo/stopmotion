#!/usr/bin/env python3
"""Sync saved animations to Jellyfin server via rsync, then trigger library refresh."""

import json
import os
import subprocess
import sys
import glob
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "sync_config.json")
PERSISTENT_DIR = "/mnt/dietpi_userdata/stopmotion"


def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def sync_files(config):
    """Rsync saved animations to remote server, delete source on success."""
    target = config["rsync_target"]
    ssh_key = config.get("rsync_ssh_key", "")

    # Check if there's anything to sync
    mp4s = glob.glob(os.path.join(PERSISTENT_DIR, "animation_*.mp4"))
    frame_dirs = glob.glob(os.path.join(PERSISTENT_DIR, "frames_*"))

    if not mp4s and not frame_dirs:
        print("Nothing to sync")
        return True

    # Rsync with include/exclude to only sync animations, not settings
    cmd = [
        "rsync", "-avz", "--remove-source-files",
        "--include=animation_*.mp4",
        "--include=frames_*/",
        "--include=frames_*/**",
        "--exclude=*",
    ]
    if ssh_key:
        cmd.extend(["-e", f"ssh -i {ssh_key} -o StrictHostKeyChecking=no"])
    cmd.append(PERSISTENT_DIR + "/")
    cmd.append(target)

    print(f"Syncing {len(mp4s)} videos and {len(frame_dirs)} frame dirs...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"Rsync failed: {result.stderr}")
        return False

    # Clean up empty frame directories (--remove-source-files only removes files)
    for d in frame_dirs:
        try:
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        except OSError:
            pass

    print("Sync complete")
    return True


def refresh_jellyfin(config):
    """Trigger Jellyfin library scan via REST API."""
    url = config["jellyfin_url"].rstrip("/")
    api_key = config["jellyfin_api_key"]
    library_id = config.get("jellyfin_library_id", "")

    if library_id:
        endpoint = f"{url}/Items/{library_id}/Refresh"
    else:
        endpoint = f"{url}/Library/Refresh"

    req = urllib.request.Request(endpoint, method="POST")
    req.add_header("X-Emby-Token", api_key)

    try:
        urllib.request.urlopen(req, timeout=10)
        print("Jellyfin library refresh triggered")
        return True
    except Exception as e:
        print(f"Jellyfin refresh failed: {e}")
        return False


def main():
    try:
        config = load_config()
    except FileNotFoundError:
        print(f"Config not found: {CONFIG_FILE}")
        print("Copy sync_config.example.json to sync_config.json and fill in values")
        return 1
    except json.JSONDecodeError as e:
        print(f"Config parse error: {e}")
        return 1

    if not sync_files(config):
        return 1

    refresh_jellyfin(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
