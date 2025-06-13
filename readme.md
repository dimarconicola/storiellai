---
title: Storyteller Box (Offline Edition)
description: A fully offline, NFC-triggered storytelling device for kids.
---

# Storyteller Box (Offline Edition)

> **A fully offline, NFC-triggered storytelling device for kids – featuring pre-recorded narration and background music.**

---

## Table of Contents

1.  [Overview](#overview)
2.  [How It Works](#how-it-works)
3.  [Repo Layout](#repo-layout)
4.  [Bill of Materials](#bill-of-materials)
5.  [Hardware Setup](#hardware-setup)
6.  [Software Setup](#software-setup)
7.  [Adding New Stories](#adding-new-stories)
8.  [Battery Management and Error Handling](#battery-management-and-error-handling)
9.  [Usage](#usage)
10. [Troubleshooting](#troubleshooting)
11. [Future Ideas](#future-ideas)
12. [Deploying to Multiple Devices (Creating a Master Image)](#deploying-to-multiple-devices)

---

## Overview

Storyteller Box is a small bedside companion that **tells pre-recorded fairy tales** triggered by NFC cards. Children place an NFC-tagged card on the lid, and the box plays a corresponding story with matching background music. The device is **fully offline**, with all narration and music pre-loaded onto an SD card.

-   **No internet required:** All stories and background music are pre-recorded and stored locally.
-   **Simple controls:** A single illuminated button handles play, pause, and shutdown.
-   **Calm time logic:** Automatically selects calm stories during bedtime hours.
-   **Parent-friendly:** Easily add new stories and music by copying files to the SD card.
-   **Language Agnostic:** While this version includes Italian stories, you can use stories in any language as long as they are in MP3 format.

---

## How It Works

1.  **NFC Card Scan:** The child places an NFC card on the box.
2.  **Story Lookup:** The `box.py` script reads the card's UID and looks up the corresponding story configuration in a JSON file located in `src/storiesoffline/`.
3.  **Audio Playback:**
    *   The script selects an appropriate background music track based on the story's defined "tone" (e.g., "calmo", "avventuroso").
    *   It plays the pre-recorded narration audio file for the selected story.
    *   `pygame` is used for audio mixing and playback.
4.  **Button Control:** A single button allows the child to play/pause the current story or initiate a shutdown.
5.  **LED Feedback:** The button\'s LED provides visual feedback (e.g., pulsing when ready, solid when playing).
6.  **Modular Design:** The codebase is now modular, with utility functions and configuration constants moved to dedicated modules for better maintainability.
7.  **Battery Management:** The system monitors battery voltage via an MCP3008 ADC. It provides a low battery warning (e.g., specific LED pattern) and can initiate a safe shutdown if the battery level becomes critical. The `hardware/hal.py` module includes logic to use a real ADC on a Raspberry Pi or a mock ADC for development on other systems (like macOS).

---

## Repo Layout

```
root/
├── src/
│   ├── box.py                # Main application logic
│   ├── config/
│   │   ├── app_config.py     # Configuration constants (paths, GPIO pins, etc.)
│   │   └── card_configs.py   # Card-specific configuration constants
│   ├── utils/
│   │   ├── __init__.py       # Package marker
│   │   ├── audio_utils.py    # Audio engine and playback utilities
│   │   ├── bgm_utils.py      # Background music utilities
│   │   ├── data_utils.py     # JSON and file utilities
│   │   ├── led_utils.py      # LED pattern manager
│   │   ├── log_utils.py      # Structured logging with rotation
│   │   ├── story_utils.py    # Story selection utilities
│   │   └── time_utils.py     # Time-based logic and battery management utilities
│   ├── hardware/             # Hardware abstraction layer (HAL)
│   │   ├── hal.py            # Defines real and mock hardware interfaces (NFC, Button, ADC)
│   │   └── led_button_fsm.py # LED/Button finite state machine
│   ├── stories/              # Online stories (API-based story generation)
│   ├── storiesoffline/       # JSON files for NFC card story mappings
│   └── audio/                # Audio files including error sound (error.mp3)
├── models/                   # LLM model files (e.g., TinyLlama)
├── tests/                    # Unit and integration tests
│   ├── test_data_utils.py    # Tests for data utilities
│   ├── test_hal_mocks.py     # Tests for hardware abstraction mocks
│   └── test_integration_card_tap.py # Integration tests
├── systemd/                  # System service files
│   ├── storyteller.service   # Systemd service for Linux/Raspberry Pi
│   └── storyteller.plist     # Launchd service for macOS
├── clean_env/                # Virtual environment (should be in .gitignore)
├── requirements.txt          # Python dependencies
├── readme.md                 # Project documentation
└── DEPLOYMENT_GUIDE.md       # Deployment instructions
```

## Battery Management and Error Handling

### Battery Monitoring

The Storyteller Box includes built-in battery monitoring via the MCP3008 ADC:

1. **Voltage Sensing**: The system monitors battery voltage through a voltage divider connected to the MCP3008 ADC.
   * Default connection: Battery voltage (5V) → Voltage divider (e.g., 10kΩ + 10kΩ) → MCP3008 Channel 1
   * The voltage divider reduces the 5V battery output to a safe 2.5V input for the ADC

2. **Thresholds**:
   * Low battery warning: 3.3V (configurable in `time_utils.py`)
   * Critical battery shutdown: 3.0V (configurable in `time_utils.py`)

3. **Feedback**:
   * Low battery: LED warning pattern (rapid blinks)
   * Critical battery: Safe shutdown sequence to prevent data corruption

### Error Handling

The system includes comprehensive error handling with user feedback:

1. **Types of Errors Handled**:
   * Missing/corrupt audio files
   * Invalid card configuration (JSON errors)
   * Hardware failures (NFC reader, audio)
   * System resource issues
   
2. **User Feedback**:
   * **Audio**: Error sound (`audio/error.mp3`) plays when an error occurs
   * **Visual**: Distinct LED patterns indicate different error types
     * Card read error: 3 quick blinks
     * Audio error: Fast pulsing pattern
     * System error: SOS pattern (3 short, 3 long, 3 short)

3. **Logging**:
   * Structured logging with rotation (max 5 files, 1MB each)
   * Both console and file logging (`storyteller.log`)
   * Detailed error traces for debugging

4. **Resilience**:
   * The system attempts to recover from errors when possible
   * Resource cleanup ensures proper release of hardware
   * Structured exception handling prevents crashes

### LED Patterns

The system uses various LED patterns to communicate system status:

| State | Pattern | Description |
|-------|---------|-------------|
| Boot  | 3 slow blinks | System is initializing |
| Ready | Slow breathing | System is ready for a card |
| Playing | Solid on | Story is playing |
| Paused | Fast breathing | Story is paused |
| Card Read Error | 3 quick blinks | Invalid/unrecognized card |
| Low Battery | 5 quick blinks every 30s | Battery needs charging |
| Error | SOS pattern | System error occurred |
| Shutdown | Fade out | System is shutting down |

These patterns can be customized in `led_utils.py` through the `LedPatternManager` class.

---

## Deploying to Multiple Devices

For instructions on how to create a master SD card image to easily set up multiple Storyteller Boxes (e.g., for gifts), please refer to the detailed guide:
[Storyteller Box Deployment Guide: Creating a Master Image](DEPLOYMENT_GUIDE.md)

---

## Bill of Materials (BOM)

| Component             | Description                                      | Est. Price (EUR) | Notes                                                                 |
| :-------------------- | :----------------------------------------------- | :--------------- | :-------------------------------------------------------------------- |
| Raspberry Pi Zero 2 W | Microcontroller board                            | 15-20            | Or any compatible Raspberry Pi (3B+, 4, etc.)                         |
| PN532 NFC Reader      | NFC/RFID reader module (SPI interface preferred) | 5-10             | Adafruit PN532 breakout or similar                                    |
| Micro SD Card         | 16GB or larger, Class 10                         | 5-10             | For OS and audio files                                                |
| Speaker               | 3W, 4 Ohm full-range speaker                     | 3-5              | Adafruit #1314 or similar                                             |
| PAM8302A Amplifier    | 2.5W Mono Class D Audio Amplifier                | 2-4              | Or similar I2S/analog amplifier compatible with Pi                    |
| LED Button            | Illuminated momentary push button                | 2-4              |                                                                       |
| Rotary Potentiometer  | 10k Ohm Linear Potentiometer                     | 1-3              | For volume control                                                    |
| MCP3008 ADC           | 8-Channel 10-Bit ADC with SPI Interface        | 2-4              | To read analog value from potentiometer and battery voltage           |
| Powerbank Battery     | Portable battery pack for powering the device    | 10-20            | Used to power the Pi. Voltage monitoring via MCP3008 (requires voltage divider circuit). |
| Jumper Wires          | Assorted male/female                             | 2-5              |                                                                       |
| NFC Cards/Tags        | NTAG215 or similar (compatible with PN532)       | 0.50-1 per card  |                                                                       |
| Enclosure             | 3D printed or custom-made box                    | 5-20             | Material cost if 3D printing                                          |
| **Optional:**         |                                                  |                  |                                                                       |
| USB Sound Card        | If Pi's onboard audio is noisy                   | 5-10             |                                                                       |
| Soldering Iron & Tin  | For connecting components                        | -                | If not using breadboard/jumper wires for permanent connections        |
| **Total Estimated:**  |                                                  | **50-100 EUR**   | Excluding optional items and tools                                    |

---

## Hardware Setup

### Wiring Instructions

#### Raspberry Pi Connections
| Component             | Raspberry Pi Pin (BCM) | Notes                                      |
|-----------------------|-------------------------|--------------------------------------------|
| **PN532 NFC Reader**  |                         |                                            |
| VCC                   | 3.3V or 5V             | Check PN532 module specs                  |
| GND                   | GND                    | Common ground                             |
| SCK/SCLK              | GPIO11 (SCLK)          | SPI Clock                                 |
| MISO                  | GPIO9 (MISO)           | SPI Master In Slave Out                  |
| MOSI                  | GPIO10 (MOSI)          | SPI Master Out Slave In                  |
| SS/SSEL/CS            | GPIO8 (CE0)            | SPI Chip Select                          |
| IRQ (optional)        | GPIO25                 | Interrupt Request                         |
| RST (optional)        | GPIO17                 | Reset                                     |
| **LED Button**        |                         |                                            |
| LED+                  | GPIO24                 | LED control                               |
| Button                | GPIO23                 | Button input                              |
| **Rotary Potentiometer** |                         |                                            |
| Signal                | MCP3008 Channel 0      | Analog input via ADC                     |
| **Battery Voltage Sense**| MCP3008 Channel 1 (example)| Connect to output of a voltage divider (e.g., 1:2) from powerbank 5V line. |
| **Speaker & Amplifier** |                         |                                            |
| Speaker+              | PAM8302A Output+       | Connect to speaker                        |
| Speaker-              | PAM8302A Output-       | Connect to speaker                        |
| VIN                   | 5V                     | Power supply                              |
| GND                   | GND                    | Common ground                             |

### Wiring Diagram (Basic ASCII Art)

```
+-------------------+       +-------------------+       +-------------------+
| Raspberry Pi      |       | PN532 NFC Reader  |       | LED Button         |
|-------------------|       |-------------------|       |-------------------|
| 3.3V (Pin 1)      +-------+ VCC               |       |                   |
| GND (Pin 6)       +-------+ GND               |       +-------------------+
| GPIO11 (Pin 23)   +-------+ SCK/SCLK          |
| GPIO9 (Pin 21)    +-------+ MISO              |
| GPIO10 (Pin 19)   +-------+ MOSI              |
| GPIO8 (Pin 24)    +-------+ SS/SSEL/CS        |
| GPIO25 (Pin 22)   +-------+ IRQ (Optional)    |
| GPIO17 (Pin 11)   +-------+ RST (Optional)    |
+-------------------+                           |
                                                |
+-------------------+                           |
| MCP3008 ADC       |                           |
|-------------------|                           |
| CH0               +---------------------------+
| VDD               +-------+ 3.3V (Pin 1)      |
| VREF              +-------+ 3.3V (Pin 1)      |
| AGND              +-------+ GND (Pin 6)       |
| DGND              +-------+ GND (Pin 6)       |
| CLK               +-------+ GPIO11 (Pin 23)   |
| DOUT              +-------+ GPIO9 (Pin 21)    |
| DIN               +-------+ GPIO10 (Pin 19)   |
| CS                +-------+ GPIO8 (Pin 24)    |
+-------------------+                           |
                                                |
+-------------------+                           |
| PAM8302A Amplifier|                           |
|-------------------|                           |
| VIN               +-------+ 5V (Pin 2)        |
| GND               +-------+ GND (Pin 6)       |
| OUT+              +-------+ Speaker+          |
| OUT-              +-------+ Speaker-          |
+-------------------+                           |
```

This diagram provides a basic overview of the connections between the Raspberry Pi, NFC reader, LED button, MCP3008 ADC (for volume and battery), and PAM8302A amplifier. For more detailed diagrams, consider using tools like Fritzing or Tinkercad.

### Enclosure Design

The enclosure can be 3D-printed or custom-made to house all components securely. Ensure the following:

1. **Ventilation**: Include openings for airflow to prevent overheating.
2. **Access Points**: Provide cutouts for the NFC reader, LED button, and speaker.
3. **Battery Compartment**: If using a powerbank, design a compartment to hold it securely.

#### Placeholder for Diagrams
- Wiring Diagram: *(To be added)*
- Enclosure Design Files: *(To be added)*

---

## Software Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/dimarconicola/storiellai.git
    cd storiellai
    ```

2.  **Install System Dependencies:**
    ```bash
    sudo apt update
    sudo apt install -y python3-pip python3-pygame libasound2-dev python3-dev libgpiod2
    # For PN532 and MCP3008 SPI (if using libraries that need it)
    # sudo apt install -y libffi-dev build-essential
    ```

3.  **Enable SPI on Raspberry Pi:**
    *   Run `sudo raspi-config`.
    *   Navigate to `Interface Options` -> `SPI`.
    *   Enable SPI and reboot if prompted.

4.  **Install Python Dependencies:**
    *   It's recommended to use a virtual environment:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   Install required packages from `requirements.txt`:
        ```bash
        pip install -r requirements.txt
        ```
        The `requirements.txt` should include:
        ```
        RPi.GPIO
        pygame
        adafruit-circuitpython-mcp3008
        adafruit-circuitpython-pn532
        ```

5.  **Configure Audio:**
    *   Ensure audio output is correctly configured in Raspberry Pi OS (e.g., to HDMI, 3.5mm jack, or I2S DAC). Use `raspi-config` under `System Options` -> `Audio`.

6.  **Set up as a Service (Optional but Recommended):**
    *   The repository includes service files in the `systemd/` folder for both Linux (systemd) and macOS (launchd).
    *   For Raspberry Pi (Linux), copy the service file:
        ```bash
        sudo cp systemd/storyteller.service /etc/systemd/system/
        ```
    *   Enable and start the service:
        ```bash
        sudo systemctl daemon-reload
        sudo systemctl enable storyteller.service
        sudo systemctl start storyteller.service
        ```
    *   For macOS, copy the plist file:
        ```bash
        cp systemd/storyteller.plist ~/Library/LaunchAgents/
        launchctl load ~/Library/LaunchAgents/storyteller.plist
        ```

---

## Adding New Stories

The offline version relies on pre-recorded audio files and JSON configurations.

1.  **Record Narration:**
    *   Record your story narration as an MP3 file (e.g., `my_new_story_part1.mp3`).
    *   Place these audio files in a structured way, for example, inside `src/audio/<card_uid>/`.

2.  **Prepare Background Music:**
    *   Ensure you have loopable background music files (MP3) in `src/bgm/` named according to tones (e.g., `calmo_loop.mp3`, `avventuroso_loop.mp3`).

3.  **Create/Update JSON Configuration:**
    *   For each NFC card, create a JSON file in `src/storiesoffline/` named `card_<UID>.json` (e.g., `card_000000.json`).
    *   The JSON structure should be:
        ```json
        {
          "card_title": "The Adventures of Leo the Lion",
          "stories": [
            {
              "id": "1",
              "title": "Leo's First Roar",
              "audio": "audio/000000/leo_roar.mp3", // Relative path from src/
              "tone": "avventuroso",
              "bedtime_suitable": false
            },
            {
              "id": "2",
              "title": "Leo Makes a Friend",
              "audio": "audio/000000/leo_friend.mp3",
              "tone": "tenero",
              "bedtime_suitable": true
            }
            // ... more stories for this card
          ]
        }
        ```
    *   `"audio"`: Path to the narration MP3 file, relative to the `src/` directory.
    *   `"tone"`: Matches a BGM file in `src/bgm/` (e.g., "avventuroso" uses `avventuroso_loop.mp3`).
    *   `"bedtime_suitable"`: `true` or `false`.

4.  **Write UID to NFC Card:**
    *   Use an NFC writing tool (e.g., "NFC Tools" app on a smartphone) to write the plain text UID (e.g., "000000") to an NFC card. This UID must match the `card_<UID>.json` filename.

5.  **Using storellai-audiobook Script:**
    *   To add new stories, you can use the [storellai-audiobook](https://github.com/dimarconicola/storellai-audiobook) script. This script uses Google APIs to generate audio files from a provided story JSON file and places them in the correct folder. Ensure you have the JSON file ready before running the script.

---

## Usage

1.  **Power On:** Connect the power supply. The system should boot, and the `box.py` script will start (if set up as a service). The LED button might pulse to indicate it\'s ready.
2.  **Place Card:** Place an NFC card on the reader.
3.  **Listen:** The story associated with the card will begin playing with background music. The volume can be adjusted using the volume knob.
4.  **Button Controls:**
    *   **Tap (Short Press):**
        *   If a story is playing: Pause/Resume the story.
        *   If idle (no story playing/paused): Replay the last played story from the beginning. If no story was played since startup or after a new card, this might do nothing or play a default "ready" sound if implemented.
    *   **Double-Tap:** Skip to a new random story from the *current* NFC card (if the card has multiple stories). If the card has only one story, or if no card is active, this might replay the current story or do nothing.
    *   **Long Press (e.g., 1.5-3 seconds):** Initiate a safe shutdown of the Raspberry Pi. The LED might blink rapidly during shutdown.

---

## Troubleshooting

*   **No audio:**
    *   Check speaker and amplifier connections.
    *   Verify audio output settings in `raspi-config`.
    *   Test with `aplay /usr/share/sounds/alsa/Front_Center.wav`.
    *   Check `pygame` mixer initialization in logs: `cat src/storyteller.log | grep mixer`.

*   **Volume knob not working:**
    *   Verify MCP3008 wiring, especially SPI connections (CLK, MISO, MOSI, CS) and power (VDD, VREF, GNDs).
    *   Ensure the correct ADC channel is used in `app_config.py` (`ADC_CHANNEL_VOLUME`).
    *   Check potentiometer wiring (GND, Wiper to ADC channel, 3.3V).
    *   Test the MCP3008 with a simple Python script example from the Adafruit library.

*   **NFC card not read:**
    *   Verify PN532 wiring and SPI configuration.
    *   Check if the NFC card UID matches a `card_<UID>.json` file.
    *   Look for NFC reader errors in the log: `cat src/storyteller.log | grep UID`.
    *   Try creating a card with a simple numeric UID (e.g., "000001").

*   **Script not running on boot:**
    *   Check systemd service status: `sudo systemctl status storyteller.service`.
    *   Check service logs: `journalctl -u storyteller.service`.
    *   Verify paths in `storyteller.service` match your actual installation.

*   **LED not working:**
    *   Check the LED connection to the GPIO pin specified in `app_config.py`.
    *   Verify the button's LED wiring (usually has a positive and ground connection).
    *   Test with a simple Python script to toggle the LED.

*   **Battery monitoring issues:**
    *   Verify the voltage divider is correctly connected to the MCP3008.
    *   Check the channel assignment in `time_utils.py`.
    *   Test the ADC with a simple script to read and print the voltage.
    *   Look for battery-related entries in the log: `cat src/storyteller.log | grep battery`.

*   **Unexpected errors or crashes:**
    *   Check the structured logs for details: `cat src/storyteller.log`.
    *   Look for error traces: `cat src/storyteller_error.log`.
    *   If the error is reproducible, try running manually: `cd src && python box.py`.
    *   Check if audio files exist and aren't corrupted.

---

## Future Ideas

*   Add gesture control (tap sequence patterns for different functions)
*   Create a simple web interface for managing stories on the SD card (accessible via local network)
*   Support for multiple narrations per story (different voices, languages)
*   "Shuffle all stories" mode triggered by a special NFC card
*   Ambient light sensor to automatically adjust LED brightness
*   Sleep timer function (play for N minutes then fade out)
*   Record and play back child's own narration
*   Add simple text-to-speech capability for dynamic content
*   Incorporate a small display for basic status information and story titles
*   Create companion app for managing content via Bluetooth
