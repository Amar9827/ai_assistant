import ollama
from typing import List, Dict, Generator
from config.settings import Settings

class LLMProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ollama.Client(host=settings.OLLAMA_HOST)
        self.conversation_history: List[Dict[str, str]] = []

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
        Generate response from LLM

        Args:
            user_input: User's question/message
            stream: If True, returns generator that yields text chunks

        Returns:
            str if stream=False, Generator[str] if stream=True
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # Include system prompt + conversation history
        messages = [self.system_prompt] + self.conversation_history

        response = self.client.chat(
            model=self.settings.OLLAMA_MODEL,
            messages=messages,
            options={
                "temperature": self.settings.OLLAMA_TEMPERATURE
            },
            stream=stream
        )

        if stream:
            return self._stream_response(response)
        else:
            assistant_message = response['message']['content']
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            return assistant_message

    def _stream_response(self, response: Generator):
        """
        Stream response chunks - yields each token as it arrives

        For WebSocket streaming, we yield raw chunks immediately.
        For sentence-based streaming (TTS), use generate_streaming_sentences()
        """
        full_response = ""

        for chunk in response:
            content = chunk['message']['content']
            full_response += content

            # Yield each chunk immediately (word-by-word streaming)
            yield content

        # Save complete response to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })

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
