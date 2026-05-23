# Contributing to AI Voice Assistant

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version, RAM)
- Error messages or logs

### Suggesting Features

Feature requests are welcome! Please include:
- Use case and motivation
- Proposed implementation (if applicable)
- Any potential drawbacks or considerations

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**:
   - Follow existing code style
   - Add tests if applicable
   - Update documentation
4. **Test thoroughly**:
   - Run existing tests
   - Test all interfaces (CLI, Web, GUI)
   - Test on your target platform
5. **Commit with clear messages**: 
   ```
   Add voice activity detection feature
   
   - Implement VAD using webrtcvad
   - Add configuration options
   - Update CLI to support VAD mode
   ```
6. **Push and create PR**: Describe what changed and why

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ai-voice-assistant.git
cd ai-voice-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -r requirements.txt
pip install -e .

# Run tests
pytest tests/
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Keep functions focused and well-documented
- Add docstrings to public methods
- Use meaningful variable names

## Project Structure

- `src/core/` - Core functionality (STT, LLM, TTS, audio)
- `src/interfaces/` - User interfaces (CLI, Web, GUI)
- `src/utils/` - Utility functions
- `config/` - Configuration management
- `tests/` - Unit and integration tests
- `examples/` - Example usage scripts

## Areas for Contribution

### High Priority
- [ ] Wake word detection
- [ ] Voice activity detection (VAD)
- [ ] Streaming LLM responses
- [ ] Unit tests for core modules
- [ ] Performance optimizations

### Medium Priority
- [ ] Multi-language support
- [ ] Additional TTS voice options
- [ ] Custom prompts/personalities
- [ ] Conversation history persistence
- [ ] Docker containerization

### Nice to Have
- [ ] Mobile app interface
- [ ] Browser extension
- [ ] Plugin system
- [ ] Advanced audio processing
- [ ] Alternative LLM backends

## Testing

Before submitting a PR:

```bash
# Run all tests
pytest tests/

# Test specific interface
python examples/simple_query.py
assistant-cli
```

Test checklist:
- [ ] CLI interface works
- [ ] Web interface works
- [ ] GUI interface works
- [ ] Voice recording works
- [ ] Transcription works
- [ ] LLM responses work
- [ ] TTS playback works
- [ ] No new errors in logs

## Documentation

When adding features:
- Update README.md if user-facing
- Add docstrings to new functions
- Update QUICKSTART.md if setup changes
- Add examples if applicable

## Questions?

Feel free to:
- Open a discussion on GitHub
- Ask in issues before starting major work
- Reach out to maintainers

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment
- Follow the Golden Rule

Thank you for contributing! 🎉
