import pytest
from unittest.mock import MagicMock
from src.core.llm import LLMProcessor

class FakeOllamaResponse:
    """Fake Ollama streaming response — yields preset chunks."""
    def __init__(self, chunks):
        self.chunks = chunks
    def __iter__(self):
        for c in self.chunks:
            yield {"message": {"content": c}}

def _make_llm(settings, response):
    llm = LLMProcessor(settings)
    llm.client = MagicMock()
    llm.client.chat = MagicMock(return_value=response)
    return llm

def test_streaming_full_consumption_commits_both_turns(settings):
    llm = _make_llm(settings, FakeOllamaResponse(["Hello", " world", "!"]))
    chunks = list(llm.generate_response("Hi", stream=True))
    assert "".join(chunks) == "Hello world!"
    assert llm.conversation_history == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello world!"},
    ]

def test_streaming_partial_consumption_still_commits(settings):
    """If consumer stops early (simulates disconnect), partial reply still commits."""
    llm = _make_llm(settings, FakeOllamaResponse(["Hello", " world", "!"]))
    gen = llm.generate_response("Hi", stream=True)
    got = next(gen)
    gen.close()  # Simulates client disconnect mid-stream
    assert got == "Hello"
    # History should have BOTH turns, with assistant content = what was yielded
    assert llm.conversation_history == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]

def test_streaming_zero_chunks_commits_nothing(settings):
    """If generator closes before yielding anything, history is untouched."""
    llm = _make_llm(settings, FakeOllamaResponse([]))
    gen = llm.generate_response("Hi", stream=True)
    gen.close()
    assert llm.conversation_history == []

def test_non_streaming_commits_atomically(settings):
    llm = _make_llm(settings, {"message": {"content": "Hi there"}})
    result = llm.generate_response("Hello")
    assert result == "Hi there"
    assert llm.conversation_history == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]

def test_history_is_capped(settings):
    llm = LLMProcessor(settings)
    llm.max_history_turns = 3  # Cap at 3 turns = 6 messages
    llm.client = MagicMock()
    for i in range(10):
        llm.client.chat = MagicMock(return_value={"message": {"content": f"reply{i}"}})
        llm.generate_response(f"q{i}")
    assert len(llm.conversation_history) == 6  # 3 turns * 2 messages
    # Last user message should be q9
    assert llm.conversation_history[-2] == {"role": "user", "content": "q9"}
