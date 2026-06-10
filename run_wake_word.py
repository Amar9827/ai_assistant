"""
Always-On Wake Word Launcher

Listens for "Hey Jarvis" continuously. On detection:
  1. Starts backend server + frontend dev server (if not already running)
  2. Waits for backend to be ready
  3. Triggers the wake word endpoint so frontend auto-starts recording

Idle behavior is controlled by backend configuration.
Wake word listener keeps running and will relaunch servers on next detection.
"""
import logging
import time
import sys
import subprocess
import socket
import os
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from wake_word.detector import OpenWakeWordDetector

PROJECT_ROOT = Path(__file__).parent
BACKEND_URL = "http://localhost:8000"
IDLE_TIMEOUT_SECONDS = int(os.getenv("IDLE_TIMEOUT_SECONDS", "0"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Subprocess handles for managed servers
_backend_proc = None
_frontend_proc = None


def _is_backend_running() -> bool:
    """Check if backend server is responding."""
    try:
        r = requests.get(f"{BACKEND_URL}/", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def _is_port_in_use(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Return True when TCP port is already bound by any process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _start_backend():
    """Launch backend server as a subprocess."""
    global _backend_proc
    # Clean up dead process handle
    if _backend_proc and _backend_proc.poll() is not None:
        _backend_proc = None

    if _backend_proc is not None:
        return  # already running

    # Reuse existing backend instance if port is already occupied.
    if _is_port_in_use(port=8000):
        print("  [INFO] Port 8000 already in use; reusing existing backend")
        return

    print("  [LAUNCH] Starting backend server...")
    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    _backend_proc = subprocess.Popen(
        [str(venv_python), str(PROJECT_ROOT / "backend" / "server.py")],
        cwd=str(PROJECT_ROOT),
    )
    print(f"  [LAUNCH] Backend PID: {_backend_proc.pid}")


def _start_frontend():
    """Launch Vite dev server as a subprocess."""
    global _frontend_proc
    # Clean up dead process handle
    if _frontend_proc and _frontend_proc.poll() is not None:
        _frontend_proc = None

    if _frontend_proc is not None:
        return  # already running

    print("  [LAUNCH] Starting frontend dev server...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    _frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(PROJECT_ROOT / "frontend"),
    )
    print(f"  [LAUNCH] Frontend PID: {_frontend_proc.pid}")


def _wait_for_backend(timeout: float = 15.0) -> bool:
    """Poll backend health endpoint until it responds or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_backend_running():
            return True

        # If the launched backend exits early (e.g., bind error), fail fast.
        if _backend_proc and _backend_proc.poll() is not None:
            return _is_backend_running()

        time.sleep(0.5)
    return False


def _cleanup_servers():
    """Terminate any running server subprocesses and their child process trees."""
    global _backend_proc, _frontend_proc
    if _backend_proc and _backend_proc.poll() is None:
        print("[CLEANUP] Stopping backend server...")
        _kill_proc_tree(_backend_proc.pid)
    _backend_proc = None
    if _frontend_proc and _frontend_proc.poll() is None:
        print("[CLEANUP] Stopping frontend server...")
        _kill_proc_tree(_frontend_proc.pid)
    _frontend_proc = None


def _kill_proc_tree(pid: int):
    """Kill a process and all its children (Windows: taskkill /T)."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
            )
        else:
            import signal
            import os
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        pass


def on_wake_word_detected(detection: dict):
    """Called when 'Hey Jarvis' is detected."""
    print("\n" + "="*60)
    print("WAKE WORD DETECTED!")
    print(f"  Model: {detection['model']}")
    print(f"  Score: {detection['score']:.4f}")
    print("="*60)

    # 1. Ensure servers are running
    backend_was_running = _is_backend_running()

    if not backend_was_running:
        _start_backend()
        _start_frontend()
        print("  [WAIT] Waiting for backend to be ready...")
        if not _wait_for_backend():
            print("  [ERROR] Backend failed to start within 15s")
            print("="*60 + "\n")
            return
        print("  [OK] Backend is ready")
    else:
        # Backend running — ensure frontend is too
        _start_frontend()

    # 2. Trigger wake word endpoint
    try:
        response = requests.post(
            f"{BACKEND_URL}/wake-word/trigger",
            timeout=2.0
        )

        if response.status_code == 200:
            result = response.json()
            clients = result.get("clients_notified", 0)
            print(f"  [OK] Backend notified ({clients} clients)")
        else:
            print(f"  [WARN] Backend returned status {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("  [ERROR] Could not connect to backend server")
    except Exception as e:
        print(f"  [ERROR] Failed to trigger backend: {e}")

    print("="*60 + "\n")


def main():
    """Main entry point — always-on wake word listener."""
    detector = OpenWakeWordDetector(
        threshold=0.4,
        debounce_seconds=3.0
    )

    detector.set_callback(on_wake_word_detected)

    print("\n" + "="*60)
    print("AI Voice Assistant — Wake Word Listener")
    print("="*60)
    print("Status: ACTIVE (always-on)")
    print("Wake Word: 'Hey Jarvis'")
    print("Threshold: 0.4")
    print("Debounce: 3.0 seconds")
    if IDLE_TIMEOUT_SECONDS > 0:
        print(f"Idle Timeout: {IDLE_TIMEOUT_SECONDS} seconds (servers auto-stop)")
    else:
        print("Idle Timeout: disabled")
    print("="*60)
    print()
    print("Say 'Hey Jarvis' — servers launch automatically")
    print("Press Ctrl+C to stop")
    print()
    print("="*60 + "\n")

    try:
        detector.start()
        while True:
            time.sleep(0.5)
            # If backend died (idle timeout), also kill frontend
            if _backend_proc and _backend_proc.poll() is not None:
                _cleanup_servers()
    except KeyboardInterrupt:
        detector.stop()
        _cleanup_servers()
        print("\nWake Word Listener stopped")
    except Exception as e:
        detector.stop()
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
