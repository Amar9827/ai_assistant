import gradio as gr
from src.core.assistant import VoiceAssistant
import numpy as np

class GUIInterface:
    def __init__(self):
        self.assistant = VoiceAssistant()
        self.assistant.initialize()
        self.chat_history = []

    def process_text(self, text: str, history: list) -> list:
        """Process text input for Gradio chatbot"""
        if not text.strip():
            return history

        response = self.assistant.process_text_query(text, speak=False)
        history.append((text, response))
        return history

    def process_audio(self, audio: tuple) -> tuple:
        """Process audio input"""
        if audio is None:
            return "No audio recorded", []

        sample_rate, audio_data = audio

        # Convert to correct format if needed
        if audio_data.dtype != np.int16:
            # Normalize to int16 range
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)

        # Transcribe
        text = self.assistant.stt.transcribe(audio_data)

        if not text.strip():
            return "Could not transcribe audio", []

        # Get response
        response = self.assistant.process_text_query(text, speak=False)

        # Update history
        self.chat_history.append((text, response))

        return f"You: {text}\n\nAssistant: {response}", self.chat_history

    def reset_conversation(self):
        """Reset conversation history"""
        self.assistant.reset()
        self.chat_history = []
        return []

    def launch(self):
        """Launch Gradio interface"""
        with gr.Blocks(title="AI Voice Assistant", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# 🎤 Local AI Voice Assistant")
            gr.Markdown("Chat with your local AI assistant using text or voice")

            with gr.Tab("💬 Text Chat"):
                chatbot = gr.Chatbot(label="Conversation", height=400)
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Type your message here...",
                        label="Your Message",
                        scale=4
                    )
                    send_btn = gr.Button("Send", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("Clear Chat")
                    reset_btn = gr.Button("Reset Conversation")

                msg.submit(self.process_text, [msg, chatbot], [chatbot])
                send_btn.click(self.process_text, [msg, chatbot], [chatbot])
                msg.submit(lambda: "", None, msg)
                send_btn.click(lambda: "", None, msg)

                clear_btn.click(lambda: [], None, chatbot)
                reset_btn.click(self.reset_conversation, None, chatbot)

            with gr.Tab("🎤 Voice Chat"):
                gr.Markdown("Record your voice and get a response")
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="numpy",
                    label="Record Your Message"
                )
                audio_output = gr.Textbox(
                    label="Conversation",
                    lines=10
                )
                voice_chatbot = gr.Chatbot(
                    label="Chat History",
                    height=300
                )

                audio_input.change(
                    self.process_audio,
                    inputs=audio_input,
                    outputs=[audio_output, voice_chatbot]
                )

                reset_voice_btn = gr.Button("Reset Conversation")
                reset_voice_btn.click(
                    self.reset_conversation,
                    None,
                    [voice_chatbot]
                )

            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### Model Settings")
                gr.Markdown(f"""
                **Current Configuration:**
                - LLM Model: {self.assistant.settings.OLLAMA_MODEL}
                - Whisper Model: {self.assistant.settings.WHISPER_MODEL}
                - Piper Voice: {self.assistant.settings.PIPER_VOICE}
                - Sample Rate: {self.assistant.settings.SAMPLE_RATE}Hz

                To change settings, edit the `.env` file in the project root.
                """)

        demo.launch(share=False, server_name="0.0.0.0", server_port=7860)


def main():
    gui = GUIInterface()
    gui.launch()


if __name__ == "__main__":
    main()
