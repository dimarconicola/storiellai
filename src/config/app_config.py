# app_config.py
"""
Application configuration for Storyteller Box.
Contains all constants, paths, and hardware pin assignments.
"""

from pathlib import Path

# ============ PATH CONSTANTS ============
BASE_DIR = Path(__file__).parent.parent
AUDIO_FOLDER = BASE_DIR / "audio"
BGM_FOLDER = BASE_DIR / "bgm"
STORIES_FOLDER = BASE_DIR / "storiesoffline"

# ============ AUDIO SETTINGS ============
AUDIO_FREQUENCY = 44100
AUDIO_BUFFER = 2048
AUDIO_CHANNELS = 2
MAX_AUDIO_CHANNELS = 8

# ============ VOLUME SETTINGS ============
MIN_SOFTWARE_VOLUME = 0.1
MAX_SOFTWARE_VOLUME = 0.9  # Max volume to prevent distortion, adjustable

# ============ STATE MACHINE STATES ============
STATE_IDLE = "idle"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_SHUTTING_DOWN = "shutting_down"

# ============ LED CONSTANTS ============
LED_OFF = False
LED_ON = True

# ============ GPIO PIN ASSIGNMENTS ============
# These should be configured to match your actual wiring
NFC_SPI_PORT = 0
NFC_SPI_CS_PIN = 0  # CE0 for SPI0
NFC_IRQ_PIN = 25    # Example
NFC_RST_PIN = 17    # Example
BUTTON_PIN = 23
LED_PIN = 24
ADC_CHANNEL_VOLUME = 0  # MCP3008 channel for volume pot

# ============ TIMING SETTINGS ============
CALM_TIME_START = (20, 30)  # 20:30
CALM_TIME_END = (6, 30)     # 6:30
VOLUME_CHECK_INTERVAL = 0.2  # Check volume 5 times per second
MAIN_LOOP_INTERVAL = 0.05    # Main loop polling interval

# ============ AUDIO TONE MAPPINGS ============
AVAILABLE_TONES = ["calmo", "avventuroso", "divertente", "misterioso", "tenero"]
