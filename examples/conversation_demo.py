"""
Conversation demo - demonstrates multi-turn conversation with context
"""
from src.core.assistant import VoiceAssistant

def main():
    print("=" * 60)
    print("AI Voice Assistant - Conversation Demo")
    print("=" * 60)
    print()

    assistant = VoiceAssistant()
    print("Initializing assistant...")
    assistant.initialize()
    print("Assistant ready!\n")

    # Conversation about a topic
    conversation = [
        "Tell me about Python programming",
        "What are its main advantages?",
        "Can you give me an example of its use in data science?",
        "What libraries are most popular for that?"
    ]

    for i, query in enumerate(conversation, 1):
        print(f"\n[Turn {i}]")
        print(f"You: {query}")
        print("-" * 60)

        response = assistant.process_text_query(query, speak=False)
        print(f"Assistant: {response}")
        print("-" * 60)

    print("\n" + "=" * 60)
    print("Conversation complete!")
    print("=" * 60)

    # Show conversation history
    print("\nConversation history length:", len(assistant.llm.conversation_history))


if __name__ == "__main__":
    main()
