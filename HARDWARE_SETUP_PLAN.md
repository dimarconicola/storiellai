# Hardware Setup Plan - REVISED

## 🎯 **Strategy: Test Complete Components, Not Individual Parts**
Test each physical component as a complete unit, then integrate with software.

## 📋 **Hardware Setup Checklist - REVISED**

### **Phase 1: Simple LED Test (Validation) ✅**
**Goal:** Verify Pi GPIO output works before testing integrated components
- [x] Connect standalone LED to GPIO 24 with 220Ω resistor
- [x] Test LED on/off with basic script
- [x] Verify Pi can control external hardware
- **Success Criteria:** LED turns on/off reliably ✅ **COMPLETED**
- **Time Estimate:** 5 minutes
- **Risk Level:** Very Low
- **Why:** Quick validation that GPIO/wiring basics work

### **Phase 2: 4-Pin Button with Integrated LED ✅**
**Goal:** Test complete button unit (switch + LED together)
- [x] Connect 4-pin button (switch pins to GPIO 23 + 3.3V, LED pins to GPIO 24 + GND)
- [x] Add 10kΩ pull-down resistor for button
- [x] Add 220Ω current-limiting resistor for LED
- [x] Test LED control independently
- [x] Test button press detection
- [x] Test button events (tap, double-tap, long-press)
- [x] Test LED responds to button presses
- **Success Criteria:** Button presses detected AND integrated LED responds ✅ **COMPLETED**
- **Time Estimate:** 25 minutes
- **Risk Level:** Medium

**✅ Phase 2 Wiring Documentation:**
```
Pi to Breadboard:
Pin 16 (GPIO 23) → a1    Pin 17 (3.3V) → a2
Pin 18 (GPIO 24) → a3    Pin 20 (GND) → a5

4-Pin Button to Breadboard:
Switch Pin 1 → b1    Switch Pin 2 → b2
LED + Pin → b4       LED - Pin → b5

Resistors:
10kΩ: c1 ↔ c5 (pull-down)    220Ω: b3 ↔ a4 (LED current limit)
Additional: a4 ↔ b4 (connect LED circuit)
```

### **Phase 3: 4-Pin Button Integration with Software ✅/❌**
**Goal:** Button controls actual Storyteller Box functions
- [ ] Enable real hardware mode in HAL
- [ ] Test button with full Storyteller Box application
- [ ] Verify pause/resume works (single tap)
- [ ] Verify skip works (double tap)
- [ ] Verify new story works (long press)
- [ ] Verify LED shows system status
- **Success Criteria:** Button fully controls story playback
- **Time Estimate:** 15 minutes
- **Risk Level:** Low (hardware already tested)

### **Phase 4: Volume Control (MCP3008 + Potentiometer) ✅/❌**
**Goal:** Add analog volume control
- [ ] Connect MCP3008 to SPI bus (MOSI, MISO, CLK, CS)
- [ ] Connect potentiometer to ADC channel 0
- [ ] Test raw ADC readings (0-1023)
- [ ] Test volume control in software
- [ ] Verify volume changes affect audio output
- **Success Criteria:** Turning knob changes system volume
- **Time Estimate:** 30 minutes
- **Risk Level:** Medium-High (SPI complexity)

### **Phase 5: RFID Reader (RC522) ✅**
**Goal:** Add card reading for story selection
- [x] Connect RC522 to SPI bus (SDA=GPIO8/Pin24, SCK=Pin23, MOSI=Pin19, MISO=Pin21, GND=Pin30, RST=GPIO25/Pin22, 3.3V=Pin1)
- [x] Enable SPI in raspi-config
- [x] Install MFRC522 Python library (`pip3 install mfrc522`)
- [x] Test basic UID reading and data writing with test scripts (`read_card.py`, `write_card.py`)
- [x] Register card UID and associate with a story (see below)
- [x] Test story switching with different cards
- [x] Verify RFID integration with full application
- **Success Criteria:** Different cards trigger different stories ✅ **COMPLETED**
- **Time Estimate:** 35 minutes
- **Risk Level:** High (complex SPI, timing sensitive)

