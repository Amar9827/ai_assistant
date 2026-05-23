from config.settings import Settings
from .stt import SpeechToText
from .llm import LLMProcessor
from .tts import TextToSpeech
from .audio_utils import AudioRecorder, AudioPlayer
from typing import Optional, Tuple
import logging
import threading
import queue

class VoiceAssistant:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

        # Initialize components
        self.stt = SpeechToText(self.settings)
        self.llm = LLMProcessor(self.settings)
        self.tts = TextToSpeech(self.settings)
        self.recorder = AudioRecorder(self.settings)
        self.player = AudioPlayer(self.settings)

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def initialize(self):
        """Initialize all components"""
        self.logger.info("Initializing Voice Assistant...")
        self.stt.initialize()
        self.llm.initialize()
        self.tts.initialize()
        self.logger.info("Initialization complete")

    def process_voice_query(self, duration: int = 5, use_vad: bool = False) -> Tuple[str, str]:
        """
        Record audio, transcribe, get LLM response, and speak it

        Args:
            duration: Recording duration in seconds (ignored if use_vad=True)
            use_vad: Use Voice Activity Detection for automatic recording stop

        Returns:
            (transcribed_text, llm_response)
        """
        # Record audio with VAD or fixed duration
        if use_vad:
            audio_data = self.recorder.record_with_vad()
        else:
            audio_data = self.recorder.record(duration)

        if len(audio_data) == 0:
            self.logger.warning("No audio recorded")
            return "", ""

        # Transcribe
        self.logger.info("Transcribing...")
        user_text = self.stt.transcribe(audio_data)
        self.logger.info(f"User: {user_text}")

        if not user_text.strip():
            self.logger.warning("No speech detected")
            return "", ""

        # Get LLM response
        self.logger.info("Generating response...")
        response_text = self.llm.generate_response(user_text)
        self.logger.info(f"Assistant: {response_text}")

        # Synthesize and play
        self.logger.info("Speaking response...")
        audio_response = self.tts.synthesize(response_text)
        # Use TTS sample rate for correct pitch
        self.player.play(audio_response, sample_rate=self.tts.last_sample_rate)

        return user_text, response_text

    def process_voice_query_streaming(self, use_vad: bool = True) -> Tuple[str, str]:
        """
        Process voice query with streaming LLM + TTS pipeline for minimum latency

        Pipeline:
        1. Record with VAD (auto-stop on silence)
        2. Transcribe speech to text
        3. Stream LLM response sentence-by-sentence
        4. Synthesize and speak each sentence while next one generates

        This dramatically reduces perceived latency - user hears response
        starting within ~5-8 seconds instead of waiting 15-20 seconds.

        Returns:
            (transcribed_text, full_llm_response)
        """
        # Record audio with VAD
        if use_vad:
            audio_data = self.recorder.record_with_vad()
        else:
            audio_data = self.recorder.record(5)

        if len(audio_data) == 0:
            self.logger.warning("No audio recorded")
            return "", ""

        # Transcribe
        self.logger.info("🎯 Transcribing...")
        user_text = self.stt.transcribe(audio_data)
        print(f"\n💬 You: {user_text}\n")

        if not user_text.strip():
            self.logger.warning("No speech detected")
            return "", ""

        # Stream LLM response and speak sentences as they come
        self.logger.info("🤖 Generating response...")
        print("🔊 Assistant: ", end="", flush=True)

        full_response = ""
        sentence_queue = queue.Queue()
        tts_thread = None

        def speak_sentences():
            """Background thread to synthesize and play sentences"""
            while True:
                sentence = sentence_queue.get()
                if sentence is None:  # Sentinel to stop
                    break

                try:
                    audio = self.tts.synthesize(sentence)
                    self.player.play(audio, sample_rate=self.tts.last_sample_rate)
                except Exception as e:
                    self.logger.error(f"TTS error: {e}")

                sentence_queue.task_done()

        # Start TTS thread
        tts_thread = threading.Thread(target=speak_sentences, daemon=True)
        tts_thread.start()

        # Stream LLM sentences and queue for TTS
        for sentence in self.llm.generate_streaming_sentences(user_text):
            sentence = sentence.strip()
            if sentence:
                print(sentence, end=" ", flush=True)
                full_response += sentence + " "
                sentence_queue.put(sentence)

        print()  # New line after response

        # Wait for all TTS to complete
        sentence_queue.put(None)  # Stop sentinel
        sentence_queue.join()
        if tts_thread:
            tts_thread.join(timeout=5)

        return user_text, full_response.strip()

    def process_text_query(self, text: str, speak: bool = True) -> str:
        """Process text query without voice input"""
        response = self.llm.generate_response(text)

        if speak:
            audio_response = self.tts.synthesize(response)
            self.player.play(audio_response)

        return response

    def reset(self):
        """Reset conversation history"""
        self.llm.reset_conversation()
        self.logger.info("Conversation reset")
