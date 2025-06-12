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
3.  [Bill of Materials](#bill-of-materials)
4.  [Hardware Setup](#hardware-setup)
5.  [Software Setup](#software-setup)
6.  [Adding New Stories](#adding-new-stories)
7.  [Usage](#usage)
8.  [Troubleshooting](#troubleshooting)
9.  [Future Ideas](#future-ideas)
10. [Repo Layout](#repo-layout)

---

## Overview

Storyteller Box is a small bedside companion that **tells pre-recorded Italian fairy tales** triggered by NFC cards. Children place an NFC-tagged card on the lid, and the box plays a corresponding story with matching background music. The device is **fully offline**, with all narration and music pre-loaded onto an SD card.

-   **No internet required:** All stories and background music are pre-recorded and stored locally.
-   **Simple controls:** A single illuminated button handles play, pause, and shutdown.
-   **Calm time logic:** Automatically selects calm stories during bedtime hours.
-   **Parent-friendly:** Easily add new stories and music by copying files to the SD card.

---

## How It Works

1.  **NFC Card Scan:** The child places an NFC card on the box.
2.  **Story Lookup:** The `box_offline.py` script reads the card's UID and looks up the corresponding story configuration in a JSON file located in `src/storiesoffline/`.
3.  **Audio Playback:**
    *   The script selects an appropriate background music track based on the story's defined "tone" (e.g., "calmo", "avventuroso").
    *   It plays the pre-recorded narration audio file for the selected story.
    *   `pygame` is used for audio mixing and playback.
4.  **Button Control:** A single button allows the child to play/pause the current story or initiate a shutdown.
5.  **LED Feedback:** The button's LED provides visual feedback (e.g., pulsing when ready, solid when playing).

---

## Bill of Materials (BOM)

| Component             | Description                                      | Est. Price (EUR) | Notes                                                                 |
| :-------------------- | :----------------------------------------------- | :--------------- | :-------------------------------------------------------------------- |
| Raspberry Pi Zero 2 W | Microcontroller board                            | 15-20            | Or any compatible Raspberry Pi (3B+, 4, etc.)                         |
| PN532 NFC Reader      | NFC/RFID reader module (SPI interface preferred) | 5-10             |                                                                       |
| Micro SD Card         | 16GB or larger, Class 10                         | 5-10             | For OS and audio files                                                |
| Speaker               | 3W, 4 Ohm full-range speaker                     | 3-5              | Adafruit #1314 or similar                                             |
| PAM8302A Amplifier    | 2.5W Mono Class D Audio Amplifier                | 2-4              | Or similar I2S/analog amplifier compatible with Pi                    |
| LED Button            | Illuminated momentary push button                | 2-4              |                                                                       |
| Power Supply          | 5V, 2.5A Micro USB power supply                  | 5-10             |                                                                       |
| Jumper Wires          | Assorted male/female                             | 2-5              |                                                                       |
| NFC Cards/Tags        | NTAG215 or similar (compatible with PN532)       | 0.50-1 per card  |                                                                       |
| Enclosure             | 3D printed or custom-made box                    | 5-20             | Material cost if 3D printing                                          |
| **Optional:**         |                                                  |                  |                                                                       |
| USB Sound Card        | If Pi's onboard audio is noisy                   | 5-10             |                                                                       |
| Soldering Iron & Tin  | For connecting components                        | -                | If not using breadboard/jumper wires for permanent connections        |
| **Total Estimated:**  |                                                  | **45-90 EUR**    | Excluding optional items and tools                                    |

---

## Hardware Setup

*(Detailed wiring diagrams and enclosure design files will be added here or in a separate `hardware/` directory.)*

1.  **Raspberry Pi:** Prepare the Raspberry Pi by flashing Raspberry Pi OS Lite.
2.  **NFC Reader (PN532):**
    *   Connect to the Raspberry Pi via SPI.
    *   **SPI Pins (Pi Zero 2 W):**
        *   `SCLK` (PN532) -> `GPIO11` (Pi SCLK)
        *   `MISO` (PN532) -> `GPIO9` (Pi MISO)
        *   `MOSI` (PN532) -> `GPIO10` (Pi MOSI)
        *   `SS/SSEL` (PN532) -> `GPIO8` (Pi CE0) (or another GPIO if using software SPI select)
        *   `IRQ` (PN532) -> A chosen GPIO (e.g., `GPIO25`)
        *   `RST` (PN532) -> A chosen GPIO (e.g., `GPIO17`)
3.  **Audio Output:**
    *   Connect the PAM8302A amplifier input to the Raspberry Pi's audio output (either 3.5mm jack or GPIO pins if using I2S).
    *   Connect the speaker to the amplifier's output.
    *   *Alternatively, use an I2S DAC like MAX98357A or PCM5102A for better audio quality.*
4.  **LED Button:**
    *   Connect the button switch to a GPIO pin (e.g., `GPIO23`) and GND.
    *   Connect the button's LED (with an appropriate resistor) to another GPIO pin (e.g., `GPIO24`) and GND.
5.  **Power:** Power the Raspberry Pi using the Micro USB power supply.

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
    sudo apt install -y python3-pip python3-pygame libasound2-dev
    # For PN532 SPI (if using a library that needs it)
    # sudo apt install -y libffi-dev
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
    *   Install required packages (a `requirements.txt` will be provided):
        ```bash
        # pip install RPi.GPIO spidev pygame python-pn532 # Example packages
        # For now, ensure pygame is installed as per system dependencies.
        # A full requirements.txt will be generated based on the final hardware choices.
        ```
        *(Note: The exact Python libraries for NFC will depend on the chosen PN532 library. `python-pn532` is a common one for SPI.)*

5.  **Configure Audio:**
    *   Ensure audio output is correctly configured in Raspberry Pi OS (e.g., to HDMI, 3.5mm jack, or I2S DAC). Use `raspi-config` under `System Options` -> `Audio`.

6.  **Set up as a Service (Optional but Recommended):**
    *   Create a systemd service file to run `box_offline.py` on boot.
    *   Example `storyteller.service` file (`/etc/systemd/system/storyteller.service`):
        ```ini
        [Unit]
        Description=Storyteller Box Service
        After=network.target sound.target

        [Service]
        ExecStart=/usr/bin/python3 /home/pi/storiellai/src/box.py
        WorkingDirectory=/home/pi/storiellai/src
        StandardOutput=inherit
        StandardError=inherit
        Restart=always
        User=pi # Or your username

        [Install]
        WantedBy=multi-user.target
        ```
    *   Enable and start the service:
        ```bash
        sudo systemctl daemon-reload
        sudo systemctl enable storyteller.service
        sudo systemctl start storyteller.service
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

---

## Usage

1.  **Power On:** Connect the power supply. The system should boot, and the `box.py` script will start (if set up as a service). The LED button might pulse to indicate it's ready.
2.  **Place Card:** Place an NFC card on the reader.
3.  **Listen:** The story associated with the card will begin playing with background music.
4.  **Button Controls:**
    *   **Short Press (while idle):** If a story was previously selected, it might replay or play the next in a sequence (if implemented).
    *   **Short Press (while playing):** Pause/Resume the story.
    *   **Long Press (e.g., 3 seconds):** Initiate a safe shutdown of the Raspberry Pi.

---

## Troubleshooting

*   **No audio:**
    *   Check speaker and amplifier connections.
    *   Verify audio output settings in `raspi-config`.
    *   Test with `aplay /usr/share/sounds/alsa/Front_Center.wav`.
    *   Check `pygame` mixer initialization in logs.
*   **NFC card not read:**
    *   Verify PN532 wiring and SPI configuration.
    *   Ensure the correct Python library for PN532 is installed and used.
    *   Check if the NFC card UID matches a `card_<UID>.json` file.
*   **Script not running on boot:**
    *   Check systemd service status: `sudo systemctl status storyteller.service`.
    *   Check service logs: `journalctl -u storyteller.service`.

---

## Future Ideas

*   More sophisticated LED patterns for different states.
*   Web interface for managing stories on the SD card (would require adding back some web server components like Flask, but could still be local network only).
*   Support for multiple narrations per story part (e.g., different voices).
*   Physical volume knob.
*   Battery power option.

---

## Repo Layout

```
storiellai/
├── readme.md              # This file
├── .gitignore             # Files to ignore in git
├── src/
│   ├── box.py             # Main script for the offline storytelling box
│   ├── hardware/
│   │   └── hal.py         # Hardware Abstraction Layer (UIDReader, Button, etc.) + mocks
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── bgm_utils.py   # Background music utilities
│   │   └── story_utils.py # Story selection logic
│   ├── audio/             # Pre-recorded narration MP3 files (organized by card UID)
│   │   ├── 000000/
│   │   │   └── 1.mp3
│   │   └── ...
│   ├── bgm/               # Background music loop MP3 files (e.g., calmo_loop.mp3)
│   │   └── calmo_loop.mp3
│   ├── storiesoffline/    # JSON files defining stories for each NFC card UID
│   │   └── card_000000.json
│   └── config/            # Configuration files (if any, e.g. parent_config.py)
│       └── parent_config.py
└── requirements.txt       # Python dependencies (to be generated)
```