**Phase 5 Wiring Documentation:**
```
RC522 Pin   → Raspberry Pi Pin
SDA         → GPIO8 (Pin 24)
SCK         → SCLK (Pin 23)
MOSI        → MOSI (Pin 19)
MISO        → MISO (Pin 21)
GND         → GND (Pin 30)
RST         → GPIO25 (Pin 22)
3.3V        → 3.3V (Pin 1)
IRQ         → Not connected
```

**Phase 5 Config Documentation:**
- SPI enabled via `sudo raspi-config` > Interface Options > SPI > Enable
- Library installed: `pip3 install mfrc522 spidev`
- Test scripts used for UID reading and writing: `read_card.py`, `write_card.py`

---

**How to Associate a Card with a Story (New Method)**

The system no longer relies on the card's unchangeable UID. Instead, you write a **Story ID** as plain text directly onto the card. This makes managing your story library much more flexible.

**To associate a new card:**

1.  **Create a Story File:**
    *   Make sure you have a story file in the `src/stories/` directory. For example, `card_000001.json`.
    *   The **Story ID** is the part of the filename after `card_` and before `.json`. In this case, the Story ID is `000001`.

2.  **Write the Story ID to the Card:**
    *   Use your `write_card.py` script to write the Story ID string (`000001`) to a blank NFC card.

3.  **Run the Application:**
    *   Start the Storyteller Box by running `python3 src/box.py`.

4.  **Tap the Card:**
    *   When you place the card on the reader, the application will:
        1.  Read the text "000001" from the card.
        2.  Look for a file named `card_000001.json`.
        3.  Load the story from that file and start playing it.

This approach means you no longer need to edit any configuration files to map UIDs. You can create new stories and assign them to cards just by writing the corresponding ID.

---

**Next Step: Continue Testing**
- Use `write_card.py` to write a story ID (e.g., "000000") to a card.
- Run `python3 src/box.py` and tap the card to see if it plays the story.
- Try creating a new story file (e.g., `card_000002.json`) and writing "000002" to a different card to test story switching.

Let me know when you're ready to test or move on to the next hardware phase!

### **Phase 6: Audio Output (Speaker/Amplifier) ✅/❌**
**Goal:** Complete audio chain with volume control
- [x] Identify I2S DAC chip (PCM5102A)
- [x] Edit /boot/config.txt:
  - Add at end:
    ```
    dtparam=audio=off
    dtoverlay=hifiberry-dac
    ```
- [x] Wire I2S DAC to Pi:
  - 5V (Pin 2 or 4) → DAC VCC
  - GND (Pin 6, 9, etc.) → DAC GND
  - Pin 12 (GPIO 18) → DAC BCLK
  - Pin 35 (GPIO 19) → DAC LRCK
  - Pin 40 (GPIO 21) → DAC DIN
- [x] Connect DAC OUT (L/R, GND) → PAM8302A IN+ and IN-
- [x] PAM8302A OUT+ and OUT- → Speaker
- [x] Power amplifier from Pi (5V, GND)
- [x] Reboot Pi
- [x] Run `aplay -l` and verify `card 1: sndrpihifiberry` appears
- [x] (Optional) Edit /etc/asound.conf to set default audio device:
  ```
  defaults.pcm.card 1
  defaults.ctl.card 1
  ```
- [x] Test audio playback:
  - `speaker-test -c2 -twav -l3` or `aplay /usr/share/sounds/alsa/Front_Center.wav`
- [ ] Troubleshoot if no sound (check overlay, wiring, power, dmesg)
- [ ] Document working config and wiring
- [ ] Test volume control affects actual audio
- [ ] Test full story playback with audio
- **Success Criteria:** Stories play audibly with volume control
- **Time Estimate:** 15 minutes
- **Risk Level:** Low (mostly software configuration)

