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
5.  **LED Feedback:** The button's LED provides visual feedback (e.g., pulsing when ready, solid when playing).
6.  **Modular Design:** The codebase is now modular, with utility functions and configuration constants moved to dedicated modules for better maintainability.

---

## Repo Layout

```
root/
├── src/
│   ├── box.py                # Main application logic
│   ├── config/
│   │   └── app_config.py     # Configuration constants (paths, GPIO pins, etc.)
│   ├── utils/
│   │   ├── audio_utils.py    # Audio engine and playback utilities
│   │   ├── data_utils.py     # JSON and file utilities
│   │   ├── led_utils.py      # LED pattern manager
│   │   ├── time_utils.py     # Time-based logic utilities
│   │   └── bgm_utils.py      # Background music utilities
│   ├── hardware/             # Hardware abstraction layer
│   └── storiesoffline/       # JSON files for NFC card story mappings
├── models/                   # Pre-trained models (e.g., TinyLlama)
├── audio/                    # Audio files (narration, BGM)
├── requirements.txt          # Python dependencies
├── readme.md                 # Project documentation
└── systemd/                  # Systemd service files for auto-start
```

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
| MCP3008 ADC           | 8-Channel 10-Bit ADC with SPI Interface        | 2-4              | To read analog value from potentiometer                             |
| Powerbank Battery     | Portable battery pack for powering the device    | 10-20            |                                                                       |
| Jumper Wires          | Assorted male/female                             | 2-5              |                                                                       |
| NFC Cards/Tags        | NTAG215 or similar (compatible with PN532)       | 0.50-1 per card  |                                                                       |
| Enclosure             | 3D printed or custom-made box                    | 5-20             | Material cost if 3D printing                                          |
| **Optional:**         |                                                  |                  |                                                                       |
| USB Sound Card        | If Pi's onboard audio is noisy                   | 5-10             |                                                                       |
| Soldering Iron & Tin  | For connecting components                        | -                | If not using breadboard/jumper wires for permanent connections        |
| **Total Estimated:**  |                                                  | **50-100 EUR**   | Excluding optional items and tools                                    |

---

## Hardware Setup

*(Detailed wiring diagrams and enclosure design files will be added here or in a separate `hardware/` directory.)*

**General Connections:**
*   Ensure all components share a common ground (GND) with the Raspberry Pi.
*   Use appropriate resistors for LEDs if not built into the button assembly.

1.  **Raspberry Pi:** Prepare the Raspberry Pi by flashing Raspberry Pi OS Lite.
2.  **NFC Reader (PN532 - SPI):**
    *   Connect to the Raspberry Pi via SPI.
    *   **PN532 Pins -> Raspberry Pi Pins (BCM numbering):**
        *   `VCC` -> `3.3V` or `5V` (check PN532 module specs)
        *   `GND` -> `GND`
        *   `SCK/SCLK` (PN532) -> `GPIO11` (Pi SCLK)
        *   `MISO` (PN532) -> `GPIO9` (Pi MISO)
        *   `MOSI` (PN532) -> `GPIO10` (Pi MOSI)
        *   `SS/SSEL/CS` (PN532) -> `GPIO8` (Pi CE0) (or another GPIO if using software SPI select, e.g., `GPIO7` / CE1)
        *   `IRQ` (PN532, optional but recommended) -> A chosen GPIO (e.g., `GPIO25`)
        *   `RST` (PN532, optional) -> A chosen GPIO (e.g., `GPIO17`)
3.  **Audio Output (PAM8302A Amplifier & Speaker):**
    *   **PAM8302A Pins -> Raspberry Pi / Speaker:**
        *   `Vin` -> `5V` (Pi)
        *   `GND` -> `GND` (Pi)
        *   `A+` (Audio Input +) -> Raspberry Pi\'s `Audio L` (Tip of 3.5mm jack) or `DAC_L` if using I2S DAC.
        *   `A-` (Audio Input -) -> Raspberry Pi\'s `Audio GND` (Sleeve of 3.5mm jack) or `DAC_R` (can be tied to GND for mono from stereo source).
        *   `Speaker Output +` -> Speaker `+` terminal
        *   `Speaker Output -` -> Speaker `-` terminal
    *   *Alternatively, use an I2S DAC like MAX98357A or PCM5102A for better audio quality, connecting to I2S pins on the Pi.*
4.  **LED Button:**
    *   **Button Pins -> Raspberry Pi Pins (BCM numbering):**
        *   Button Switch Terminal 1 -> `GPIO23` (or chosen button pin)
        *   Button Switch Terminal 2 -> `GND`
        *   LED Anode (+) (usually marked) -> `GPIO24` (or chosen LED pin, via a current-limiting resistor e.g., 220-330 Ohm if not built-in)
        *   LED Cathode (-) (usually marked) -> `GND`
5.  **Volume Control (Potentiometer & MCP3008 ADC):**
    *   **Potentiometer Pins:**
        *   Terminal 1 (e.g., CCW limit) -> `GND` (Pi)
        *   Terminal 2 (Wiper) -> `CH0` (MCP3008, or chosen ADC channel)
        *   Terminal 3 (e.g., CW limit) -> `3.3V` (Pi)
    *   **MCP3008 Pins -> Raspberry Pi Pins (BCM numbering):**
        *   `VDD` (MCP3008) -> `3.3V` (Pi)
        *   `VREF` (MCP3008) -> `3.3V` (Pi) (connect to VDD for ratiometric reading)
        *   `AGND` (MCP3008) -> `GND` (Pi)
        *   `DGND` (MCP3008) -> `GND` (Pi)
        *   `CLK` (MCP3008) -> `GPIO11` (Pi SCLK)
        *   `DOUT` (MCP3008 MISO) -> `GPIO9` (Pi MISO)
        *   `DIN` (MCP3008 MOSI) -> `GPIO10` (Pi MOSI)
        *   `CS/SHDN` (MCP3008 Chip Select) -> `GPIO7` (Pi CE1) (or another free GPIO, e.g., `GPIO22`. Cannot share CE0 with PN532 if both are on SPI0)
        *   `CH0` - `CH7`: Analog inputs. Connect potentiometer wiper to one of these (e.g., `CH0`).
6.  **Power:** Power the Raspberry Pi using the Micro USB power supply.

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
    *   Check `pygame` mixer initialization in logs.
*   **Volume knob not working:**
    *   Verify MCP3008 wiring, especially SPI connections (CLK, MISO, MOSI, CS) and power (VDD, VREF, GNDs).
    *   Ensure the correct ADC channel is used in `hal.py`.
    *   Check potentiometer wiring (GND, Wiper to ADC channel, 3.3V).
    *   Test the MCP3008 with a simple Python script example from the Adafruit library.
*   **NFC card not read:**
    *   Verify PN532 wiring and SPI configuration.
    *   Ensure the correct Python library for PN532 is installed and used.
    *   Check if the NFC card UID matches a `card_<UID>.json` file.
*   **Script not running on boot:**
    *   Check systemd service status: `sudo systemctl status storyteller.service`.
    *   Check service logs: `journalctl -u storyteller.service`.

---

## Future Ideas

*   More sophisticated LED patterns for different states (e.g., story finished, error).
*   Web interface for managing stories on the SD card (would require adding back some web server components like Flask, but could still be local network only).
*   Support for multiple narrations per story part (e.g., different voices).
*   Battery power option with low-battery warning/shutdown.
*   "Shuffle all stories" mode, perhaps triggered by a special NFC card or a different button combination.
