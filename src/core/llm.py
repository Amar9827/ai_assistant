import logging
import ollama
from groq import Groq
import httpx
from typing import List, Dict, Generator
from config.settings import Settings

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.LLM_PROVIDER.lower()
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_turns = getattr(settings, "MAX_HISTORY_TURNS", 20)

        # Always initialize both clients (lightweight — no model loading)
        self.ollama_client = ollama.Client(host=settings.OLLAMA_HOST)
        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = Groq(
                api_key=settings.GROQ_API_KEY,
                http_client=httpx.Client(verify=False),
            )

        # JARVIS persona system prompt
        self.system_prompt = {
            "role": "system",
            "content": (
                "You are J.A.R.V.I.S. — Just A Rather Very Intelligent System — "
                "a highly capable AI voice assistant inspired by the iconic AI from the Iron Man films. "
                "You serve your operator, Amar, with precision and composure.\n\n"
                "PERSONALITY:\n"
                "- Formal, composed, and precise. Professional with dry wit when appropriate.\n"
                "- Address the user as 'sir' occasionally but naturally, not robotically.\n"
                "- Never hedge unnecessarily or second-guess the user's intent.\n"
                "- When you make a mistake, acknowledge it briefly and correct immediately.\n\n"
                "VOICE RULES:\n"
                "- Keep responses concise: 1-3 sentences for simple queries, up to 5 for complex ones.\n"
                "- Speak naturally as if talking, not writing. No markdown, no bullet points, no headers.\n"
                "- Never read out URLs, file paths, or code aloud.\n"
                "- Get straight to the point. No filler phrases like 'Great question!' or 'That's interesting!'.\n"
                "- Use natural spoken language: 'You have 58 gigabytes available, sir' NOT 'Available: 58GB'.\n\n"
                "CONTEXT:\n"
                "- You are running on a Windows system (Dell Latitude 5440, i7-1370P, 32GB RAM).\n"
                "- Current date and time should be inferred from conversation context.\n"
                "- You are a voice assistant — your responses will be spoken aloud via text-to-speech."
            )
        }

    def initialize(self):
        """Verify primary LLM provider is reachable (fallback is best-effort)."""
        if self.provider == "groq" and self.groq_client:
            try:
                self.groq_client.models.list()
                logger.info("Groq API connected (primary)")
            except Exception as e:
                logger.warning(f"Groq API not reachable: {e} — will fall back to Ollama")
        try:
            self.ollama_client.list()
            logger.info("Ollama connected (fallback)" if self.provider == "groq" else "Ollama connected (primary)")
        except Exception as e:
            if self.provider != "groq":
                raise ConnectionError(f"Ollama not reachable: {e}")
            logger.warning(f"Ollama fallback not available: {e}")
        return True

    def generate_response(self, user_input: str, stream: bool = False):
        """
        Generate response from LLM with automatic fallback.

        If Groq is primary and fails, falls back to local Ollama.
        Returns str if stream=False, Generator[str] if stream=True.
        """
        pending_user = {"role": "user", "content": user_input}
        messages = [self.system_prompt] + self.conversation_history + [pending_user]

        if self.provider == "groq" and self.groq_client:
            try:
                return self._groq_response(messages, pending_user, stream)
            except Exception as e:
                logger.warning(f"Groq failed ({e}), falling back to Ollama")
                return self._ollama_response(messages, pending_user, stream)
        else:
            return self._ollama_response(messages, pending_user, stream)

    def _groq_response(self, messages, pending_user, stream):
        """Generate response via Groq cloud API."""
        response = self.groq_client.chat.completions.create(
            model=self.settings.GROQ_MODEL,
            messages=messages,
            temperature=self.settings.OLLAMA_TEMPERATURE,
            stream=stream,
        )

        if stream:
            return self._stream_groq(response, pending_user)

        assistant_message = response.choices[0].message.content
        self.conversation_history.append(pending_user)
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )
        self._cap_history()
        return assistant_message

    def _stream_groq(self, response, pending_user):
        """Stream chunks from Groq, committing history atomically.
        If Groq fails mid-stream before producing content, falls back to Ollama."""
        full_response = ""
        try:
            for chunk in response:
                delta = chunk.choices[0].delta
                content = delta.content if delta.content else ""
                if content:
                    full_response += content
                    yield content
        except Exception as e:
            if not full_response.strip():
                # No content produced yet — fall back to Ollama
                logger.warning(f"Groq stream failed ({e}), falling back to Ollama")
                messages = [self.system_prompt] + self.conversation_history + [pending_user]
                yield from self._stream_response(
                    self.ollama_client.chat(
                        model=self.settings.OLLAMA_MODEL,
                        messages=messages,
                        options={"temperature": self.settings.OLLAMA_TEMPERATURE},
                        stream=True,
                    ),
                    pending_user,
                )
                return
            else:
                logger.warning(f"Groq stream failed mid-response ({e}), keeping partial")
        finally:
            if full_response.strip():
                self.conversation_history.append(pending_user)
                self.conversation_history.append(
                    {"role": "assistant", "content": full_response}
                )
                self._cap_history()

    def _ollama_response(self, messages, pending_user, stream):
        """Generate response via local Ollama."""
        response = self.ollama_client.chat(
            model=self.settings.OLLAMA_MODEL,
            messages=messages,
            options={"temperature": self.settings.OLLAMA_TEMPERATURE},
            stream=stream,
        )

        if stream:
            return self._stream_response(response, pending_user)

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
