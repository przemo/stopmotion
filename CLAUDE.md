# Stop Motion Studio — Project Notes

## Hardware
- **Device**: Orange Pi Zero 2W (aarch64, 1GB RAM)
- **OS**: DietPi (Debian Trixie)
- **Display**: 1024×600 touchscreen (HDMI)
- **Camera**: USB webcam (OpenCV VideoCapture)
- **GPIO buttons**: 5 physical buttons via `gpioget` (chip 1)
  - CAPTURE: GPIO 268 (Pin 11)
  - PLAY:    GPIO 256 (Pin 29)
  - REWIND:  GPIO 261 (Pin 15)
  - CLEAR:   GPIO 267 (Pin 32)
  - SAVE:    GPIO 271 (Pin 31)
- **SSH**: `root@192.168.1.190`

## Architecture

### Boot sequence
1. DietPi starts LXDE desktop (xinit → lxsession → openbox)
2. LXDE autostart runs `/root/.config/autostart/stopmotion.desktop`
3. Desktop entry executes `/root/stopmotion/launcher.sh`
4. `launcher.sh` loops: runs `stopmotion.py`, catches exit code 42 → launches TouchKio

**Critical**: stopmotion.service (systemd) is **disabled**. LXDE autostart is the sole launcher.
Do NOT re-enable stopmotion.service — it conflicts with the LXDE X session (:0 vt1).

### Kiosk mode switch (one-way)
- User opens Settings menu (hold status bar 3s, or PLAY+SAVE for 2s)
- Selects **Kiosk** → `stopmotion.py` sets `exit_to_kiosk = True`, exits with `sys.exit(42)`
- `launcher.sh` catches exit code 42:
  1. Starts `python3 -m http.server 8080` in `/root/kiosk-ha/`
  2. Launches `touchkio --no-sandbox --web-url=http://localhost:8080/kiosk-display.html`
  3. When TouchKio exits: kills HTTP server, breaks loop (no return to stopmotion)
- On next reboot: autostart runs `launcher.sh` → stopmotion starts normally

### File layout on device
```
/root/stopmotion/          ← git repo (github.com/przemo/stopmotion)
  launcher.sh              ← main supervisor (LXDE autostart entry point)
  stopmotion.py            ← main app
  start_app.sh             ← legacy launcher (NOT used, kept for reference)
  install.sh               ← run after git pull when service files change
  stopmotion.service       ← systemd unit (DISABLED, kept in repo for reference)
  touchkiosk.service       ← systemd unit (DISABLED)
  sync_to_server.py        ← rsync saved animations to Jellyfin + trigger refresh
  sync_config.json         ← rsync/Jellyfin config (NOT in git, local only)

/root/kiosk-ha/            ← NOT in git, copied via scp
  kiosk-display.html       ← custom HA dashboard (standalone HTML)

/root/.config/autostart/
  stopmotion.desktop       ← LXDE autostart entry → launcher.sh
```

## Deployment workflow

```bash
# On dev machine (this machine):
git -C /home/przemek/stopmotion add <files>
git -C /home/przemek/stopmotion commit -m "..."
git -C /home/przemek/stopmotion push   # remote: git@github.com:przemo/stopmotion.git

# On Pi:
ssh root@192.168.1.190
cd /root/stopmotion && git pull

# Only needed when service files change:
bash install.sh

# To apply Python changes without reboot:
pkill -f stopmotion.py   # launcher.sh will restart it after 2s
```

**Auto-pull at boot**: `update_on_boot.sh` + `stopmotion-update.service` pull from main at boot (if network is available). May be installed — check with `systemctl status stopmotion-update.service`.

## SSH stability
- **Root cause**: tight OpenCV loop consumed 100%+ CPU, starving sshd under memory pressure
- **Fixes applied**:
  - `cap.set(cv2.CAP_PROP_FPS, 20)` — camera capped at 20fps
  - `cv2.waitKey(33)` instead of `waitKey(1)` — 30fps display cap
  - `/etc/systemd/system/ssh.service.d/oom-protect.conf` — `OOMScoreAdjust=-500` protects sshd
  - stopmotion.service has `MemoryMax=700M`, `Nice=10`, `OOMScoreAdjust=500` (kills app first)

**Known issue**: SSH drops briefly when `stopmotion.py` is killed abruptly (SIGKILL/pkill).
Use graceful restart: `pkill -TERM -f stopmotion.py` or just reboot.

## Saved animations
- Saved to: `/mnt/dietpi_userdata/stopmotion/animation_YYYYMMDD_HHMMSS.mp4`
- Format: H.264 MP4 with silent AAC audio (Jellyfin compatible)
- Auto-synced to Jellyfin via `sync_to_server.py` (reads `sync_config.json`)

## kiosk-display.html
Standalone HTML dashboard connecting to Home Assistant via WebSocket.
- **HA WS**: `wss://ha.local.pmjlab.org/api/websocket`
- **Two modes** (auto-switches based on `sensor.flight_tracker_flight_status`):
  - **Home mode**: clock, weather (OpenWeatherMap), indoor temps (4 rooms), security (locks/alarm/garage/water), presence (Przemek/Tomek), outdoor stats (rain/electricity/water)
  - **Flight mode**: ADS-B radar, speed gauge, altitude bar, ETA/delay/distance

Key entities:
```
sensor.flight_tracker_*         sensor.openweathermap_*
sensor.main_floor_temperature   sensor.upstairs_temperature
sensor.kids_room_temperature    sensor.basement_wall_thermohygrometer_h5072_75_tempc
lock.2375_golden_eagle_way_front_door   lock.back_door_lock
alarm_control_panel.2375_golden_eagle_way_alarm_control_panel
cover.garage_door_opener_door   sensor.flume_sensor_eagle_way_current
person.przemek  person.tomek    sensor.daily_rainfall
sensor.electricity_day_usage    sensor.water_day_consumption
```

## HA Lovelace dashboard
A native HA dashboard `home-display` was also created (url_path: `home-display`).
TouchKio can be pointed at `https://ha.local.pmjlab.org/home-display?kiosk` instead
of the local HTML file if preferred.

## TouchKio
- Installed: `/usr/bin/touchkio` (v1.4.3, arm64 deb)
- Must run with `--no-sandbox` (running as root)
- Config: `~/.config/touchkio/Arguments.json`
- Systemd service (`touchkiosk.service`) exists but is **disabled** — managed by launcher.sh
