# FancyClock

A single-file Flask server that serves two NTP-synchronized clock displays:

- `/` — themed digital clock (animated digits, configurable via `clock_settings.json` or `/settings`)
- `/broadcast` — broadcast-style canvas clock (orange per-second tick ring, copper labels, red lower-hemisphere glow, central `HH:MM:SS`)

Both outputs pull time from the same `/api/time` endpoint, which is driven by `ntplib` against the configured NTP server, so every client on your LAN stays locked to the same reference.

---

## 1. Pull the latest code

```bash
git clone http://<your-git-host>/ShowSysDan/FancyClock.git
cd FancyClock
git pull origin main
```

If you already have a clone:

```bash
cd FancyClock
git fetch origin
git pull origin main
```

To use the broadcast-clock feature branch before it's merged:

```bash
git fetch origin
git checkout claude/add-second-clock-output-RJhWB
git pull
```

## 2. Install dependencies

Requires Python 3.8+.

```bash
pip install flask ntplib
```

If your distro blocks system-wide pip installs, use a virtualenv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask ntplib
```

## 3. Configure

Open `ClockServer.py` and adjust the two settings at the top:

```python
PORT = 5100                    # change to your preferred port
NTP_SERVER = "10.1.248.1"      # your LAN/internet NTP server
NTP_SYNC_INTERVAL = 3600       # re-sync with NTP every hour
```

Display themes/colors for `/` live in `clock_settings.json` and can also be edited live from the `/settings` page.

## 4. Run a test

Start the server:

```bash
python3 ClockServer.py
```

Expected banner (on the configured port):

```
======================================================================
         ULTIMATE PROFESSIONAL DIGITAL CLOCK SERVER
======================================================================
  Clock display:  http://localhost:5100
  Broadcast clock: http://localhost:5100/broadcast
  Settings page:  http://localhost:5100/settings
  NTP server:     10.1.248.1
  NTP offset:     0.42ms
======================================================================
```

Smoke-test the endpoints from another terminal:

```bash
curl -sf http://localhost:5100/                   | head -c 200
curl -sf http://localhost:5100/broadcast          | head -c 200
curl -sf http://localhost:5100/api/time           | python3 -m json.tool
curl -sf http://localhost:5100/api/heartbeat      | python3 -m json.tool
```

`/api/time` should include `"ntp_synced": true` and a small `ntp_offset_ms` value if the NTP server is reachable.

**Lockstep check.** Open `http://<host>:5100/` and `http://<host>:5100/broadcast` side-by-side (two tabs, or two machines). Seconds should tick over simultaneously on both, matching an independent NTP reference (e.g. `date` on the server).

**Offset-skew check.** Set the client machine's system clock forward by 30 s and reload `/broadcast`. It should still display the correct NTP time — the browser's local skew is absorbed by `serverTimeOffset`.

## 5. Change the port to 5700

Edit line 10 of `ClockServer.py`:

```python
PORT = 5700
```

Restart the server (or the systemd service below). Verify:

```bash
curl -sf http://localhost:5700/api/time | python3 -m json.tool
```

## 6. Install as a systemd service

These steps assume Linux with systemd and the repo checked out to your home directory at `~/FancyClock` (e.g. `/home/cuelight/FancyClock`). The service runs as your own login user and invokes **the Python interpreter from the project's virtualenv** — not the system Python — so Flask and `ntplib` are always resolved from `.venv` regardless of what's installed globally.

Throughout this section, replace `cuelight` with your own username if different. You can confirm yours with `whoami` and your home path with `echo $HOME`.

### 6a. Place the code and create the virtualenv

```bash
cd ~
git clone http://<your-git-host>/ShowSysDan/FancyClock.git
cd ~/FancyClock
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install flask ntplib
```

Confirm the venv's python works before moving on:

```bash
~/FancyClock/.venv/bin/python ~/FancyClock/ClockServer.py
```

You should see the startup banner. Press Ctrl+C and continue.

### 6b. Create the unit file

Save as `/etc/systemd/system/fancyclock.service` (this path requires `sudo`):

```ini
[Unit]
Description=FancyClock broadcast clock server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=cuelight
Group=cuelight
WorkingDirectory=/home/cuelight/FancyClock
# IMPORTANT: use the venv's python so Flask/ntplib resolve from .venv,
# not from the system Python. Absolute paths are required — systemd
# does not expand ~ or $HOME in unit files.
ExecStart=/home/cuelight/FancyClock/.venv/bin/python /home/cuelight/FancyClock/ClockServer.py
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Notes on the unit file:

- `User=` / `Group=` must match the owner of `~/FancyClock`. systemd will not read files from another user's home by default.
- `WorkingDirectory=` and `ExecStart=` both use the **absolute** home path — systemd does not expand `~` or `$HOME`.
- `ExecStart` points at `.venv/bin/python`, not `/usr/bin/python3`. This is what makes the service use the virtualenv.

### 6c. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fancyclock.service
sudo systemctl status fancyclock.service
```

### 6d. Verify the service is using the venv

```bash
systemctl show fancyclock.service -p ExecStart --value
```

The output should contain `/home/cuelight/FancyClock/.venv/bin/python` — if it shows `/usr/bin/python3` instead, re-edit the unit file and run `sudo systemctl daemon-reload && sudo systemctl restart fancyclock.service`.

### 6e. Watch logs

```bash
sudo journalctl -u fancyclock.service -f
```

You should see the startup banner (with port 5700 if you set it) and periodic `NTP sync successful. Offset: ...ms` lines.

### 6f. Update after a `git pull`

```bash
cd ~/FancyClock
git pull origin main
# If dependencies changed:
.venv/bin/pip install -U flask ntplib
sudo systemctl restart fancyclock.service
```

## Endpoints reference

| Path             | Purpose                                                 |
| ---------------- | ------------------------------------------------------- |
| `/`              | Themed digital clock display                            |
| `/broadcast`     | Broadcast-style canvas clock display                    |
| `/settings`      | Live editor for the `/` clock theme and layout          |
| `/api/time`      | NTP-synced timestamp (JSON) — consumed by both clocks   |
| `/api/heartbeat` | Liveness probe                                          |
| `/api/settings`  | `GET` current settings; `POST` to update                |

## Troubleshooting

- **`NTP sync failed: No response received`** — `NTP_SERVER` is unreachable. The server still runs on system time; fix the network route or point `NTP_SERVER` at a reachable host.
- **Clocks drift between tabs** — confirm both tabs see `"ntp_synced": true` from `/api/time`. The broadcast clock re-syncs every 10 s; after the first sync, drift should be under one frame.
- **Port already in use** — another process owns the port. Change `PORT` or stop the other process (`ss -ltnp | grep :5700`).
