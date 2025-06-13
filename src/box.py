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
import sys
import threading  # Added for asynchronous loading
from utils.log_utils import logger

from hardware.hal import IS_RASPBERRY_PI, BUTTON_NO_EVENT, BUTTON_TAP, BUTTON_DOUBLE_TAP, BUTTON_LONG_PRESS
from utils.time_utils import handle_battery_status
from adafruit_mcp3xxx.analog_in import AnalogIn

# Import from utility modules
from utils.audio_utils import (
    initialize_audio_engine, set_system_volume, preload_bgm, 
    play_narration_with_bgm, test_audio_performance, play_error_sound,
    preload_narration_async  # New async preloading function
)
from utils.data_utils import load_card_stories, verify_audio_files, preload_card_data  # Added preload_card_data
from utils.time_utils import is_calm_time, select_story_for_time
from utils.led_utils import LedPatternManager
from utils.bgm_utils import stop_bgm

# Import configuration
from config.app_config import (
    STATE_IDLE, STATE_PLAYING, STATE_PAUSED, STATE_SHUTTING_DOWN,
    LED_OFF, LED_ON
)

# Hardware components
if IS_RASPBERRY_PI:
    from hardware.hal import UIDReader, Button, VolumeControl
    import RPi.GPIO as GPIO  # For cleanup
else:
    from hardware.hal import UIDReader, Button, VolumeControl

# Global flag for background loading
background_loading_active = False

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
    
    # Fast audio engine initialization
    start_time = time.time()
    if not initialize_audio_engine():
        logger.critical("Failed to initialize audio. Exiting.")
        if button:
            led_manager = LedPatternManager(button)
            led_manager.set_pattern('blink', period=0.15, duty=0.5)
        play_error_sound()
        return
    logger.info(f"Audio engine initialization took {(time.time() - start_time)*1000:.1f}ms")
    
    # Hardware initialization (extracted to a function)
    reader, button, volume_ctrl, adc = initialize_hardware()
    
    # Check if critical hardware components initialized properly
    if reader is None or button is None or volume_ctrl is None:
        logger.critical("Critical hardware components failed to initialize")
        if button:
            led_manager = LedPatternManager(button)
            led_manager.set_pattern('blink', period=0.1, duty=0.5)
        play_error_sound()
        return
    
    # Set up LED manager
    led_manager = LedPatternManager(button)
    
    # Start preloading BGM in main thread (critical for early response)
    preload_start = time.time()
    preload_bgm()
    logger.info(f"BGM preloading took {(time.time() - preload_start)*1000:.1f}ms")
    
    # Start background preloading thread for narrations
    preload_thread = threading.Thread(target=background_preload, daemon=True)
    preload_thread.start()
    
    current_card_uid = None
    current_story_data = None
    current_narration_path = None
    current_bgm_tone = None
    
    state = STATE_IDLE
    button.set_led(LED_ON)  # LED on when idle, ready
    logger.info(f"System started, state: {state}")
    logger.info(f"Running on {'Raspberry Pi' if IS_RASPBERRY_PI else 'Mock Hardware'}")
    
    # Timing variables
    last_volume_check_time = time.time()
    last_battery_check_time = time.time()
    last_loop_time = time.time()
    
    # Dynamic sleep time for main loop
    target_loop_time = 0.02  # Target 50Hz for button responsiveness
    
    # Initial volume setting
    master_volume_level = volume_ctrl.get_volume() 
    set_system_volume(master_volume_level)
    
    # System booting up: show boot sequence
    led_manager.set_boot_sequence()
    time.sleep(1.0)  # Allow boot sequence to start
    
    # Calculate total startup time
    total_startup_time = time.time() - start_time
    logger.info(f"Total startup time: {total_startup_time*1000:.1f}ms")

    try:
        while state != STATE_SHUTTING_DOWN:
            loop_start = time.time()
            led_manager.update()
            
            # Dynamic timing for responsive interaction
            current_time = time.time()
            
            # Volume control check (check every 200ms)
            if current_time - last_volume_check_time > 0.2:
                new_volume = volume_ctrl.get_volume()
                if abs(new_volume - master_volume_level) > 0.01:
                    set_system_volume(new_volume)
                last_volume_check_time = current_time
            
            # Battery status check (every 10 seconds)
            if current_time - last_battery_check_time > 10:
                handle_battery_status(adc, led_manager)
                last_battery_check_time = current_time
            
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
                    
                    # Show loading pattern while selecting a new story
                    led_manager.set_loading_pattern()
                    
                    card_data = load_card_stories(current_card_uid)
                    if card_data and card_data.get("stories"):
                        stories = card_data["stories"]
                        selected_story = select_story_for_time(stories, is_calm_time())
                        current_narration_path = Path(__file__).parent / selected_story["audio"]
                        current_bgm_tone = selected_story.get("tone", "calmo")
                        if current_narration_path.exists():
                            logger.info(f"Playing new story: {selected_story['title']}")
                            play_narration_with_bgm(current_narration_path, current_bgm_tone)
                            led_manager.set_success_pattern(next_pattern='solid')
                            state = STATE_PLAYING
                        else:
                            logger.error(f"Audio for new story not found: {current_narration_path}")
                            led_manager.set_error_pattern(count=2)
                            play_error_sound()
                            state = STATE_IDLE
                    else:
                        logger.warning("No stories for current card on double tap, returning to idle.")
                        led_manager.set_pattern('solid', state=True)
                        state = STATE_IDLE

            elif button_event == BUTTON_LONG_PRESS:
                logger.info("Long press: Initiating shutdown.")
                led_manager.set_shutdown_sequence()
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
                
                # Show loading pattern while processing card
                led_manager.set_attention_pattern(count=1)
                
                # Preload next card in background
                if uid in ["000000", "000001", "000002", "000003", "000004"]:
                    next_uid = f"{int(uid) + 1:06d}"
                    threading.Thread(
                        target=preload_narration_async, 
                        args=(next_uid,), 
                        daemon=True
                    ).start()
                
                # Card data loading - this could be from cache now
                card_data = load_card_stories(uid)
                if not card_data:
                    logger.error(f"Invalid or missing JSON for card {uid}")
                    led_manager.set_card_sequence(is_valid=False)
                    play_error_sound()
                    current_card_uid = None
                    state = STATE_IDLE
                    continue
                if not card_data.get("stories"):
                    logger.warning(f"Empty card: no stories for card {uid}")
                    led_manager.set_pattern('colorshift', levels=[50, 0, 50, 0], duration=0.2, count=3, next_pattern='breathing')
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
                    led_manager.set_error_pattern(count=2)
                    play_error_sound()
                    current_card_uid = None
                    state = STATE_IDLE
                    continue
                logger.info(f"Transitioning to PLAYING state")
                play_narration_with_bgm(current_narration_path, current_bgm_tone)
                led_manager.set_card_sequence(is_valid=True)
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
                    led_manager.set_pattern('fadeout', duration=1.0, next_pattern='breathing')
                    state = STATE_IDLE
                    current_card_uid = None
            elif state == STATE_PAUSED:
                led_manager.set_pattern('breathing', period=2.5)
                # uid = reader.read_uid()  # Now handled above
                # ...existing code...
            # Dynamic sleep calculation for consistent loop timing
            loop_time = time.time() - loop_start
            sleep_time = max(0.001, target_loop_time - loop_time)  # Ensure at least 1ms sleep
            time.sleep(sleep_time)
            
            # Monitor loop performance
            if time.time() - last_loop_time > 5.0:  # Log every 5 seconds
                avg_loop = (time.time() - last_loop_time) / (1.0 / target_loop_time * 5.0)
                logger.debug(f"Main loop avg time: {avg_loop*1000:.2f}ms (target: {target_loop_time*1000:.1f}ms)")
                last_loop_time = time.time()
        
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
    # test_audio_performance()  # Removed performance test to speed up startup
    main()