**Phase 6 Wiring Documentation:**
```
Pi Header → PCM5102A DAC:
Pin 2 (5V)      → VCC
Pin 6 (GND)     → GND
Pin 12 (GPIO18) → BCLK
Pin 35 (GPIO19) → LRCK
Pin 40 (GPIO21) → DIN

PCM5102A OUTL/OUTR/GND → PAM8302A IN+/IN-
PAM8302A OUT+/OUT-     → Speaker
PAM8302A VCC/GND       → Pi 5V/GND
```

**Phase 6 Config Documentation:**
- `/boot/config.txt`:
  ```
  dtparam=audio=off
  dtoverlay=hifiberry-dac
  ```
- `/etc/asound.conf` (optional):
  ```
  defaults.pcm.card 1
  defaults.ctl.card 1
  ```
- Test command: `aplay -l` (should show `sndrpihifiberry`)
- Test playback: `speaker-test -c2 -twav -l3` or `aplay /usr/share/sounds/alsa/Front_Center.wav`

**Troubleshooting:**
- If no sound: check overlay spelling, wiring, power, run `dmesg | grep -i hifi`.
- If only HDMI audio: double-check `/boot/config.txt` and reboot.

---

## 📑 **Raspberry Pi Pinout and Component Mapping**

### **GPIO and Pin Usage by Component**

| Component         | Pi Pin (Header) | GPIO # | Function/Signal | Description/Usage                         |
|-------------------|-----------------|--------|-----------------|-------------------------------------------|
| 4-Pin Button      | Pin 16          | GPIO23 | Button Switch   | Reads button press                        |
|                   | Pin 17          | 3.3V   | Power           | Powers button circuit                     |
|                   | Pin 18          | GPIO24 | Button LED      | Controls button LED                       |
|                   | Pin 20          | GND    | Ground          | Ground for button                         |
| MCP3008 (ADC)     | Pin 19          | GPIO10 | MOSI            | SPI data to MCP3008                       |
|                   | Pin 21          | GPIO9  | MISO            | SPI data from MCP3008                     |
|                   | Pin 23          | GPIO11 | SCLK            | SPI clock                                |
|                   | Pin 24          | GPIO8  | CS0             | SPI chip select (shared with RC522)       |
|                   | Pin 25          | GND    | Ground          | Ground for MCP3008                        |
|                   | Pin 1           | 3.3V   | Power           | Power for MCP3008                         |
| Potentiometer     | MCP3008 CH0     | -      | Analog In       | Volume control input                      |
| RC522 RFID        | Pin 24          | GPIO8  | SDA/CS          | SPI chip select for RC522                 |
|                   | Pin 23          | GPIO11 | SCK             | SPI clock                                |
|                   | Pin 19          | GPIO10 | MOSI            | SPI data to RC522                         |
|                   | Pin 21          | GPIO9  | MISO            | SPI data from RC522                       |
|                   | Pin 30          | GND    | Ground          | Ground for RC522                          |
|                   | Pin 22          | GPIO25 | RST             | Reset for RC522                           |
|                   | Pin 1           | 3.3V   | Power           | Power for RC522                           |
| PCM5102A DAC      | Pin 2           | 5V     | VCC             | Power for DAC                             |
|                   | Pin 6           | GND    | Ground          | Ground for DAC                            |
|                   | Pin 12          | GPIO18 | BCLK            | I2S bit clock                             |
|                   | Pin 35          | GPIO19 | LRCK            | I2S word select                           |
|                   | Pin 40          | GPIO21 | DIN             | I2S data in                               |
| PAM8302A Amp      | -               | -      | IN+/IN-         | Audio input from DAC                      |
|                   | -               | -      | OUT+/OUT-       | Output to speaker                         |
|                   | Pin 2/4         | 5V     | VCC             | Power for amplifier                       |
|                   | Pin 6/9/etc     | GND    | Ground          | Ground for amplifier                      |

---
