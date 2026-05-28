import ollama
from typing import List, Dict, Generator
from config.settings import Settings

class LLMProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ollama.Client(host=settings.OLLAMA_HOST)
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_turns = getattr(settings, "MAX_HISTORY_TURNS", 20)

        # System prompt for concise voice responses
        self.system_prompt = {
            "role": "system",
            "content": "You are a helpful voice assistant. Keep responses concise and conversational - aim for 1-3 sentences. Speak naturally as if talking to someone, not writing an essay. Get straight to the point."
        }

    def initialize(self):
        """Verify Ollama is running and model is available"""
        try:
            self.client.list()
            return True
        except Exception as e:
            raise ConnectionError(f"Ollama not reachable: {e}")

    def generate_response(self, user_input: str, stream: bool = False):
        """
        Generate response from LLM.

        Returns str if stream=False, Generator[str] if stream=True.
        History is committed atomically: either both user and assistant
        turns are appended, or neither is (e.g., on disconnect mid-stream).
        """
        pending_user = {"role": "user", "content": user_input}
        messages = [self.system_prompt] + self.conversation_history + [pending_user]

        response = self.client.chat(
            model=self.settings.OLLAMA_MODEL,
            messages=messages,
            options={"temperature": self.settings.OLLAMA_TEMPERATURE},
            stream=stream,
        )

        if stream:
            return self._stream_response(response, pending_user)

        # Non-streaming path: commit both turns now.
        assistant_message = response["message"]["content"]
        self.conversation_history.append(pending_user)
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )
        self._cap_history()
        return assistant_message

    def _stream_response(self, response, pending_user):
        """
        Stream chunks while accumulating the full assistant reply.

        On generator close (GeneratorExit), normal completion, or any
        other exit: commit both user and assistant turns IF any content
        was produced. If zero chunks were yielded (immediate disconnect),
        commit nothing — leave history clean.
        """
        full_response = ""
        try:
            for chunk in response:
                content = chunk["message"]["content"]
                full_response += content
                yield content
        finally:
            if full_response.strip():
                self.conversation_history.append(pending_user)
                self.conversation_history.append(
                    {"role": "assistant", "content": full_response}
                )
                self._cap_history()

    def _cap_history(self):
        """Trim conversation_history to last N turns (N user + N assistant msgs)."""
        max_msgs = self.max_history_turns * 2
        if len(self.conversation_history) > max_msgs:
            self.conversation_history = self.conversation_history[-max_msgs:]

    def generate_streaming_sentences(self, user_input: str):
        """
        Generate response and yield complete sentences as they're ready

        This is optimized for TTS - each yielded sentence can be spoken
        while the next sentence is being generated.
        """
        return self.generate_response(user_input, stream=True)

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
