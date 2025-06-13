#!/usr/bin/env python3
"""
Main application logic for the Storyteller Box (Offline Edition).
Handles NFC card reading, story selection, audio playback, button events, volume control, and LED feedback patterns.

- NFC cards trigger story playback (pre-recorded audio, offline only)
- Button supports tap (pause/play), double-tap (new story), long-press (shutdown)
- Volume knob via MCP3008 ADC
- LED feedback (solid, breathing, blink) via PWM
- Hardware abstraction via hal.py for easy testing/mocking
"""

import os
import time
import traceback
from pathlib import Path
import pygame
import sys  # For GPIO cleanup on exit
from utils.log_utils import logger

from hardware.hal import IS_RASPBERRY_PI, BUTTON_NO_EVENT, BUTTON_TAP, BUTTON_DOUBLE_TAP, BUTTON_LONG_PRESS
from utils.time_utils import handle_battery_status
from adafruit_mcp3xxx.analog_in import AnalogIn

if IS_RASPBERRY_PI:
    from hardware.hal import RealUIDReader, RealButton, RealVolumeControl
    import RPi.GPIO as GPIO  # For cleanup
else:
    from hardware.hal import MockUIDReader, MockButton, MockVolumeControl

# Import from utility modules
from utils.audio_utils import (
    initialize_audio_engine, set_system_volume, preload_bgm, 
    play_narration_with_bgm, test_audio_performance, play_error_sound
)
from utils.data_utils import load_card_stories, verify_audio_files
from utils.time_utils import is_calm_time, select_story_for_time
from utils.led_utils import LedPatternManager
from utils.bgm_utils import stop_bgm

# Import configuration
from config.app_config import (
    STATE_IDLE, STATE_PLAYING, STATE_PAUSED, STATE_SHUTTING_DOWN,
    LED_OFF, LED_ON
)

