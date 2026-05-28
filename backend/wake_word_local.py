"""
Wake word detector using local-wake library
Detects "Hey Jarvis" and triggers voice assistant
"""
import time
import logging
import lwake
from typing import Callable, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalWakeWordDetector:
    """Wake word detector using local-wake with debouncing"""

    def __init__(
        self,
        reference_dir: str = "wake_word_refs",
        threshold: float = 0.22,
        buffer_size: float = 2.0,
        slide_size: float = 0.25,
        debounce_seconds: float = 2.0
    ):
        """
        Initialize wake word detector

        Args:
            reference_dir: Directory containing reference .wav files
            threshold: Detection threshold (lower = more sensitive)
            buffer_size: Audio buffer size in seconds
            slide_size: Sliding window size in seconds
            debounce_seconds: Minimum time between detections
        """
        self.reference_dir = Path(reference_dir)
        self.threshold = threshold
        self.buffer_size = buffer_size
        self.slide_size = slide_size
        self.debounce_seconds = debounce_seconds

        self.last_detection_time = 0
        self.callback: Optional[Callable] = None
        self.running = False

        logger.info(f"LocalWakeWordDetector initialized")
        logger.info(f"Reference dir: {self.reference_dir.absolute()}")
        logger.info(f"Threshold: {threshold}, Debounce: {debounce_seconds}s")

    def set_callback(self, callback: Callable):
        """Set callback function to be called when wake word is detected"""
        self.callback = callback

    def _handle_detection(self, detection: dict, stream):
        """Internal handler for wake word detection with debouncing"""
        current_time = time.time()
        time_since_last = current_time - self.last_detection_time

        # Debouncing: ignore detections too close together
        if time_since_last < self.debounce_seconds:
            logger.debug(f"Ignoring detection (debounce): {time_since_last:.2f}s since last")
            return

        self.last_detection_time = current_time

        logger.info(f"Wake word detected! Distance: {detection['distance']:.4f}")

        # Call user's callback if set
        if self.callback:
            try:
                self.callback(detection)
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}", exc_info=True)

    def start(self):
        """Start listening for wake word (blocking)"""
        if not self.reference_dir.exists():
            raise FileNotFoundError(f"Reference directory not found: {self.reference_dir}")

        ref_files = list(self.reference_dir.glob("*.wav"))
        if not ref_files:
            raise FileNotFoundError(f"No .wav files found in {self.reference_dir}")

        logger.info(f"Starting wake word detection with {len(ref_files)} reference files")
        logger.info("Listening for 'Hey Jarvis'...")

        self.running = True

        try:
            lwake.listen(
                str(self.reference_dir),
                threshold=self.threshold,
                method="embedding",
                buffer_size=self.buffer_size,
                slide_size=self.slide_size,
                callback=self._handle_detection
            )
        except KeyboardInterrupt:
            logger.info("Wake word detection stopped by user")
        except Exception as e:
            logger.error(f"Wake word detection error: {e}", exc_info=True)
        finally:
            self.running = False

    def stop(self):
        """Stop listening (not implemented in lwake - use Ctrl+C)"""
        self.running = False
        logger.info("Stop requested (will stop after current audio chunk)")


def test_detector():
    """Test the wake word detector"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_wake_word_detected(detection: dict):
        print(f"\n[WAKE WORD DETECTED!]")
        print(f"  Matched: {detection['wakeword']}")
        print(f"  Distance: {detection['distance']:.4f}")
        print(f"  Timestamp: {detection['timestamp']}")
        print("  [Your voice assistant would activate here]\n")

    detector = LocalWakeWordDetector(
        reference_dir="wake_word_refs",
        threshold=0.10,
        debounce_seconds=2.0  # Only trigger once every 2 seconds
    )

    detector.set_callback(on_wake_word_detected)

    print("\n" + "="*60)
    print("Wake Word Detection Test")
    print("="*60)
    print("Say 'Hey Jarvis' to test detection")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    detector.start()


if __name__ == "__main__":
    test_detector()