def initialize_hardware():
    """Initialize hardware components with appropriate error handling"""
    reader = None
    button = None
    volume_ctrl = None
    adc = None
    
    try:
        if IS_RASPBERRY_PI:
            # GPIO pins from app_config
            from config.app_config import (
                NFC_SPI_PORT, NFC_SPI_CS_PIN, NFC_IRQ_PIN, NFC_RST_PIN,
                BUTTON_PIN, LED_PIN, ADC_CHANNEL_VOLUME
            )
            reader = UIDReader(spi_port=NFC_SPI_PORT, spi_cs_pin=NFC_SPI_CS_PIN, irq_pin=NFC_IRQ_PIN, rst_pin=NFC_RST_PIN)
            button = Button(button_pin=BUTTON_PIN, led_pin=LED_PIN)
            volume_ctrl = VolumeControl(adc_channel=ADC_CHANNEL_VOLUME)
            adc = AnalogIn()  # Initialize MCP3008 ADC
        else:
            reader = UIDReader()
            button = Button()
            volume_ctrl = VolumeControl()

        logger.info("Hardware initialization successful")
        return reader, button, volume_ctrl, adc
        
    except Exception as e:
        logger.error(f"Hardware initialization error: {e}")
        logger.debug(traceback.format_exc())
        # Return what we have - main() will check for None values
        return reader, button, volume_ctrl, adc

def background_preload():
    """Preload assets in background thread"""
    global background_loading_active
    try:
        background_loading_active = True
        logger.info("Starting background preloading...")
        
        # Preload common card data
        preload_card_data()
        
        # Preload narration for first few cards (adjust number as needed)
        for uid in ["000000", "000001", "000002"]:
            preload_narration_async(uid)
            
        logger.info("Background preloading completed")
    except Exception as e:
        logger.error(f"Background preloading error: {e}")
    finally:
        background_loading_active = False

def handle_error(led_manager, error_type="general", message=None):
    """
    Handle different types of errors with appropriate LED feedback and logging.
    
    Args:
        led_manager: LedPatternManager instance
        error_type: Type of error ("card", "audio", "system", "network", "battery")
        message: Optional error message to log
    """
    if message:
        logger.error(message)
    
    # Play error sound as immediate feedback
    play_error_sound()
    
    # Different LED patterns for different error types
    if error_type == "card":
        # Card read error - pulsing red pattern
        led_manager.set_pattern('colorshift', levels=[100, 0, 100, 0], duration=0.2, count=3, next_pattern='breathing')
    elif error_type == "audio":
        # Audio error - error pattern
        led_manager.set_error_pattern(count=2)
    elif error_type == "system":
        # System error - SOS pattern
        led_manager.set_sos(count=1, next_pattern='breathing')
    elif error_type == "network":
        # Network connectivity error - slow pulse
        led_manager.set_pattern('pulse', count=3, next_pattern='breathing')
    elif error_type == "battery":
        # Battery error - custom pattern based on severity
        level = message if isinstance(message, int) else 15
        led_manager.set_battery_warning(level)
    else:
        # General error - attention pattern
        led_manager.set_attention_pattern(count=2, next_pattern='breathing')
    
    # Wait for pattern to start
    time.sleep(0.2)

if __name__ == "__main__":
    # Skip verification during normal operation for faster startup
    # To run with verification: python box.py --verify
    import sys
    if "--verify" in sys.argv:
        run_with_verification()
    else:
        main()