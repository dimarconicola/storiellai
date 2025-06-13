# Storyteller Box Deployment Guide: Creating a Master Image

Thi8.  **Set Up Auto-Start Service:**
    *   Copy the provided systemd service file to the system directory:
        ```bash
        sudo cp systemd/storyteller.service /etc/systemd/system/
        ```
    *   Reload the systemd daemon:
        ```bash
        sudo systemctl daemon-reload
        ```
    *   Enable the service to start on boot:
        ```bash
        sudo systemctl enable storyteller.service
        ```
9.  **Test Logging Setup:**
    *   The system uses structured logging with rotation
    *   Check that logging is configured correctly:
        ```bash
        # Run the application manually
        cd /home/pi/storiellai/src
        python3 box.py
        
        # Stop with Ctrl+C after a moment and check logs
        cat storyteller.log
        ```
    *   Ensure log rotation works and error logs are captured
10. **Thoroughly Test:**es the process for creating a master Raspberry Pi OS image for the Storyteller Box. This allows for quick and easy replication of the software setup onto multiple Raspberry Pi units, ideal for creating gifts or multiple instances of the device.

## Overview

The core idea is to set up one Raspberry Pi perfectly (the "master" Pi), then create a disk image of its SD card. This image can then be flashed onto new SD cards, creating identical copies.

## Steps to Create the Master Image

**Phase 1: Prepare the Master Raspberry Pi**

