from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from src.core.assistant import VoiceAssistant
import uvicorn
import tempfile
import os

app = FastAPI(title="AI Voice Assistant")
assistant = VoiceAssistant()


class TextQuery(BaseModel):
    query: str


@app.on_event("startup")
async def startup():
    """Initialize assistant on startup"""
    try:
        assistant.initialize()
    except Exception as e:
        print(f"Failed to initialize assistant: {e}")


@app.post("/api/text")
async def process_text(data: TextQuery):
    """Process text query"""
    try:
        response = assistant.process_text_query(data.query, speak=False)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio")
async def process_audio(file: UploadFile = File(...)):
    """Process audio file"""
    try:
        # Save uploaded audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Transcribe audio
            text = assistant.stt.transcribe_file(tmp_path)
            # Get LLM response
            response = assistant.llm.generate_response(text)
            return {"transcription": text, "response": response}
        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def reset_conversation():
    """Reset conversation history"""
    try:
        assistant.reset()
        return {"message": "Conversation reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve web UI"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Voice Assistant</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .input-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type="text"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                box-sizing: border-box;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin-right: 10px;
            }
            button:hover {
                background-color: #45a049;
            }
            .response {
                margin-top: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-left: 4px solid #4CAF50;
                border-radius: 5px;
            }
            .error {
                border-left-color: #f44336;
                color: #f44336;
            }
        </style>
    </head>
    <body>
        <h1>🎤 AI Voice Assistant</h1>
        <div class="container">
            <div class="input-group">
                <label for="textInput">Enter your message:</label>
                <input type="text" id="textInput" placeholder="Type your message here...">
            </div>
            <button onclick="sendText()">Send Message</button>
            <button onclick="resetConversation()" style="background-color: #ff9800;">Reset</button>

            <div id="response" class="response" style="display:none;">
                <strong>Response:</strong>
                <p id="responseText"></p>
            </div>
        </div>

        <script>
            async function sendText() {
                const input = document.getElementById('textInput');
                const query = input.value.trim();

                if (!query) {
                    alert('Please enter a message');
                    return;
                }

                const responseDiv = document.getElementById('response');
                const responseText = document.getElementById('responseText');

                try {
                    const response = await fetch('/api/text', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: query })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        responseDiv.style.display = 'block';
                        responseDiv.classList.remove('error');
                        responseText.textContent = data.response;
                    } else {
                        throw new Error(data.detail || 'Request failed');
                    }
                } catch (error) {
                    responseDiv.style.display = 'block';
                    responseDiv.classList.add('error');
                    responseText.textContent = 'Error: ' + error.message;
                }

                input.value = '';
            }

            async function resetConversation() {
                try {
                    const response = await fetch('/api/reset', {
                        method: 'POST'
                    });

                    if (response.ok) {
                        alert('Conversation reset successfully');
                        document.getElementById('response').style.display = 'none';
                    }
                } catch (error) {
                    alert('Error resetting conversation: ' + error.message);
                }
            }

            // Allow Enter key to send message
            document.getElementById('textInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendText();
                }
            });
        </script>
    </body>
    </html>
    """)


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