# ============ MAIN APPLICATION ============
def main():
    """
    Main application loop.
    - Initializes hardware abstraction (real or mock)
    - Handles state machine for NFC, audio, button, and LED
    - Integrates volume knob and error handling
    - Monitors battery status
    - Cleans up on exit
    """
    global master_volume_level
    if not initialize_audio_engine():
        logger.critical("Failed to initialize audio. Exiting.")
        if button:
            led_manager = LedPatternManager(button)
            led_manager.set_pattern('blink', period=0.15, duty=0.5)
        play_error_sound()
        return
    
    preload_bgm()
    
    current_card_uid = None
    current_story_data = None
    current_narration_path = None
    current_bgm_tone = None
    
    # Hardware Initialization
    reader = None
    button = None
    volume_ctrl = None
    adc = None
    
    try:
        if IS_RASPBERRY_PI:
            # GPIO pins - MUST BE CONFIGURABLE OR MATCH ACTUAL WIRING
            NFC_SPI_PORT = 0 
            NFC_SPI_CS_PIN = 0 # CE0 for SPI0
            NFC_IRQ_PIN = 25   # Example
            NFC_RST_PIN = 17   # Example
            BUTTON_PIN = 23
            LED_PIN = 24
            ADC_CHANNEL_VOLUME = 0 # MCP3008 channel for volume pot
            reader = RealUIDReader(spi_port=NFC_SPI_PORT, spi_cs_pin=NFC_SPI_CS_PIN, irq_pin=NFC_IRQ_PIN, rst_pin=NFC_RST_PIN)
            button = RealButton(button_pin=BUTTON_PIN, led_pin=LED_PIN)
            volume_ctrl = RealVolumeControl(adc_channel=ADC_CHANNEL_VOLUME)
            adc = AnalogIn()  # Initialize MCP3008 ADC
        else:
            reader = MockUIDReader()
            button = MockButton()
            volume_ctrl = MockVolumeControl()

        # Hardware check: if any critical component failed, signal error
        if reader is None or button is None or volume_ctrl is None:
            logger.critical("Hardware initialization failed.")
            if button:
                led_manager = LedPatternManager(button)
                led_manager.set_pattern('blink', period=0.1, duty=0.5)
            play_error_sound()
            return

        state = STATE_IDLE
        button.set_led(LED_ON) # LED on when idle, ready
        logger.info(f"System started, state: {state}")
        logger.info(f"Running on {'Raspberry Pi' if IS_RASPBERRY_PI else 'Mock Hardware'}")

        last_volume_check_time = time.monotonic()
        last_battery_check_time = time.monotonic()

        # Initial volume setting
        master_volume_level = volume_ctrl.get_volume() 
        set_system_volume(master_volume_level)

        led_manager = LedPatternManager(button)
        led_manager.set_pattern('breathing', period=2.5) # Start with breathing for idle

        while state != STATE_SHUTTING_DOWN:
            led_manager.update()

            # Volume control check (periodically)
            if time.monotonic() - last_volume_check_time > 0.2: # Check 5 times a second
                new_volume = volume_ctrl.get_volume()
                if abs(new_volume - master_volume_level) > 0.01: # Update if changed significantly
                    set_system_volume(new_volume)
                last_volume_check_time = time.monotonic()

            # Battery status check (periodically)
            if time.monotonic() - last_battery_check_time > 10:  # Check every 10 seconds
                handle_battery_status(adc, led_manager)
                last_battery_check_time = time.monotonic()

            # Button event handling
            button_event = button.get_event()

            if button_event == BUTTON_TAP:
                if state == STATE_PLAYING:
                    pygame.mixer.music.pause()
                    led_manager.set_pattern('breathing', period=2.5)
                    state = STATE_PAUSED
                    logger.info("Playback PAUSED")
                elif state == STATE_PAUSED:
                    pygame.mixer.music.unpause()
                    led_manager.set_pattern('solid', state=True)
                    state = STATE_PLAYING
                    logger.info("Playback RESUMED")

            elif button_event == BUTTON_DOUBLE_TAP:
                if current_card_uid and state in [STATE_PLAYING, STATE_PAUSED, STATE_IDLE]:
                    logger.info("Double tap: Reselecting story for current card.")
                    stop_bgm()
                    pygame.mixer.stop()
                    card_data = load_card_stories(current_card_uid)
                    if card_data and card_data.get("stories"):
                        stories = card_data["stories"]
                        selected_story = select_story_for_time(stories, is_calm_time())
                        current_narration_path = Path(__file__).parent / selected_story["audio"]
                        current_bgm_tone = selected_story.get("tone", "calmo")
                        if current_narration_path.exists():
                            logger.info(f"Playing new story: {selected_story['title']}")
                            play_narration_with_bgm(current_narration_path, current_bgm_tone)
                            led_manager.set_pattern('solid', state=True)
                            state = STATE_PLAYING
                        else:
                            logger.error(f"Audio for new story not found: {current_narration_path}")
                            led_manager.set_pattern('blink', period=0.15, duty=0.5, count=5)
                            play_error_sound()
                            state = STATE_IDLE
                    else:
                        logger.warning("No stories for current card on double tap, returning to idle.")
                        led_manager.set_pattern('solid', state=True)
                        state = STATE_IDLE

            elif button_event == BUTTON_LONG_PRESS:
                logger.info("Long press: Initiating shutdown.")
                led_manager.set_pattern('blink', period=0.2, duty=0.5, count=10)
                stop_bgm()
                pygame.mixer.stop()
                state = STATE_SHUTTING_DOWN
                continue

            # --- Card tap logic for all states ---
            uid = reader.read_uid()
            if uid and uid != current_card_uid:
                logger.info(f"New card {uid} detected. Interrupting current story (if any) and starting new.")
                stop_bgm()
                pygame.mixer.stop()
                current_card_uid = uid
                card_data = load_card_stories(uid)
                if not card_data or not card_data.get("stories"):
                    logger.error(f"No stories for card {uid}")
                    led_manager.set_pattern('blink', period=0.15, duty=0.5, count=5)
                    play_error_sound()
                    current_card_uid = None
                    state = STATE_IDLE
                    continue
                current_story_data = card_data["stories"]
                selected_story = select_story_for_time(current_story_data, is_calm_time())
                logger.info(f"Selected story: {selected_story['title']} (tone: {selected_story['tone']})")
                current_narration_path = Path(__file__).parent / selected_story["audio"]
                current_bgm_tone = selected_story.get("tone", "calmo")
                if not current_narration_path.exists():
                    logger.error(f"Audio file not found: {current_narration_path}")
                    led_manager.set_pattern('blink', period=0.15, duty=0.5, count=5)
                    play_error_sound()
                    current_card_uid = None
                    state = STATE_IDLE
                    continue
                logger.info(f"Transitioning to PLAYING state")
                play_narration_with_bgm(current_narration_path, current_bgm_tone)
                led_manager.set_pattern('solid', state=True)
                state = STATE_PLAYING

            # Main state machine logic
            if state == STATE_IDLE:
                led_manager.set_pattern('breathing', period=2.5)
                # uid = reader.read_uid()  # Now handled above
                # ...existing code...
            elif state == STATE_PLAYING:
                # If music stopped and no other sound is playing, means story finished
                if not pygame.mixer.music.get_busy() and not pygame.mixer.get_busy():
                    logger.info("Playback finished, returning to IDLE state.")
                    led_manager.set_pattern('blink', period=0.3, duty=0.5, count=3)
                    state = STATE_IDLE
                    current_card_uid = None
            elif state == STATE_PAUSED:
                led_manager.set_pattern('breathing', period=2.5)
                # uid = reader.read_uid()  # Now handled above
                # ...existing code...
            time.sleep(0.05) # Main loop polling interval

        # Shutdown sequence
        logger.info("Shutting down...")
        if IS_RASPBERRY_PI:
            # Perform safe shutdown command
            # os.system("sudo shutdown now") # Make sure this user has sudo rights without password for shutdown
            logger.info("[SIMULATE] os.system('sudo shutdown now')") 
        
        # Cleanup HAL components
        if reader: reader.cleanup()
        if button: button.cleanup()
        if volume_ctrl: volume_ctrl.cleanup()
        if IS_RASPBERRY_PI:
            GPIO.cleanup() # Final GPIO cleanup
            logger.info("[HAL] GPIO.cleanup() called.")

        pygame.quit()
        logger.info("Pygame quit. Exiting application.")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Manual interruption: exiting program.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        logger.debug(f"{traceback.format_exc()}")
    finally:
        logger.info("Performing final cleanup...")
        stop_bgm() # Ensure BGM is stopped
        pygame.mixer.stop() # Ensure all sounds are stopped

        if reader: reader.cleanup()
        if button: button.cleanup()
        if volume_ctrl: volume_ctrl.cleanup()
        
        if IS_RASPBERRY_PI and 'GPIO' in locals(): # Check if GPIO was successfully imported
             GPIO.cleanup()
             logger.info("[HAL] GPIO.cleanup() called in finally.")
        logger.info("Application finished.")

def run_with_verification():
    """Run the application with initial verification"""
    logger.info("Starting Storellai-1 with verification checks")
    verify_audio_files()
    # Remove or comment out the test playback step:
    # test_audio_performance()
    main()

if __name__ == "__main__":
    # Simplified run for now, can add verification back later
    main()