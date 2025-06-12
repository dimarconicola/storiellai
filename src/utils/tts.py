import requests
import os
from config.tts_config import TTS_CONFIG

def text_to_speech(text, wav_path="output.wav"):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": TTS_CONFIG["model"],
        "input": text,
        "voice": TTS_CONFIG["voice"],
        "response_format": TTS_CONFIG["response_format"],
        "instructions": TTS_CONFIG["instructions"],
        "speed": TTS_CONFIG["speed"]
        # Add prosody, language, etc. if your API supports them
    }
    # If your API supports language or prosody, add them here:
    if "language" in TTS_CONFIG:
        payload["language"] = TTS_CONFIG["language"]
    if "prosody" in TTS_CONFIG:
        payload["prosody"] = TTS_CONFIG["prosody"]

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        with open(wav_path, "wb") as f:
            f.write(response.content)
        print(f"Audio salvato in {wav_path}")
    else:
        print(f"Errore TTS: {response.status_code} {response.text}")

if __name__ == "__main__":
    text = "Ciao! Questa è una prova di sintesi vocale italiana con OpenAI."
    text_to_speech(text)