1.  **Select a Raspberry Pi:** Use a Raspberry Pi model identical to the ones you'll be deploying on (e.g., Raspberry Pi Zero 2 W).
2.  **Flash Base OS:**
    *   Download the latest "Raspberry Pi OS Lite" from the [official Raspberry Pi website](https://www.raspberrypi.com/software/operating-systems/).
    *   Use the "Raspberry Pi Imager" tool (available for macOS, Windows, Linux) to flash the OS Lite image onto a high-quality microSD card.
3.  **Initial Boot & Configuration:**
    *   Insert the SD card into the master Pi, connect a keyboard, monitor, and power it on.
    *   Complete the initial setup wizard (set username/password, locale, etc.). It's recommended to change the default `pi` user's password.
    *   **Connect to Network:** Configure Wi-Fi or connect via Ethernet. This is crucial for downloading software.
        *   *Note for Gifts:* Decide how the final devices will connect to Wi-Fi. If you pre-configure it with specific credentials, the recipient's network must match, or they'll need to reconfigure it. See "Wi-Fi Considerations for Gifts" below.
    *   **Enable SSH:**
        ```bash
        sudo systemctl enable ssh
        sudo systemctl start ssh
        ```
        (Or use `sudo raspi-config` -> `Interface Options` -> `SSH` -> `Enable`). This allows remote access from your main computer.
    *   **Enable SPI:**
        Use `sudo raspi-config`:
        Navigate to `Interface Options` -> `SPI` -> `Enable`.
    *   **Update System:**
        ```bash
        sudo apt update
        sudo apt upgrade -y
        ```
4.  **Install Project Dependencies:**
    *   Install Git:
        ```bash
        sudo apt install git -y
        ```
    *   Install Python 3 pip and other system dependencies:
        ```bash
        sudo apt install python3-pip python3-pygame libasound2-dev python3-dev libgpiod2 -y
        ```
5.  **Clone Your Application:**
    *   Navigate to the desired directory:
        ```bash
        cd /home/pi/
        git clone https://github.com/dimarconicola/storiellai.git
        cd storiellai
        ```
6.  **Install Python Requirements:**
    *   Install Python packages:
        ```bash
        pip3 install -r requirements.txt
        ```
7.  **Hardware Configuration:**
    *   If using the battery monitoring feature:
        *   Connect a voltage divider to the power source and to MCP3008 Channel 1 (or as configured in `time_utils.py`)
        *   The voltage divider should reduce the 5V input to a safe level for the ADC (≤3.3V)
        *   Adjust `LOW_BATTERY_THRESHOLD` and `CRITICAL_BATTERY_THRESHOLD` in `src/utils/time_utils.py` if needed
    *   If using custom LED patterns:
        *   The system uses the `LedPatternManager` in `src/utils/led_utils.py` for visual feedback
        *   You can customize patterns for different states (boot, ready, error, etc.)
8.  **Set Up Auto-Start Service:**
    *   Copy your systemd service file to the system directory:
        ```bash
        sudo cp systemd/storyteller.service /etc/systemd/system/
        ```
    *   Reload the systemd daemon:
        ```bash
        sudo systemctl daemon-reload
        ```
    *   Enable the service to start on boot:
        ```bash
        sudo systemctl enable storyteller.service
        ```
8.  **Thoroughly Test:**
    *   Reboot the Raspberry Pi: `sudo reboot`.
    *   Verify that your application starts automatically and all features work as expected (NFC reading, audio playback, button controls, LED feedback, battery monitoring if applicable).
    *   Check logs for any errors: `sudo journalctl -u storyteller.service -f` and your application-specific logs.

**Phase 2: Prepare the Master Pi for Imaging**

1.  **Clean Up:**
    *   Remove unnecessary packages: `sudo apt autoremove -y`
    *   Clean package cache: `sudo apt clean`
    *   Clear bash history: `history -c && history -w`
    *   Clear log files to start fresh:
        ```bash
        cd /home/pi/storiellai/src
        rm -f storyteller.log*
        rm -f storyteller_error.log*
        ```
    *   Remove any test files or temporary data
2.  **Wi-Fi Considerations for Gifts:**
    *   **Option 1 (Simplest for recipient if credentials match):** If the master Pi is configured with the recipient's Wi-Fi, you're set.
    *   **Option 2 (Generic Setup):** Remove specific Wi-Fi credentials from `/etc/wpa_supplicant/wpa_supplicant.conf` before imaging. The recipient will need to connect a keyboard/monitor or use Ethernet to set up their Wi-Fi.
    *   **Option 3 (Advanced - Access Point Mode):** Configure the Pi to start as a Wi-Fi Access Point on first boot, allowing the user to connect to it and enter their credentials via a web page. This is more complex to set up.
    *   **Option 4 (Manual `wpa_supplicant.conf`):** After flashing the image to a *new* SD card, you can mount its `rootfs` partition on your computer and manually edit `/etc/wpa_supplicant/wpa_supplicant.conf` with the recipient's details before giving them the card.

**Phase 3: Create the Disk Image**

1.  **Shut Down Master Pi:**
    ```bash
    sudo shutdown now
    ```
    Wait for the Pi to fully power down, then disconnect its power.
2.  **Remove SD Card:** Carefully remove the microSD card from the master Pi.
3.  **Connect SD Card to Your Computer:** Use an SD card reader.
4.  **Create the Image File:**
    *   **Using Raspberry Pi Imager:**
        *   Select "Choose OS" -> "Use custom".
        *   Instead of choosing an OS, there should be an option to "Read" from an existing drive to an image file, or a utility within it for imaging drives. (The exact wording might vary by Imager version).
        *   Alternatively, under "Operating System", choose "Erase" to format a USB drive, then under "Storage" select your SD card. Then, for "Operating System", choose "Copy OS" (or similar) and select your SD card as the source and the USB drive (or a file path) as the destination.
    *   **Using ApplePi-Baker (macOS):**
        *   A popular third-party tool. Select your SD card and use the "Backup" feature to create an `.img` file.
    *   **Using `dd` (macOS/Linux Terminal - Advanced):**
        *   Identify your SD card: `diskutil list` (macOS) or `lsblk` (Linux). Be **extremely careful** to identify the correct disk (e.g., `/dev/diskN` on macOS, `/dev/sdX` on Linux).
        *   Unmount the SD card (replace `/dev/diskN` with the correct identifier):
            ```bash
            # macOS
            diskutil unmountDisk /dev/diskN
            # Linux (unmount all partitions of the disk)
            # sudo umount /dev/sdX1 /dev/sdX2 ...
            ```
        *   Create the image (replace `/dev/rdiskN` or `/dev/sdX` and the output path):
            ```bash
            # macOS (use rdisk for faster raw access)
            sudo dd if=/dev/rdiskN of=~/Desktop/storyteller_master.img bs=1m status=progress
            # Linux
            sudo dd if=/dev/sdX of=/path/to/storyteller_master.img bs=4M status=progress
            ```
            **WARNING:** `dd` is a powerful tool. A mistake in `if` (input file) or `of` (output file) can lead to data loss. Double-check everything.
        *   The process can take a while depending on SD card size and speed.

**Phase 4: Deploying the Image to New SD Cards**

1.  **Get New SD Cards:** Ensure they are of sufficient capacity (same size or larger than the original master SD card).
2.  **Flash the Master Image:**
    *   Use "Raspberry Pi Imager":
        *   Choose "Operating System" -> "Use custom".
        *   Select your `storyteller_master.img` file.
        *   Choose your new SD card as the "Storage".
        *   Click "Write".
    *   Or use ApplePi-Baker ("Restore" function) or `dd` (carefully, reversing `if` and `of` to write to the SD card).
3.  **(Optional) Post-Flash Wi-Fi Configuration:** If you opted to configure Wi-Fi manually per card (Option 4 in "Wi-Fi Considerations"), mount the newly flashed SD card's `rootfs` partition on your computer and edit `/etc/wpa_supplicant/wpa_supplicant.conf` with the specific Wi-Fi details for that gift.
4.  **Install in New Pi:** Insert the newly flashed SD card into a new Raspberry Pi, power it on, and it should boot up as a clone of your master setup.

## Maintaining the Master Image

If you update your application or system software:

1.  Update your **master Raspberry Pi** first.
2.  Test thoroughly.
3.  Repeat **Phase 2 (Prepare for Imaging)** and **Phase 3 (Create Disk Image)** to create a new version of your `storyteller_master.img`.

This ensures your deployment image always has the latest stable version of your project.
