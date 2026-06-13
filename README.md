# Battery Monitor

Alerts you with a full-screen wallpaper and looping sound when the laptop battery is fully charged while the charger is still plugged in.

## Quick Install

```bash
curl -fsSL 'https://raw.githubusercontent.com/electrodragon/battery-monitor/main/install_battery_monitor.sh' | sudo bash
```

After install, use `battery-monitor <command>` to control the service.

## Requirements

- **feh** — displays wallpaper (`sudo dnf install feh`)
- **mpv** or **ffplay** or **paplay** — plays alert sound
- **pactl** or **amixer** — sets volume to 80% on alert

## Usage

```
battery-monitor [command]
```

| Command | Description |
|---|---|
| `help` | Show help message |
| `run` | Run in foreground (testing) |
| `install` | Install system-wide service (requires sudo) |
| `uninstall` | Remove service (requires sudo) |
| `start` | Start via systemctl |
| `stop` | Stop via systemctl |
| `restart` | Restart via systemctl |
| `status` | Check if service is running |
| `logs` | Follow journalctl logs |

## Assets

Place these in the project directory (or `/opt/battery-monitor/` after install):

- `battery_full_wallpaper.jpg` — full-screen background image
- `battery_full_alert.wav` — looping alert sound

## How it works

The monitor polls `/sys/class/power_supply/BAT0/status` and `/sys/class/power_supply/AC/online` every 5 seconds. When `status == "Full"` and AC is plugged in, it:

1. Raises volume to 80%
2. Shows the wallpaper full-screen via `feh`
3. Plays the alert sound in a loop

All alerts stop automatically when the charger is unplugged.
