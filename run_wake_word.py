"""
Production Wake Word Service
Runs alongside your existing backend server and triggers it when wake word is detected
"""
import logging
import sys
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from backend.wake_word_local import LocalWakeWordDetector

# Backend server URL
BACKEND_URL = "http://localhost:8000"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def on_wake_word_detected(detection: dict):
    """Called when 'Hey Jarvis' is detected"""
    print("\n" + "="*60)
    print("WAKE WORD DETECTED!")
    print(f"  Matched: {detection['wakeword']}")
    print(f"  Distance: {detection['distance']:.4f}")
    print("="*60)

    # Trigger backend server
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
        print("         Make sure backend is running on port 8000")
    except Exception as e:
        print(f"  [ERROR] Failed to trigger backend: {e}")

    print("="*60 + "\n")


def main():
    """Main entry point"""
    detector = LocalWakeWordDetector(
        reference_dir="wake_word_refs",
        threshold=0.22,
        debounce_seconds=2.0
    )

    detector.set_callback(on_wake_word_detected)

    print("\n" + "="*60)
    print("Wake Word Detection Service")
    print("="*60)
    print("Status: ACTIVE")
    print("Wake Word: 'Hey Jarvis'")
    print("Threshold: 0.22")
    print("Debounce: 2.0 seconds")
    print("="*60)
    print()
    print("Say 'Hey Jarvis' to test detection")
    print("Press Ctrl+C to stop")
    print()
    print("="*60 + "\n")

    try:
        detector.start()
    except KeyboardInterrupt:
        print("\n\nWake Word Service stopped")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
