"""
Voice demo - demonstrates full voice-to-voice interaction
NOTE: Requires microphone and speakers
"""
from src.core.assistant import VoiceAssistant

def main():
    print("=" * 60)
    print("AI Voice Assistant - Voice Demo")
    print("=" * 60)
    print()

    assistant = VoiceAssistant()
    print("Initializing assistant...")
    assistant.initialize()
    print("Assistant ready!\n")

    print("This demo will:")
    print("1. Record your voice for 5 seconds")
    print("2. Transcribe what you said")
    print("3. Get a response from the LLM")
    print("4. Speak the response back to you")
    print()

    input("Press Enter when ready to start recording...")

    try:
        user_text, response_text = assistant.process_voice_query(duration=5)

        print("\n" + "=" * 60)
        print("Transcription:")
        print(f"  {user_text}")
        print()
        print("Response:")
        print(f"  {response_text}")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("- Make sure you have a working microphone")
        print("- Check that Ollama is running (ollama serve)")
        print("- Ensure Piper model is downloaded to models/piper/")


if __name__ == "__main__":
    main()
