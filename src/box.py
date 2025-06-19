#!/usr/bin/env python3
"""
Main application logic for the Storyteller Box (Offline Edition).
Handles NFC card reading, story selection, audio playback, button events, volume control, and LED feedback patterns.

- NFC cards trigger story playback (pre-recorded audio, offline only)
- Button supports tap (pause/play), double-tap (new story), long-press (shutdown)
- Volume knob via MCP3008 ADC
- LED feedback (solid, breathing, blink) via PWM
- Hardware abstraction via hal.py for easy testing/mocking
- Keyboard controls: 'p' (pause/resume), 'n' (new story), 'q'/ESC (quit)
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

# Try to import AnalogIn from adafruit_mcp3xxx, fallback to hardware.hal
try:
    from adafruit_mcp3xxx.analog_in import AnalogIn
except ImportError:
    from hardware.hal import AnalogIn  # Use the mock if the real one is missing

# Import from utility modules
from utils.audio_utils import (
    initialize_audio_engine, set_system_volume, preload_bgm, 
    play_narration_with_bgm, test_audio_performance, play_error_sound,
    preload_narration_async,  # New async preloading function
    play_card_valid_sound, play_card_invalid_sound, play_transition_sound,
    play_boot_sound, play_shutdown_sound, play_pause_sound, play_resume_sound, play_success_sound
)
from utils.data_utils import load_card_stories, verify_audio_files, preload_card_data  # Added preload_card_data
from utils.time_utils import is_calm_time, select_story_for_time
from utils.led_utils import LedPatternManager
from utils.bgm_utils import stop_bgm

# Import configuration
from config.app_config import (
    STATE_IDLE, STATE_PLAYING, STATE_PAUSED, STATE_SHUTTING_DOWN,
    LED_OFF, LED_ON, VOLUME_CHECK_INTERVAL, MAIN_LOOP_INTERVAL,
    IDLE_SHUTDOWN_TIMEOUT_MINUTES # Added IDLE_SHUTDOWN_TIMEOUT_MINUTES
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
    # Defer Pygame display initialization
    # pygame.init() # Moved lower
    # pygame.display.set_mode((200, 100)) # Moved lower
    # pygame.display.set_caption("Storyteller Control") # Moved lower

    global master_volume_level
    
    # Fast audio engine initialization
    start_time = time.time()
    if not initialize_audio_engine(): # This already calls pygame.mixer.init()
        logger.critical("Failed to initialize audio. Exiting.")
        if IS_RASPBERRY_PI and 'button' in locals() and button: # Check if button was initialized
            led_manager = LedPatternManager(button)
            led_manager.set_pattern('blink', period=0.15, duty=0.5)
        elif not IS_RASPBERRY_PI and 'button' in locals() and button: # Mock environment
            # In a mock setup, we might not have a physical LED, but can log
            logger.info("Mock LED: Blink pattern (0.15s period, 0.5 duty)")
        play_error_sound()
        return
    logger.info(f"Audio engine initialization took {(time.time() - start_time)*1000:.1f}ms")
    
    # Hardware initialization (extracted to a function)
    reader, button, volume_ctrl, adc = initialize_hardware()
    
    if reader is None or button is None or volume_ctrl is None:
        logger.critical("Critical hardware components failed to initialize")
        if IS_RASPBERRY_PI and button: # Check if button was initialized before trying to use led_manager
            led_manager = LedPatternManager(button)
            led_manager.set_pattern('blink', period=0.1, duty=0.5)
        elif not IS_RASPBERRY_PI and button: # Mock environment
             logger.info("Mock LED: Blink pattern (0.1s period, 0.5 duty)")
        play_error_sound() # Ensure error sound is played
        return # Exit if hardware fails
    
    led_manager = LedPatternManager(button)
    
    preload_start = time.time()
    preload_bgm() # This can take time
    logger.info(f"BGM preloading took {(time.time() - preload_start)*1000:.1f}ms")
    
    preload_thread = threading.Thread(target=background_preload, daemon=True)
    preload_thread.start()
    
    current_card_uid = None
    current_story_data = None
    current_narration_path = None
    current_bgm_tone = None
    
    state = STATE_IDLE
    last_activity_time = time.time() # Initialize last activity time for idle shutdown
    last_story_played_time = time.time() # Initialize time for idle shutdown
    button.set_led(LED_ON)
    logger.info(f"System started, state: {state}")
    logger.info(f"Running on {'Raspberry Pi' if IS_RASPBERRY_PI else 'Mock Hardware'}")
    
    last_volume_check_time = time.time()
    last_battery_check_time = time.time()
    last_loop_time = time.time()
    
    target_loop_time = 0.02
    
    master_volume_level = volume_ctrl.get_volume() 
    set_system_volume(master_volume_level)
    
    # NOW initialize pygame.display and set up the window
    pygame.init() # Initialize all pygame modules if not done by mixer
    pygame.display.set_mode((200, 100))
    pygame.display.set_caption("Storyteller Control")
    pygame.mouse.set_visible(True) # Ensure mouse is visible

    # System booting up: show boot sequence
    led_manager.set_boot_sequence()
    play_boot_sound() # This function has its own wait, we'll address it next
    # Wait for boot sound to finish and give a slight pause
    while pygame.mixer.get_busy(): 
        pygame.event.pump() # Process events to keep window responsive
        time.sleep(0.05) # Shorter sleep
    time.sleep(0.2)  # Shorter additional pause

    total_startup_time = time.time() - start_time
    logger.info(f"Total startup time: {total_startup_time*1000:.1f}ms")

    try:
        while state != STATE_SHUTTING_DOWN:
            loop_start_time_debug = time.time() # For debugging loop duration
            led_manager.update()

            # --- Keyboard Input Handling ---
            for event in pygame.event.get(): # This also pumps events
                if event.type == pygame.QUIT:  # Window close event
                    logger.info("Pygame window closed, initiating shutdown.")
                    state = STATE_SHUTTING_DOWN
                    break
                if event.type == pygame.KEYDOWN:
                    logger.debug(f"Key pressed: {pygame.key.name(event.key)} (code: {event.key})") # DEBUG PRINT
                    if event.key == pygame.K_p: # Toggle Pause/Resume
                        if state == STATE_PLAYING:
                            pygame.mixer.music.pause()
                            play_pause_sound()
                            # Wait for sound to finish while pumping events
                            sound_start_time = time.time()
                            while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0): # Max 2s wait
                                pygame.event.pump()
                                time.sleep(0.02)
                            led_manager.set_pattern('breathing', period=2.5)
                            state = STATE_PAUSED
                            logger.info("Playback PAUSED (Keyboard)")
                        elif state == STATE_PAUSED:
                            pygame.mixer.music.unpause()
                            play_resume_sound()
                            sound_start_time = time.time()
                            while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0): # Max 2s wait
                                pygame.event.pump()
                                time.sleep(0.02)
                            led_manager.set_pattern('solid', state=True)
                            state = STATE_PLAYING
                            logger.info("Playback RESUMED (Keyboard)")
                    elif event.key == pygame.K_n: # New Story
                        if current_card_uid and state in [STATE_PLAYING, STATE_PAUSED, STATE_IDLE]:
                            logger.info("Keyboard 'n': Reselecting story for current card.")
                            stop_bgm()
                            pygame.mixer.stop() 
                            led_manager.set_loading_pattern()
                            play_transition_sound()
                            sound_start_time = time.time()
                            while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0): 
                                pygame.event.pump()
                                time.sleep(0.02)
                            time.sleep(0.3) # Keep this specific pause after transition

                            card_data = load_card_stories(current_card_uid) 
                            if card_data and card_data.get("stories"):
                                stories = card_data["stories"]
                                selected_story = select_story_for_time(stories, is_calm_time())
                                new_narration_path = Path(__file__).parent / selected_story["audio"]
                                new_bgm_tone = selected_story.get("tone", "calmo")
                                if new_narration_path.exists():
                                    logger.info(f"Playing new story (Keyboard): {selected_story['title']}")
                                    current_narration_path = new_narration_path 
                                    current_bgm_tone = new_bgm_tone 
                                    play_narration_with_bgm(current_narration_path, current_bgm_tone)
                                    # play_success_sound() # Success sound is part of play_narration_with_bgm or should be called carefully
                                    # Ensure narration has started before trying to play success or waiting
                                    # This part needs careful sequencing if success sound is desired here
                                    led_manager.set_success_pattern(next_pattern='solid') # Set pattern immediately
                                    state = STATE_PLAYING
                                else:
                                    logger.error(f"Audio for new story not found (Keyboard): {new_narration_path}")
                                    led_manager.set_error_pattern(count=2)
                                    play_error_sound()
                                    state = STATE_IDLE 
                            else:
                                logger.warning("No stories for current card on 'n' key, returning to idle.")
                                led_manager.set_pattern('solid', state=True) 
                                play_error_sound() 
                                state = STATE_IDLE
                        else:
                            logger.info("Keyboard 'n': No active card or invalid state for new story.")
                            play_error_sound() 

                    elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        logger.info("Quit key pressed, initiating shutdown.")
                        state = STATE_SHUTTING_DOWN
                        break
            
            if state == STATE_SHUTTING_DOWN: 
                continue
            
            current_time = time.time()
            
            if current_time - last_volume_check_time > VOLUME_CHECK_INTERVAL: # Use constant
                new_volume = volume_ctrl.get_volume()
                if abs(new_volume - master_volume_level) > 0.01: # master_volume_level is already scaled
                    set_system_volume(new_volume) # Pass raw knob value
                last_volume_check_time = current_time
            
            if IS_RASPBERRY_PI and current_time - last_battery_check_time > 10 : # Only on RPi
                handle_battery_status(adc, led_manager) 
                last_battery_check_time = current_time
            
            button_event = button.get_event()
            
            if button_event == BUTTON_TAP:
                if state == STATE_PLAYING:
                    pygame.mixer.music.pause()
                    play_pause_sound()
                    sound_start_time = time.time()
                    while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0): 
                        pygame.event.pump()
                        time.sleep(0.02)
                    led_manager.set_pattern('breathing', period=2.5)
                    state = STATE_PAUSED
                    logger.info("Playback PAUSED")
                elif state == STATE_PAUSED:
                    pygame.mixer.music.unpause()
                    play_resume_sound()
                    sound_start_time = time.time()
                    while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0): 
                        pygame.event.pump()
                        time.sleep(0.02)
                    led_manager.set_pattern('solid', state=True)
                    state = STATE_PLAYING
                    logger.info("Playback RESUMED")

            elif button_event == BUTTON_DOUBLE_TAP:
                if current_card_uid and state in [STATE_PLAYING, STATE_PAUSED, STATE_IDLE]:
                    logger.info("Double tap: Reselecting story for current card.")
                    stop_bgm()
                    pygame.mixer.stop()
                    led_manager.set_loading_pattern()
                    play_transition_sound()
                    sound_start_time = time.time()
                    while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0):
                        pygame.event.pump()
                        time.sleep(0.02)
                    time.sleep(0.3) 
                    card_data = load_card_stories(current_card_uid)
                    if card_data and card_data.get("stories"):
                        stories = card_data["stories"]
                        selected_story = select_story_for_time(stories, is_calm_time())
                        current_narration_path = Path(__file__).parent / selected_story["audio"]
                        current_bgm_tone = selected_story.get("tone", "calmo")
                        if current_narration_path.exists():
                            logger.info(f"Playing new story: {selected_story['title']}")
                            play_narration_with_bgm(current_narration_path, current_bgm_tone)
                            # play_success_sound() # Part of play_narration_with_bgm or needs careful sequencing
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
                        play_error_sound()
                        state = STATE_IDLE

            elif button_event == BUTTON_LONG_PRESS:
                logger.info("Long press: Initiating shutdown.")
                led_manager.set_shutdown_sequence()
                play_shutdown_sound()
                sound_start_time = time.time()
                while pygame.mixer.get_busy() and (time.time() - sound_start_time < 3.0): # Longer wait for shutdown sound
                    pygame.event.pump()
                    time.sleep(0.02)
                stop_bgm()
                pygame.mixer.stop()
                state = STATE_SHUTTING_DOWN
                continue

            uid = reader.read_uid()
            if uid and uid != current_card_uid:
                logger.info(f"New card {uid} detected. Interrupting current story (if any) and starting new.")
                last_activity_time = time.time() # Reset activity timer on new card
                last_story_played_time = time.time() # Reset story played timer
                stop_bgm()
                pygame.mixer.stop()
                current_card_uid = uid
                led_manager.set_attention_pattern(count=1)
                play_transition_sound()
                sound_start_time = time.time()
                while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0):
                    pygame.event.pump()
                    time.sleep(0.02)
                time.sleep(0.3)

                if uid in ["000000", "000001", "000002", "000003", "000004"]: # Example UIDs
                    next_uid_int = int(uid) + 1
                    if next_uid_int <= 999999: # Ensure it doesn't exceed 6 digits
                         next_uid = f"{next_uid_int:06d}"
                         threading.Thread(
                             target=preload_narration_async, 
                             args=(next_uid,), 
                             daemon=True
                         ).start()
                card_data = load_card_stories(uid)
                if not card_data:
                    logger.error(f"Invalid or missing JSON for card {uid}")
                    led_manager.set_card_sequence(is_valid=False)
                    play_card_invalid_sound()
                    sound_start_time = time.time()
                    while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0):
                        pygame.event.pump()
                        time.sleep(0.02)
                    time.sleep(0.3)
                    play_error_sound()
                    current_card_uid = None
                    state = STATE_IDLE
                    continue
                if not card_data.get("stories"):
                    logger.warning(f"Empty card: no stories for card {uid}")
                    led_manager.set_pattern('colorshift', levels=[50, 0, 50, 0], duration=0.2, count=3, next_pattern='breathing')
                    play_card_invalid_sound()
                    sound_start_time = time.time()
                    while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0):
                        pygame.event.pump()
                        time.sleep(0.02)
                    time.sleep(0.3)
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
                    play_card_invalid_sound()
                    sound_start_time = time.time()
                    while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0):
                        pygame.event.pump()
                        time.sleep(0.02)
                    time.sleep(0.3)
                    play_error_sound()
                    current_card_uid = None
                    state = STATE_IDLE
                    continue
                logger.info(f"Transitioning to PLAYING state")
                play_card_valid_sound()
                sound_start_time = time.time()
                while pygame.mixer.get_busy() and (time.time() - sound_start_time < 2.0):
                    pygame.event.pump()
                    time.sleep(0.02)
                time.sleep(0.3)
                play_narration_with_bgm(current_narration_path, current_bgm_tone)
                led_manager.set_card_sequence(is_valid=True)
                state = STATE_PLAYING
                last_story_played_time = time.time() # Update when a new story starts

            if state == STATE_IDLE:
                led_manager.set_pattern('breathing', period=2.5)
                # Check for idle timeout based on no new story played
                if IDLE_SHUTDOWN_TIMEOUT_MINUTES > 0: # Only if timeout is set
                    if (time.time() - last_story_played_time) > (IDLE_SHUTDOWN_TIMEOUT_MINUTES * 60):
                        logger.info(f"No new story played for {IDLE_SHUTDOWN_TIMEOUT_MINUTES} minutes. Initiating shutdown.")
                        led_manager.set_shutdown_sequence()
                        play_shutdown_sound()
                        sound_start_time = time.time()
                        while pygame.mixer.get_busy() and (time.time() - sound_start_time < 3.0):
                            pygame.event.pump()
                            time.sleep(0.02)
                        stop_bgm()
                        pygame.mixer.stop()
                        state = STATE_SHUTTING_DOWN
                        continue # Skip to next loop iteration to process shutdown

            elif state == STATE_PLAYING:
                if not pygame.mixer.music.get_busy() and not pygame.mixer.get_busy(): # Check both music and sound channels
                    logger.info("Playback finished, returning to IDLE state.")
                    led_manager.set_pattern('fadeout', duration=1.0, next_pattern='breathing')
                    state = STATE_IDLE
                    current_card_uid = None 
            elif state == STATE_PAUSED:
                led_manager.set_pattern('breathing', period=2.5)
                # Paused state does not reset last_story_played_time, so it will eventually shut down
                # if no new story is initiated.
                # If you want pause to keep it alive indefinitely (or reset the timer), 
                # you would update last_story_played_time here.
                # For now, the behavior is: if paused for longer than IDLE_SHUTDOWN_TIMEOUT_MINUTES 
                # without a new story being played, it will shut down. This seems reasonable.
            
            loop_time = time.time() - loop_start_time_debug
            sleep_time = max(0.001, MAIN_LOOP_INTERVAL - loop_time) # Use MAIN_LOOP_INTERVAL from config
            time.sleep(sleep_time)
            
            pygame.display.flip() 
            
            if time.time() - last_loop_time > 5.0: 
                # Calculate actual average loop time over the 5s period
                num_loops_in_5_sec = 5.0 / MAIN_LOOP_INTERVAL # Expected number of loops
                actual_avg_loop_time_ms = ((time.time() - last_loop_time) / num_loops_in_5_sec) * 1000 if num_loops_in_5_sec > 0 else 0
                logger.debug(f"Main loop avg time over last 5s: {actual_avg_loop_time_ms:.2f}ms (target: {MAIN_LOOP_INTERVAL*1000:.1f}ms)")
                last_loop_time = time.time()
        
        logger.info("Shutting down...")
        if IS_RASPBERRY_PI:
            logger.info("[SIMULATE] os.system('sudo shutdown now')") 
        
        if reader: reader.cleanup()
        if button: button.cleanup()
        if volume_ctrl: volume_ctrl.cleanup()
        if IS_RASPBERRY_PI and 'GPIO' in locals() and GPIO: # Ensure GPIO was imported and available
            GPIO.cleanup()
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
        stop_bgm() 
        pygame.mixer.stop() 

        if reader: reader.cleanup()
        if button: button.cleanup()
        if volume_ctrl: volume_ctrl.cleanup()
        
        if IS_RASPBERRY_PI and 'GPIO' in locals() and GPIO: 
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