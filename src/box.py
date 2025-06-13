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
    play_narration_with_bgm, test_audio_performance
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
        print("[CRITICAL] Failed to initialize audio. Exiting.")
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

        state = STATE_IDLE
        button.set_led(LED_ON) # LED on when idle, ready
        print(f"[INFO] System started, state: {state}")
        print(f"[INFO] Running on {'Raspberry Pi' if IS_RASPBERRY_PI else 'Mock Hardware'}")

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
                    print("[INFO] Playback PAUSED")
                elif state == STATE_PAUSED:
                    pygame.mixer.music.unpause()
                    led_manager.set_pattern('solid', state=True)
                    state = STATE_PLAYING
                    print("[INFO] Playback RESUMED")

            elif button_event == BUTTON_DOUBLE_TAP:
                if current_card_uid and state in [STATE_PLAYING, STATE_PAUSED, STATE_IDLE]:
                    print("[INFO] Double tap: Reselecting story for current card.")
                    stop_bgm()
                    pygame.mixer.stop()
                    card_data = load_card_stories(current_card_uid)
                    if card_data and card_data.get("stories"):
                        stories = card_data["stories"]
                        selected_story = select_story_for_time(stories, is_calm_time())
                        current_narration_path = Path(__file__).parent / selected_story["audio"]
                        current_bgm_tone = selected_story.get("tone", "calmo")
                        if current_narration_path.exists():
                            print(f"[INFO] Playing new story: {selected_story['title']}")
                            play_narration_with_bgm(current_narration_path, current_bgm_tone)
                            led_manager.set_pattern('solid', state=True)
                            state = STATE_PLAYING
                        else:
                            print(f"[ERROR] Audio for new story not found: {current_narration_path}")
                            led_manager.set_pattern('solid', state=True)
                            state = STATE_IDLE
                    else:
                        print("[WARN] No stories for current card on double tap, returning to idle.")
                        led_manager.set_pattern('solid', state=True)
                        state = STATE_IDLE

            elif button_event == BUTTON_LONG_PRESS:
                print("[INFO] Long press: Initiating shutdown.")
                led_manager.set_pattern('blink', period=0.2, duty=0.5, count=10)
                stop_bgm()
                pygame.mixer.stop()
                state = STATE_SHUTTING_DOWN
                continue

            # Main state machine logic
            if state == STATE_IDLE:
                led_manager.set_pattern('breathing', period=2.5)
                uid = reader.read_uid()
                if uid:
                    print(f"[INFO] Card detected: {uid}")
                    current_card_uid = uid
                    card_data = load_card_stories(uid)
                    if not card_data or not card_data.get("stories"):
                        print(f"[ERROR] No stories for card {uid}")
                        current_card_uid = None
                        continue
                    
                    current_story_data = card_data["stories"]
                    selected_story = select_story_for_time(current_story_data, is_calm_time())
                    print(f"[INFO] Selected story: {selected_story['title']} (tone: {selected_story['tone']})")
                    
                    current_narration_path = Path(__file__).parent / selected_story["audio"]
                    current_bgm_tone = selected_story.get("tone", "calmo")

                    if not current_narration_path.exists():
                        print(f"[ERROR] Audio file not found: {current_narration_path}")
                        current_card_uid = None
                        continue
                        
                    print(f"[INFO] Transitioning to PLAYING state")
                    play_narration_with_bgm(current_narration_path, current_bgm_tone)
                    led_manager.set_pattern('solid', state=True)
                    state = STATE_PLAYING
            
            elif state == STATE_PLAYING:
                # If music stopped and no other sound is playing, means story finished
                if not pygame.mixer.music.get_busy() and not pygame.mixer.get_busy():
                    print("[INFO] Playback finished, returning to IDLE state.")
                    led_manager.set_pattern('blink', period=0.3, duty=0.5, count=3)
                    state = STATE_IDLE
                    current_card_uid = None
            
            elif state == STATE_PAUSED:
                led_manager.set_pattern('breathing', period=2.5)
                uid = reader.read_uid() # Non-blocking if possible, or with short timeout
                if uid and uid != current_card_uid: # New card placed
                    print(f"[INFO] New card {uid} detected while paused. Stopping current and processing new.")
                    stop_bgm()
                    pygame.mixer.stop()
                    current_card_uid = uid # Process this new card in next IDLE iteration
                    state = STATE_IDLE # Go to IDLE to process the new card
                    led_manager.set_pattern('breathing', period=2.5)
                    continue # Restart loop to handle new card

            time.sleep(0.05) # Main loop polling interval

        # Shutdown sequence
        print("[INFO] Shutting down...")
        if IS_RASPBERRY_PI:
            # Perform safe shutdown command
            # os.system("sudo shutdown now") # Make sure this user has sudo rights without password for shutdown
            print("[SIMULATE] os.system('sudo shutdown now')") 
        
        # Cleanup HAL components
        if reader: reader.cleanup()
        if button: button.cleanup()
        if volume_ctrl: volume_ctrl.cleanup()
        if IS_RASPBERRY_PI:
            GPIO.cleanup() # Final GPIO cleanup
            print("[HAL] GPIO.cleanup() called.")

        pygame.quit()
        print("[INFO] Pygame quit. Exiting application.")
        sys.exit(0)

    except KeyboardInterrupt:
        print("[INFO] Manual interruption: exiting program.")
    except Exception as e:
        print(f"[ERROR] Unexpected error in main loop: {e}")
        print(f"[DEBUG] {traceback.format_exc()}")
    finally:
        print("[INFO] Performing final cleanup...")
        stop_bgm() # Ensure BGM is stopped
        pygame.mixer.stop() # Ensure all sounds are stopped

        if reader: reader.cleanup()
        if button: button.cleanup()
        if volume_ctrl: volume_ctrl.cleanup()
        
        if IS_RASPBERRY_PI and 'GPIO' in locals(): # Check if GPIO was successfully imported
             GPIO.cleanup()
             print("[HAL] GPIO.cleanup() called in finally.")
        pygame.quit()
        print("[INFO] Application finished.")

def run_with_verification():
    """Run the application with initial verification"""
    print("[INFO] Starting Storellai-1 with verification checks")
    verify_audio_files()
    # Remove or comment out the test playback step:
    # test_audio_performance()
    main()

if __name__ == "__main__":
    # Simplified run for now, can add verification back later
    main()