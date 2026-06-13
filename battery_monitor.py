#!/usr/bin/env python3
import os
import sys
import re
import time
import signal
import select
import shlex
import subprocess
import threading
import logging
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WALLPAPER = SCRIPT_DIR / "battery_full_wallpaper.jpg"
ALERT_SOUND = SCRIPT_DIR / "battery_full_alert.wav"

BATTERY_STATUS = "/sys/class/power_supply/BAT0/status"
AC_ONLINE = "/sys/class/power_supply/AC/online"

POLL_INTERVAL = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("battery_monitor")

alert_processes = []
alert_active = False
lock = threading.Lock()


def get_battery_status():
    try:
        with open(BATTERY_STATUS) as f:
            return f.read().strip()
    except FileNotFoundError:
        log.error("Battery status file not found: %s", BATTERY_STATUS)
        return None


def get_ac_online():
    try:
        with open(AC_ONLINE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        log.error("AC online file not found or invalid: %s", AC_ONLINE)
        return None


def set_volume(percent):
    try:
        result = subprocess.run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("Volume set to %d%% via pactl", percent)
            return
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            ["amixer", "-D", "pulse", "sset", "Master", f"{percent}%"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("Volume set to %d%% via amixer", percent)
            return
    except FileNotFoundError:
        pass

    log.warning("Failed to set volume to %d%% (pactl/amixer)", percent)


def show_wallpaper():
    try:
        proc = subprocess.Popen(
            ["feh", "--fullscreen", "--borderless", "--zoom", "fill",
             str(WALLPAPER)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    except FileNotFoundError:
        log.error("feh not found. Install it: sudo dnf install feh")
        return None


def get_current_volume():
    try:
        result = subprocess.run(
            ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            percent_line = result.stdout.strip().split("\n")[0]
            if "/" in percent_line:
                parts = percent_line.split("/")
                if len(parts) >= 2:
                    try:
                        vol = int(parts[1].strip().rstrip("%"))
                        log.info("Current volume: %d%% (from pactl)", vol)
                        return vol
                    except ValueError:
                        pass
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["amixer", "-D", "pulse", "sget", "Master"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            match = re.search(r'(\d+)%', result.stdout)
            if match:
                vol = int(match.group(1))
                log.info("Current volume: %d%% (from amixer)", vol)
                return vol
    except Exception:
        pass

    log.warning("Could not determine current volume (pactl/amixer)")
    return None


def play_sound_loop():
    try:
        proc = subprocess.Popen(
            ["mpv", "--loop-file=inf", "--no-video", str(ALERT_SOUND)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    except FileNotFoundError:
        pass

    try:
        proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-loop", "0", str(ALERT_SOUND)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    except FileNotFoundError:
        pass

    try:
        proc = subprocess.Popen(
            ["paplay", str(ALERT_SOUND)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    except FileNotFoundError:
        pass

    try:
        proc = subprocess.Popen(
            ["sh", "-c", f'while true; do aplay {shlex.quote(str(ALERT_SOUND))}; done'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    except FileNotFoundError:
        log.error("No audio player found (mpv/ffplay/paplay/aplay)")
        return None


def start_alert():
    global alert_active
    with lock:
        if alert_active:
            return
        alert_active = True

    log.info("Battery full & charger plugged — showing alert")

    current_volume = get_current_volume()
    if current_volume is not None and current_volume < 80:
        log.info("Volume is %d%%, raising to 80%%", current_volume)
        set_volume(80)

    wp = show_wallpaper()
    audio = play_sound_loop()

    with lock:
        alert_processes.clear()
        if wp:
            alert_processes.append(wp)
        if audio:
            alert_processes.append(audio)


def stop_alert():
    global alert_active
    with lock:
        if not alert_active:
            return
        alert_active = False
        for proc in alert_processes:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        alert_processes.clear()
    log.info("Alert stopped — battery unplugged or discharging")


def verify_assets():
    missing = []
    if not WALLPAPER.exists():
        missing.append(str(WALLPAPER))
    if not ALERT_SOUND.exists():
        missing.append(str(ALERT_SOUND))
    if missing:
        log.error("Missing required assets:\n  " + "\n  ".join(missing))
        log.error("Place battery_full_wallpaper.jpg and battery_full_alert.wav in: %s", SCRIPT_DIR)
        return False
    return True


def fake_full():
    if not verify_assets():
        sys.exit(1)
    log.info("Fake-full: simulating battery full alert")
    start_alert()

    with lock:
        wp_proc = alert_processes[0] if alert_processes else None

    log.info("Press Enter or close the wallpaper (q) to stop")
    try:
        while True:
            if wp_proc and wp_proc.poll() is not None:
                log.info("Wallpaper closed — stopping alert")
                break
            if select.select([sys.stdin], [], [], 0.5)[0]:
                sys.stdin.readline()
                break
    except (EOFError, KeyboardInterrupt):
        pass
    stop_alert()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--fake-full":
        fake_full()
        return

    if not verify_assets():
        sys.exit(1)

    log.info("Battery monitor started (polling every %ds)", POLL_INTERVAL)

    was_alerting = False

    while True:
        status = get_battery_status()
        ac = get_ac_online()

        if status is None or ac is None:
            time.sleep(POLL_INTERVAL)
            continue

        should_alert = (status == "Full" and ac == 1)

        if should_alert and not was_alerting:
            start_alert()
            was_alerting = True
        elif not should_alert and was_alerting:
            stop_alert()
            was_alerting = False

        if was_alerting:
            with lock:
                wp_proc = alert_processes[0] if alert_processes else None
            if wp_proc and wp_proc.poll() is not None:
                log.info("Wallpaper closed — stopping alert")
                stop_alert()
                was_alerting = False

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
