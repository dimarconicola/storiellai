TTS_CONFIG = {
    "model": "gpt-4o-mini-tts",  # or another model if available
    "voice": "nova",             # try "nova", "echo", "onyx", "fable", etc.
    "language": "it",            # ISO code, if supported by your API
    "response_format": "wav",
    "instructions": "Parla con accento italiano, tono fiabesco, naturale e coinvolgente.",
    "speed": 0.95,               # 1.0 is normal, <1 slower, >1 faster
    "prosody": {
        "pitch": "medium",       # if supported
        "rate": "medium",        # if supported
        "volume": "medium"       # if supported
    }
}