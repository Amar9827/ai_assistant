import sounddevice as sd
import numpy as np
from typing import Optional
from config.settings import Settings

# Try to import webrtcvad, fallback to simple VAD if not available
try:
    import webrtcvad
    HAS_WEBRTC_VAD = True
except (ImportError, ModuleNotFoundError):
    HAS_WEBRTC_VAD = False
    print("Warning: webrtcvad not available, using simple volume-based VAD")

class AudioRecorder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sample_rate = settings.SAMPLE_RATE
        self.channels = settings.CHANNELS
        self.recording = []

    def record(self, duration: int = 5) -> np.ndarray:
        """Record audio for specified duration"""
        print(f"Recording for {duration} seconds...")
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16'
        )
        sd.wait()
        return audio.flatten()

    def record_with_vad(self,
                        vad_aggressiveness: int = 2,
                        silence_duration: float = 1.0,
                        max_duration: int = 30,
                        min_speech_duration: float = 0.5,
                        volume_threshold: float = 0.005) -> np.ndarray:
        """
        Record with Voice Activity Detection

        Uses WebRTC VAD if available, otherwise falls back to volume-based detection.

        Args:
            vad_aggressiveness: 0-3, higher = more aggressive filtering (2 is balanced)
            silence_duration: seconds of silence before stopping
            max_duration: maximum recording duration in seconds
            min_speech_duration: minimum speech before considering valid
            volume_threshold: volume threshold for simple VAD (if WebRTC unavailable)
        """

        # Use WebRTC VAD if available, otherwise simple volume-based VAD
        if HAS_WEBRTC_VAD:
            return self._record_with_webrtc_vad(
                vad_aggressiveness, silence_duration, max_duration, min_speech_duration
            )
        else:
            return self._record_with_simple_vad(
                volume_threshold, silence_duration, max_duration, min_speech_duration
            )

    def _record_with_simple_vad(self,
                                 volume_threshold: float = 0.01,
                                 silence_duration: float = 1.0,
                                 max_duration: int = 30,
                                 min_speech_duration: float = 0.5) -> np.ndarray:
        """
        Simple volume-based Voice Activity Detection (fallback)

        Uses dynamic threshold based on speaking volume to handle background noise
        """
        print("🎤 Listening... (speak now)")

        recording = []
        frame_duration_ms = 100  # Check every 100ms
        frames_per_check = int(self.sample_rate * frame_duration_ms / 1000)

        silence_threshold_frames = int(silence_duration * 1000 / frame_duration_ms)
        min_speech_frames = int(min_speech_duration * 1000 / frame_duration_ms)
        max_frames = int(max_duration * 1000 / frame_duration_ms)

        # Use dynamic threshold based on speaking volume
        state = {
            'total_frames': 0,
            'speech_frames': 0,
            'silence_frames': 0,
            'speech_started': False,
            'max_volume_seen': 0.0,
            'should_stop': False,
            'speaking_volumes': [],  # Track volumes during speech
            'dynamic_threshold': volume_threshold
        }

        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")

            if state['should_stop']:
                return

            recording.append(indata.copy())
            state['total_frames'] += 1

            # Calculate volume (RMS)
            volume = np.sqrt(np.mean(indata**2))
            state['max_volume_seen'] = max(state['max_volume_seen'], volume)

            # Dynamic threshold: use initial threshold to detect speech,
            # then adapt based on actual speaking volume
            if not state['speech_started']:
                # Before speech detected, use static threshold
                threshold = volume_threshold
                is_speech = volume > threshold
            else:
                # After speech started, track speaking volumes
                if volume > state['dynamic_threshold']:
                    state['speaking_volumes'].append(volume)
                    # Keep only recent volumes (last 20 frames = 2 seconds)
                    if len(state['speaking_volumes']) > 20:
                        state['speaking_volumes'].pop(0)

                    # Update dynamic threshold: 40% of average speaking volume
                    if len(state['speaking_volumes']) >= 5:
                        avg_speaking = np.mean(state['speaking_volumes'])
                        state['dynamic_threshold'] = avg_speaking * 0.4

                # Silence = volume drops below 40% of speaking level
                threshold = state['dynamic_threshold']
                is_speech = volume > threshold

            # Show volume meter
            if state['total_frames'] % 3 == 0:  # Update frequently
                bars = int(volume * 500)
                silence_info = f" [Silence: {state['silence_frames']}/{silence_threshold_frames}]" if state['speech_started'] else ""
                threshold_info = f" (threshold: {threshold:.4f})"
                print(f"Volume: {'|' * min(bars, 50)} {volume:.4f}{silence_info}{threshold_info}        ", end='\r')

            if is_speech:
                state['speech_frames'] += 1
                state['silence_frames'] = 0
                if not state['speech_started'] and state['speech_frames'] >= min_speech_frames:
                    state['speech_started'] = True
                    print("\n🗣️  Speech detected... (stop talking to finish)                    ")
            else:
                if state['speech_started']:
                    state['silence_frames'] += 1
                    # Check if we should stop
                    if state['silence_frames'] >= silence_threshold_frames:
                        state['should_stop'] = True
                        print(f"\n🔇 Silence detected (volume dropped to {volume:.4f}), processing...                    ")
                state['speech_frames'] = max(0, state['speech_frames'] - 1)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback,
            dtype='float32',
            blocksize=frames_per_check
        ):
            # Record until stop signal or max duration
            while state['total_frames'] < max_frames and not state['should_stop']:
                sd.sleep(frame_duration_ms)

        print()  # New line after volume meter

        if len(recording) == 0:
            print("⚠️  No audio recorded")
            return np.array([], dtype=np.int16)

        # Convert back to int16 for Whisper
        audio_float = np.concatenate(recording).flatten()
        audio_int16 = (audio_float * 32767).astype(np.int16)

        duration = len(audio_int16) / self.sample_rate

        if not state['speech_started']:
            print(f"⚠️  No speech detected. Max volume: {state['max_volume_seen']:.4f}, Threshold: {volume_threshold:.4f}")
            print(f"💡 Try speaking louder or adjust threshold")
        else:
            print(f"✅ Recorded {duration:.1f}s")

        return audio_int16

    def _record_with_webrtc_vad(self,
                                 vad_aggressiveness: int = 2,
                                 silence_duration: float = 1.0,
                                 max_duration: int = 30,
                                 min_speech_duration: float = 0.5) -> np.ndarray:
        """
        Record with WebRTC VAD (used when webrtcvad library is available)
        """
        print("🎤 Listening... (speak now)")

        # WebRTC VAD works with specific sample rates
        vad_sample_rate = 16000  # WebRTC VAD supports 8000, 16000, 32000, 48000
        frame_duration = 30  # milliseconds (10, 20, or 30)
        frame_size = int(vad_sample_rate * frame_duration / 1000)

        vad = webrtcvad.Vad(vad_aggressiveness)

        recording = []
        speech_frames = 0
        silence_frames = 0
        silence_threshold = int(silence_duration * 1000 / frame_duration)  # frames of silence
        min_speech_frames = int(min_speech_duration * 1000 / frame_duration)
        max_frames = int(max_duration * 1000 / frame_duration)
        total_frames = 0

        is_speaking = False
        speech_started = False

        def callback(indata, frames, time, status):
            nonlocal speech_frames, silence_frames, total_frames, is_speaking, speech_started
            if status:
                print(f"Audio status: {status}")

            recording.append(indata.copy())
            total_frames += 1

            # Convert to bytes for VAD
            audio_bytes = (indata * 32767).astype(np.int16).tobytes()

            # Process in 30ms frames
            for i in range(0, len(audio_bytes), frame_size * 2):  # *2 for int16
                frame = audio_bytes[i:i + frame_size * 2]
                if len(frame) < frame_size * 2:
                    break

                # Check if frame contains speech
                try:
                    is_speech = vad.is_speech(frame, vad_sample_rate)

                    if is_speech:
                        speech_frames += 1
                        silence_frames = 0
                        if not speech_started and speech_frames >= min_speech_frames:
                            speech_started = True
                            print("🗣️  Speech detected...")
                        is_speaking = True
                    else:
                        if speech_started:
                            silence_frames += 1
                        speech_frames = max(0, speech_frames - 1)
                except Exception as e:
                    # VAD can fail on very quiet audio
                    pass

        with sd.InputStream(
            samplerate=vad_sample_rate,
            channels=self.channels,
            callback=callback,
            dtype='float32',
            blocksize=frame_size
        ):
            # Record until silence after speech or max duration
            while total_frames < max_frames:
                sd.sleep(frame_duration)

                if speech_started and silence_frames >= silence_threshold:
                    print("🔇 Silence detected, processing...")
                    break

        if len(recording) == 0:
            print("⚠️  No audio recorded")
            return np.array([], dtype=np.int16)

        # Convert back to int16 for Whisper
        audio_float = np.concatenate(recording).flatten()
        audio_int16 = (audio_float * 32767).astype(np.int16)

        duration = len(audio_int16) / vad_sample_rate
        print(f"✅ Recorded {duration:.1f}s")

        return audio_int16

    def record_until_silence(self,
                            silence_threshold: float = 0.01,
                            silence_duration: float = 1.5,
                            max_duration: int = 30) -> np.ndarray:
        """Record until silence is detected (legacy method, use record_with_vad instead)"""
        print("Recording... (speak now, will stop on silence)")
        recording = []
        silence_frames = 0
        silence_samples = int(silence_duration * self.sample_rate)
        max_samples = int(max_duration * self.sample_rate)
        total_frames = 0

        def callback(indata, frames, time, status):
            nonlocal silence_frames, total_frames
            if status:
                print(f"Status: {status}")

            recording.append(indata.copy())
            total_frames += frames

            # Check for silence
            volume = np.abs(indata).mean()
            if volume < silence_threshold:
                silence_frames += frames
            else:
                silence_frames = 0

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback,
            dtype='int16'
        ):
            # Record until silence or max duration
            while silence_frames < silence_samples and total_frames < max_samples:
                sd.sleep(100)

        print("Recording stopped.")
        if len(recording) == 0:
            return np.array([], dtype=np.int16)
        return np.concatenate(recording).flatten()


class AudioPlayer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sample_rate = settings.SAMPLE_RATE

    def play(self, audio_data: np.ndarray, sample_rate: int = None):
        """Play audio data at correct sample rate"""
        if len(audio_data) == 0:
            print("No audio to play.")
            return

        # Use provided sample rate or fallback to settings
        rate = sample_rate if sample_rate else self.sample_rate
        sd.play(audio_data, rate)
        sd.wait()
