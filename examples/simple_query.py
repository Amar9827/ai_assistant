"""
Simple query example - demonstrates basic text-to-text interaction
"""
from src.core.assistant import VoiceAssistant

def main():
    print("Initializing AI Voice Assistant...")
    assistant = VoiceAssistant()
    assistant.initialize()
    print("Assistant ready!\n")

    # Simple text query without speech
    print("Asking: What is the capital of France?")
    response = assistant.process_text_query(
        "What is the capital of France?",
        speak=False  # Set to True to hear the response
    )
    print(f"Response: {response}\n")

    # Another query with conversation context
    print("Asking: What is its population?")
    response = assistant.process_text_query(
        "What is its population?",
        speak=False
    )
    print(f"Response: {response}\n")

    # Reset conversation
    print("Resetting conversation...")
    assistant.reset()

    # New conversation
    print("Asking: Tell me a fun fact about space")
    response = assistant.process_text_query(
        "Tell me a fun fact about space",
        speak=False
    )
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
