import time
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
import os
import sys

# ========================================
# Auto-detect Configuration
# ========================================
def find_clawx_exe():
    """Auto-detect ClawX installation"""
    possible_paths = [
        r"C:\Program Files\ClawX\ClawX.exe",
        r"C:\Program Files (x86)\ClawX\ClawX.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\ClawX\ClawX.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\ClawX\ClawX.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\ClawX\ClawX.exe"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def find_openclaw_cmd():
    """Auto-detect openclaw.cmd"""
    clawx_exe = find_clawx_exe()
    if clawx_exe:
        clawx_dir = os.path.dirname(clawx_exe)
        possible_paths = [
            os.path.join(clawx_dir, "resources", "cli", "openclaw.cmd"),
            os.path.join(clawx_dir, "resources", "bin", "openclaw.cmd"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
    return None

def detect_port():
    """Auto-detect OpenClaw port from config"""
    config_paths = [
        os.path.expandvars(r"%USERPROFILE%\.openclaw\openclaw.json"),
        os.path.expandvars(r"%APPDATA%\openclaw\openclaw.json"),
    ]
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Simple parse to find port
                    if '"port"' in content:
                        import json
                        config = json.loads(content)
                        if "gateway" in config and "port" in config["gateway"]:
                            return config["gateway"]["port"]
            except:
                pass
    return 18789  # Default port

# ========================================
# Configuration (auto-detected)
# ========================================
PORT = detect_port()
URL = "http://127.0.0.1:{}/".format(PORT)
INTERVAL_SEC = 10
FAIL_THRESHOLD = 3
RESTART_COOLDOWN_SEC = 60
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "clawx_watchdog.log")
CLAWX_EXE = find_clawx_exe()
OPENCLAW_CMD = find_openclaw_cmd()
MAX_RESTART_ATTEMPTS = 3
MAX_LOG_SIZE_MB = 1
MAX_LOG_LINES = 500
# ========================================

def log(msg):
    line = "[{}] {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

def check_and_clean_log():
    """Check log file size and clean if too large"""
    try:
        if not os.path.exists(LOG_FILE):
            return
        file_size = os.path.getsize(LOG_FILE)
        max_size_bytes = MAX_LOG_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            log("Log file too large ({}MB), cleaning...".format(round(file_size / 1024 / 1024, 2)))
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            if len(lines) > MAX_LOG_LINES:
                lines = lines[-MAX_LOG_LINES:]
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines)
            log("Log cleaned, kept last {} lines".format(len(lines)))
    except Exception as e:
        print("[{}] Failed to clean log: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e))

def check_url(url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clawx-watchdog/3.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 600
    except:
        return False

def is_clawx_running():
    """Check if ClawX process is running"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ClawX.exe"],
            capture_output=True, text=True, timeout=10
        )
        return "ClawX.exe" in result.stdout
    except:
        return False

def restart_gateway():
    """Restart OpenClaw gateway (stop then start)"""
    if not OPENCLAW_CMD:
        log("ERROR: openclaw.cmd not found!")
        return False

    log("Restarting gateway (stop + start)...")

    # Step 1: Stop gateway
    try:
        log("Stopping gateway...")
        result = subprocess.run(
            [OPENCLAW_CMD, "gateway", "stop"],
            capture_output=True, text=True, timeout=15
        )
        log("Gateway stop -> code={}".format(result.returncode))
    except subprocess.TimeoutExpired:
        log("Gateway stop timed out, killing gateway process...")
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True, timeout=10)
    except Exception as e:
        log("Gateway stop error: {}".format(e))

    time.sleep(5)

    # Step 2: Start gateway
    try:
        log("Starting gateway...")
        result = subprocess.run(
            [OPENCLAW_CMD, "gateway", "start"],
            capture_output=True, text=True, timeout=15
        )
        log("Gateway start -> code={}".format(result.returncode))
        if result.stdout:
            log("Output: {}".format(result.stdout.strip()[:200]))
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log("Gateway start timed out")
        return False
    except Exception as e:
        log("Gateway start failed: {}".format(e))
        return False

def kill_clawx():
    """Kill ClawX process"""
    log("Killing ClawX...")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ClawX.exe"], capture_output=True, timeout=30)
        time.sleep(3)
        log("ClawX killed")
    except Exception as e:
        log("Kill failed: {}".format(e))

def start_clawx():
    """Start ClawX"""
    if not CLAWX_EXE:
        log("ERROR: ClawX.exe not found!")
        return

    log("Starting ClawX...")
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", CLAWX_EXE],
            shell=False
        )
        log("ClawX started (independent process)")
        time.sleep(5)
    except Exception as e:
        log("Start failed: {}".format(e))

def restart_clawx_and_gateway():
    """Restart ClawX and gateway"""
    log("=" * 50)
    log("FULL RESTART: ClawX + Gateway")
    log("=" * 50)
    kill_clawx()
    time.sleep(5)
    start_clawx()
    time.sleep(10)
    restart_gateway()

def main():
    check_and_clean_log()

    log("=" * 50)
    log("ClawX Watchdog v3.0 (Portable)")
    log("=" * 50)

    # Show detected paths
    log("Auto-detected paths:")
    log("  ClawX: {}".format(CLAWX_EXE if CLAWX_EXE else "NOT FOUND"))
    log("  OpenClaw CMD: {}".format(OPENCLAW_CMD if OPENCLAW_CMD else "NOT FOUND"))
    log("  Port: {}".format(PORT))

    if not CLAWX_EXE:
        log("ERROR: ClawX not found! Please install ClawX first.")
        log("Checked paths:")
        for p in [
            r"C:\Program Files\ClawX\ClawX.exe",
            r"C:\Program Files (x86)\ClawX\ClawX.exe",
        ]:
            log("  {}".format(p))
        return

    log("Target: {}".format(URL))
    log("Strategy:")
    log("  1. Check ClawX process first")
    log("  2. Restart gateway if ClawX running")
    log("  3. Restart ClawX + gateway if needed")
    log("Max attempts: {}".format(MAX_RESTART_ATTEMPTS))
    log("Log cleanup: {}MB max, keep last {} lines".format(MAX_LOG_SIZE_MB, MAX_LOG_LINES))
    log("=" * 50)

    fails = 0
    last_restart = 0.0
    restart_attempts = 0

    while True:
        try:
            if check_url(URL):
                if fails > 0:
                    log("Connection restored!")
                    fails = 0
                    restart_attempts = 0
                else:
                    log("Connection OK")
            else:
                fails += 1
                log("Connection failed ({}/{})".format(fails, FAIL_THRESHOLD))

                if fails >= FAIL_THRESHOLD:
                    now = time.time()

                    # Check cooldown
                    if (now - last_restart) < RESTART_COOLDOWN_SEC:
                        log("In cooldown ({}s remaining)".format(
                            int(RESTART_COOLDOWN_SEC - (now - last_restart))))
                        time.sleep(5)
                        continue

                    # Check max attempts
                    if restart_attempts >= MAX_RESTART_ATTEMPTS:
                        log("Max attempts reached, stopping")
                        log("Please check ClawX manually")
                        break

                    # Step 1: Check if ClawX is running
                    if not is_clawx_running():
                        log("ClawX process NOT running, starting ClawX...")
                        start_clawx()

                        log("Waiting for ClawX to start (up to 30s)...")
                        for i in range(6):
                            time.sleep(5)
                            if check_url(URL):
                                log("Connection restored! ClawX auto-recovered")
                                last_restart = time.time()
                                fails = 0
                                restart_attempts = 0
                                break
                        else:
                            log("ClawX started but not connected, restarting gateway...")
                            restart_gateway()
                            last_restart = time.time()
                            fails = 0
                        continue

                    # Step 2: ClawX is running, try gateway restart
                    log("ClawX is running, attempting gateway restart...")
                    if restart_gateway():
                        log("Gateway restart completed, monitoring...")
                        last_restart = time.time()
                        fails = 0

                        log("Waiting up to 15s for gateway to start...")
                        for i in range(3):
                            time.sleep(5)
                            if check_url(URL):
                                log("Connection restored after gateway restart!")
                                break
                        else:
                            log("Gateway restart didn't help")
                    else:
                        log("Gateway restart failed, restarting ClawX...")
                        restart_clawx_and_gateway()
                        restart_attempts += 1
                        last_restart = time.time()
                        fails = 0
                        log("Restart attempt {}/{}".format(restart_attempts, MAX_RESTART_ATTEMPTS))

            time.sleep(INTERVAL_SEC)

        except KeyboardInterrupt:
            log("Stopped by user")
            break
        except Exception as e:
            log("Error: {}".format(e))
            time.sleep(5)

    log("Watchdog terminated")

if __name__ == "__main__":
    main()
