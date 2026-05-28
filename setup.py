from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-voice-assistant",
    version="0.1.0",
    author="Your Name",
    description="A fully local AI voice assistant with no cloud dependencies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "faster-whisper>=0.10.0",
        "ollama>=0.1.0",
        "piper-tts>=1.3.0,<2.0",
        "numpy>=1.24.0",
        "sounddevice>=0.4.6",
        "scipy>=1.10.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "websockets>=12.0",
        # gradio removed - using custom UI
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "assistant-cli=src.interfaces.cli:main",
            # Web UI will be added back with new real-time interface
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
