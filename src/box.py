import os
import random
import time
import traceback
from pathlib import Path
import pygame
import sys # For GPIO cleanup on exit

from hardware.hal import IS_RASPBERRY_PI, BUTTON_NO_EVENT, BUTTON_TAP, BUTTON_DOUBLE_TAP, BUTTON_LONG_PRESS

if IS_RASPBERRY_PI:
    from hardware.hal import RealUIDReader, RealButton, RealVolumeControl
    import RPi.GPIO as GPIO # For cleanup
else:
    from hardware.hal import MockUIDReader, MockButton, MockVolumeControl

from utils.story_utils import pick_story # Assuming this is confirmed offline-only
from utils.bgm_utils import (
    play_bgm_loop, stop_bgm, fade_bgm_to,
    BGM_INTRO_VOLUME, BGM_NARRATION_VOLUME, BGM_OUTRO_VOLUME
)
import json

# ============ CONSTANTS ============
AUDIO_FOLDER = Path(__file__).parent / "audio"
BGM_FOLDER = Path(__file__).parent / "bgm"
STORIES_FOLDER = Path(__file__).parent / "storiesoffline"

# Audio quality settings
AUDIO_FREQUENCY = 44100
AUDIO_BUFFER = 2048
AUDIO_CHANNELS = 2
MAX_AUDIO_CHANNELS = 8

# Software Volume Limits
MIN_SOFTWARE_VOLUME = 0.1
MAX_SOFTWARE_VOLUME = 0.9 # Max volume to prevent distortion, adjustable

# State machine states
STATE_IDLE = "idle"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused" # Added for pause functionality
STATE_SHUTTING_DOWN = "shutting_down"

# LED states / patterns (can be simple for now)
LED_OFF = False
LED_ON = True
# For pulsing, we'd need a separate update loop or thread for the LED
# For now, simple on/off based on player state.

# Audio cache to reduce loading times
BGM_CACHE = {}
NARRATION_CACHE = {}


# ============ JSON HANDLING ============
def load_card_stories(uid):
    """
    Load stories for a card from JSON file.
    
    Args:
        uid (str): Card UID
        
    Returns:
        dict or None: Card data if found and valid, None otherwise
    """
    path = STORIES_FOLDER / f"card_{uid}.json"
    print(f"[DEBUG] Looking for JSON file: {path}")
    
    if not path.exists():
        print(f"[ERROR] JSON file not found: {path}")
        return None
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"[INFO] Successfully loaded JSON for card {uid}")
            return data
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON format in {path}: {e}")
        print(f"[DEBUG] Error at line {e.lineno}, column {e.colno}: {e.msg}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to read {path}: {e}")
        return None

# ============ AUDIO ENGINE ============
def initialize_audio_engine():
    """Initialize the audio engine with optimal settings"""
    try:
        pygame.mixer.quit()  # Ensure clean state
        pygame.mixer.init(
            frequency=AUDIO_FREQUENCY,
            size=-16,  # 16-bit signed
            channels=AUDIO_CHANNELS,
            buffer=AUDIO_BUFFER
        )
        pygame.mixer.set_num_channels(MAX_AUDIO_CHANNELS)
        print("[INFO] Audio engine initialized successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to initialize audio engine: {e}")
        print(f"[DEBUG] {traceback.format_exc()}")
        return False

def set_system_volume(level, current_bgm_volume_factor=1.0):
    """Set master volume for Pygame, respecting software limits."""
    # Level is 0.0 to 1.0 from volume knob
    # Scale it to our desired min/max software range
    effective_volume = MIN_SOFTWARE_VOLUME + (level * (MAX_SOFTWARE_VOLUME - MIN_SOFTWARE_VOLUME))
    
    # Apply to BGM (music channel)
    # If BGM is playing, its perceived volume is also affected by BGM_NARRATION_VOLUME etc.
    # We need to scale the current BGM volume factor by the new master_volume_level
    # pygame.mixer.music.set_volume(effective_volume * current_bgm_volume_factor)
    # For now, let's assume current_bgm_volume_factor is handled by fade_bgm_to or initial play
    pygame.mixer.music.set_volume(effective_volume)


    # Apply to narration (sound channels) - this is harder as sounds are played on any free channel
    # For simplicity, we might need to iterate over active channels if Pygame allows,
    # or rely on setting volume when sounds are played.
    # A simpler approach: store the master volume and apply it when sounds are played.
    # This requires modifying play_narration_with_bgm.
    # For now, this function will primarily control BGM master level.
    # Individual sound objects can have their volume set via sound.set_volume(level) before playing.
    global master_volume_level
    master_volume_level = effective_volume # Store for use by narration
    
    print(f"[AUDIO] System volume set to {effective_volume:.2f} (raw knob: {level:.2f})")

master_volume_level = MAX_SOFTWARE_VOLUME # Initial master volume

def preload_bgm():
    """Preload background music into memory"""
    print("[DEBUG] Starting BGM preload...")
    bgm_loaded = 0
    
    for tone in ["calmo", "avventuroso", "divertente", "misterioso", "tenero"]:
        bgm_path = BGM_FOLDER / f"{tone}_loop.mp3"
        if bgm_path.exists():
            try:
                BGM_CACHE[tone] = pygame.mixer.Sound(str(bgm_path))
                bgm_loaded += 1
                print(f"[INFO] Preloaded BGM: {tone}")
            except Exception as e:
                print(f"[ERROR] Failed to preload BGM {tone}: {e}")
    
    print(f"[INFO] Preloaded {bgm_loaded}/5 BGM files")

def preload_narration(uid):
    """Preload narration files for a specific card"""
    print(f"[DEBUG] Preloading narration for card {uid}...")
    card_data = load_card_stories(uid)
    if not card_data or not card_data.get("stories"):
        print(f"[WARNING] No stories found for card {uid}, skipping narration preload")
        return
    
    stories_loaded = 0
    stories_failed = 0
    
    for story in card_data["stories"]:
        narration_path = Path(__file__).parent / story["audio"]
        if narration_path.exists():
            try:
                key = f"{uid}_{story['id']}"
                NARRATION_CACHE[key] = pygame.mixer.Sound(str(narration_path))
                stories_loaded += 1
                print(f"[INFO] Preloaded narration: {story['title']}")
            except Exception as e:
                stories_failed += 1
                print(f"[ERROR] Failed to preload narration {story['title']}: {e}")
    
    print(f"[INFO] Preloaded {stories_loaded} narrations ({stories_failed} failed)")

def crossfade_bgm_to_narration(bgm_path, narration_path, tone):
    global master_volume_level
    print(f"[DEBUG] Starting crossfade playback: {tone} with master_volume: {master_volume_level:.2f}")
    # ... (mixer init check) ...
    try:
        pygame.mixer.music.load(str(bgm_path))
        # BGM_INTRO_VOLUME is a factor (e.g. 1.0), scale by master_volume_level
        pygame.mixer.music.set_volume(BGM_INTRO_VOLUME * master_volume_level)
        pygame.mixer.music.play(-1)
        print(f"[DEBUG] BGM started at volume {BGM_INTRO_VOLUME * master_volume_level:.2f}")
    except Exception as e:
        print(f"[ERROR] Failed to play BGM: {e}")
        return
    time.sleep(1.5)
    try:
        narration = pygame.mixer.Sound(str(narration_path))
        narration.set_volume(master_volume_level) # Set narration volume based on master
        print(f"[DEBUG] Narration loaded: {narration_path.name}, volume: {master_volume_level:.2f}")
    except Exception as e:
        print(f"[ERROR] Failed to load narration: {e}")
        stop_bgm()
        return
    
    # Fade BGM to its narration level, scaled by master_volume
    fade_bgm_to(BGM_NARRATION_VOLUME * master_volume_level, duration=1.0)
    print(f"[DEBUG] BGM faded to {BGM_NARRATION_VOLUME * master_volume_level:.2f} for narration")
    time.sleep(0.3)
    
    try:
        narration_channel = narration.play()
        print("[INFO] Narration started")
        
        # Wait for narration to finish
        while narration_channel and narration_channel.get_busy():
            time.sleep(0.1)
        print("[INFO] Narration finished")
    except Exception as e:
        print(f"[ERROR] Narration playback error: {e}")
    
    # Raise BGM, scaled by master_volume
    fade_bgm_to(BGM_INTRO_VOLUME * 0.8 * master_volume_level, duration=1.5)
    print(f"[DEBUG] BGM raised after narration to {BGM_INTRO_VOLUME * 0.8 * master_volume_level:.2f}")
    
    # Let BGM play for a short outro period
    time.sleep(2.0)
    
    # Fade out completely
    fade_bgm_to(0.0, duration=1.5)
    time.sleep(1.5)
    stop_bgm()
    print("[DEBUG] Playback completed")

def play_narration_with_bgm(narration_path, tone):
    """
    Play narration with background music.
    
    Args:
        narration_path (Path): Path to narration file
        tone (str): Mood tone for selecting BGM
    """
    bgm_path = BGM_FOLDER / f"{tone}_loop.mp3"
    if not bgm_path.exists():
        print(f"[ERROR] BGM not found for tone '{tone}': {bgm_path}")
        return False
    
    crossfade_bgm_to_narration(bgm_path, narration_path, tone)
    return True

def stop_bgm():
    """Safely stop background music"""
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
            print("[DEBUG] Background music stopped")
        except Exception as e:
            print(f"[ERROR] Failed to stop BGM: {e}")
    else:
        print("[DEBUG] Mixer not initialized, skipping stop_bgm.")

# ============ TIME UTILITIES ============
def is_calm_time():
    """Check if current time is within calm period (20:30-06:30)"""
    now = time.localtime()
    hour, minute = now.tm_hour, now.tm_min
    now_minutes = hour * 60 + minute
    start = 20 * 60 + 30   # 20:30 in minutes
    end = 6 * 60 + 30      # 6:30 in minutes
    result = now_minutes >= start or now_minutes < end
    print(f"[DEBUG] Current time: {hour:02}:{minute:02} | Calm period? {result}")
    return result

# ============ STORY SELECTION ============
def select_story_for_time(stories, is_calm):
    """
    Select a story appropriate for the current time of day.
    
    Args:
        stories (list): List of stories to choose from
        is_calm (bool): True if during calm hours, False otherwise
        
    Returns:
        dict: Selected story
    """
    print(f"[DEBUG] Selecting story, calm time: {is_calm}")
    
    if is_calm:
        try:
            selected_story = pick_story(stories, tone="calmo")
            print(f"[DEBUG] Selected calm story: {selected_story['title']}")
            return selected_story
        except Exception as e:
            print(f"[WARNING] Failed to select calm story: {e}")
    
    try:
        # Filter out calm stories during active hours
        non_calm_stories = [s for s in stories if s.get("tone", "").lower() != "calmo"]
        
        if non_calm_stories:
            selected_story = random.choice(non_calm_stories)
            print(f"[DEBUG] Selected non-calm story: {selected_story['title']}")
            return selected_story
    except Exception as e:
        print(f"[WARNING] Failed to filter non-calm stories: {e}")
    
    # Fallback to any random story if filtering fails
    selected_story = random.choice(stories)
    print(f"[DEBUG] Selected fallback story: {selected_story['title']}")
    return selected_story

# ============ VERIFICATION ============
def verify_audio_files():
    """Verify all audio files exist and are valid"""
    print("[INFO] Starting audio file verification...")
    
    # Check BGM files
    bgm_folder = Path(__file__).parent / "bgm"
    missing_bgm = []
    for tone in ["calmo", "avventuroso", "divertente", "misterioso", "tenero"]:
        bgm_path = bgm_folder / f"{tone}_loop.mp3"
        if not bgm_path.exists():
            missing_bgm.append(tone)
    
    if missing_bgm:
        print(f"[WARNING] Missing BGM files for: {', '.join(missing_bgm)}")
    else:
        print("[INFO] All required BGM files found")
    
    # Check narration files
    print("[INFO] Checking narration files...")
    stories_folder = Path(__file__).parent / "storiesoffline"
    invalid_audio = []
    stories_checked = 0
    
    for json_file in stories_folder.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                card_data = json.load(f)
            
            if "stories" in card_data:
                for story in card_data["stories"]:
                    stories_checked += 1
                    if "audio" in story:
                        audio_path = Path(__file__).parent / story["audio"]
                        if not audio_path.exists():
                            invalid_audio.append(f"{story['title']} ({audio_path})")
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON format in {json_file}")
        except Exception as e:
            print(f"[ERROR] Failed to process {json_file}: {e}")
    
    if invalid_audio:
        print(f"[WARNING] Missing audio files: {len(invalid_audio)}/{stories_checked} stories")
        for item in invalid_audio:
            print(f"  - {item}")
    else:
        print(f"[INFO] All {stories_checked} narration audio files found")

def test_audio_performance():
    """Test audio engine performance"""
    print("[INFO] Testing audio performance...")
    
    if not pygame.mixer.get_init():
        initialize_audio_engine()
    
    # Test BGM playback
    bgm_path = BGM_FOLDER / "calmo_loop.mp3"
    if bgm_path.exists():
        start_time = time.time()
        pygame.mixer.music.load(str(bgm_path))
        load_time = time.time() - start_time
        
        start_time = time.time()
        pygame.mixer.music.play()
        time.sleep(0.1)
        pygame.mixer.music.stop()
        play_time = time.time() - start_time
        
        print(f"[INFO] BGM load time: {load_time:.4f}s, play startup: {play_time:.4f}s")
    else:
        print("[WARNING] Cannot test BGM performance, file not found")
    
    # Test Sound object performance
    test_paths = []
    for subdir in AUDIO_FOLDER.iterdir():
        if subdir.is_dir():
            for file in subdir.glob("*.mp3"):
                test_paths.append(file)
                break
    
    if test_paths:
        start_time = time.time()
        sound = pygame.mixer.Sound(str(test_paths[0]))
        load_time = time.time() - start_time
        
        start_time = time.time()
        channel = sound.play()
        time.sleep(0.1)
        channel.stop()
        play_time = time.time() - start_time
        
        print(f"[INFO] Sound load time: {load_time:.4f}s, play startup: {play_time:.4f}s")
    else:
        print("[WARNING] Cannot test Sound performance, no files found")

# ============ MAIN APPLICATION ============
def main():
    """Main application loop"""
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
            # MCP3008 SPI pins might be shared with NFC or use different CS
            # For simplicity, assuming MCP3008 uses its own CS or is on a different SPI bus if necessary
            # If sharing SPI0, ensure CS pins are distinct and managed.
            # ADC_SPI_PORT = 0
            # ADC_SPI_CS_PIN = 1 # CE1 for SPI0, if NFC uses CE0

            reader = RealUIDReader(spi_port=NFC_SPI_PORT, spi_cs_pin=NFC_SPI_CS_PIN, irq_pin=NFC_IRQ_PIN, rst_pin=NFC_RST_PIN)
            button = RealButton(button_pin=BUTTON_PIN, led_pin=LED_PIN)
            volume_ctrl = RealVolumeControl(adc_channel=ADC_CHANNEL_VOLUME) # Add SPI params if needed
        else:
            reader = MockUIDReader()
            button = MockButton()
            volume_ctrl = MockVolumeControl()

        state = STATE_IDLE
        button.set_led(LED_ON) # LED on when idle, ready
        print(f"[INFO] System started, state: {state}")
        print(f"[INFO] Running on {'Raspberry Pi' if IS_RASPBERRY_PI else 'Mock Hardware'}")

        last_volume_check_time = time.monotonic()
        
        # Initial volume setting
        master_volume_level = volume_ctrl.get_volume() 
        set_system_volume(master_volume_level)


        while state != STATE_SHUTTING_DOWN:
            # Volume control check (periodically)
            if time.monotonic() - last_volume_check_time > 0.2: # Check 5 times a second
                new_volume = volume_ctrl.get_volume()
                if abs(new_volume - master_volume_level) > 0.01: # Update if changed significantly
                    # If playing, we need to know the current BGM volume factor
                    # This is tricky as fade_bgm_to changes it.
                    # For now, set_system_volume will update a global master_volume_level
                    # and crossfade/play functions will use it.
                    set_system_volume(new_volume)
                last_volume_check_time = time.monotonic()

            # Button event handling
            button_event = button.get_event()

            if button_event == BUTTON_TAP:
                if state == STATE_PLAYING:
                    pygame.mixer.music.pause()
                    # pygame.mixer.pause() # Pauses all sound channels
                    button.set_led(LED_OFF) # Or a pulsing LED for PAUSED
                    state = STATE_PAUSED
                    print("[INFO] Playback PAUSED")
                elif state == STATE_PAUSED:
                    pygame.mixer.music.unpause()
                    # pygame.mixer.unpause()
                    button.set_led(LED_ON)
                    state = STATE_PLAYING
                    print("[INFO] Playback RESUMED")
                # Optional: if idle and tapped, replay last story? For now, no action.

            elif button_event == BUTTON_DOUBLE_TAP:
                if current_card_uid and state in [STATE_PLAYING, STATE_PAUSED, STATE_IDLE]:
                    print("[INFO] Double tap: Reselecting story for current card.")
                    if pygame.mixer.music.get_busy() or pygame.mixer.get_busy(): # if something is playing/paused
                        stop_bgm() # Stop current playback fully
                        # Ensure all sound channels are stopped too if narration was separate
                        pygame.mixer.stop()


                    # Force re-selection and play from IDLE-like state for this card
                    # This simulates as if the card was just placed again for a new story
                    card_data = load_card_stories(current_card_uid) # Reload data
                    if card_data and card_data.get("stories"):
                        stories = card_data["stories"]
                        selected_story = select_story_for_time(stories, is_calm_time())
                        current_narration_path = Path(__file__).parent / selected_story["audio"]
                        current_bgm_tone = selected_story.get("tone", "calmo")
                        
                        if current_narration_path.exists():
                            print(f"[INFO] Playing new story: {selected_story['title']}")
                            play_narration_with_bgm(current_narration_path, current_bgm_tone)
                            button.set_led(LED_ON)
                            state = STATE_PLAYING
                        else:
                            print(f"[ERROR] Audio for new story not found: {current_narration_path}")
                            button.set_led(LED_ON) # Back to ready state
                            state = STATE_IDLE
                    else:
                        print("[WARN] No stories for current card on double tap, returning to idle.")
                        button.set_led(LED_ON)
                        state = STATE_IDLE


            elif button_event == BUTTON_LONG_PRESS:
                print("[INFO] Long press: Initiating shutdown.")
                button.set_led(LED_OFF) # LED off during shutdown
                stop_bgm()
                pygame.mixer.stop()
                # Add any other cleanup here
                state = STATE_SHUTTING_DOWN
                continue # Skip to end of while loop for shutdown sequence

            # Main state machine logic
            if state == STATE_IDLE:
                button.set_led(LED_ON) # Ready indicator
                # print("[DEBUG] Waiting for card...") # Too noisy
                uid = reader.read_uid()
                if uid:
                    print(f"[INFO] Card detected: {uid}")
                    current_card_uid = uid
                    # preload_narration(uid) # Optional: preload if not done globally or if memory is an issue
                    
                    card_data = load_card_stories(uid)
                    if not card_data or not card_data.get("stories"):
                        print(f"[ERROR] No stories for card {uid}")
                        current_card_uid = None # Reset if card is invalid
                        continue
                    
                    current_story_data = card_data["stories"]
                    selected_story = select_story_for_time(current_story_data, is_calm_time())
                    print(f"[INFO] Selected story: {selected_story['title']} (tone: {selected_story['tone']})")
                    
                    current_narration_path = Path(__file__).parent / selected_story["audio"]
                    current_bgm_tone = selected_story.get("tone", "calmo")

                    if not current_narration_path.exists():
                        print(f"[ERROR] Audio file not found: {current_narration_path}")
                        current_card_uid = None # Reset
                        continue
                        
                    print(f"[INFO] Transitioning to PLAYING state")
                    play_narration_with_bgm(current_narration_path, current_bgm_tone)
                    button.set_led(LED_ON) # LED solid while playing
                    state = STATE_PLAYING
            
            elif state == STATE_PLAYING:
                # If music stopped and no other sound is playing, means story finished
                if not pygame.mixer.music.get_busy() and not pygame.mixer.get_busy():
                    print("[INFO] Playback finished, returning to IDLE state.")
                    button.set_led(LED_ON) # Ready indicator
                    state = STATE_IDLE
                    current_card_uid = None # Ready for a new card entirely
            
            elif state == STATE_PAUSED:
                # Handled by button events or new card scan
                # Check for new card while paused
                uid = reader.read_uid() # Non-blocking if possible, or with short timeout
                if uid and uid != current_card_uid: # New card placed
                    print(f"[INFO] New card {uid} detected while paused. Stopping current and processing new.")
                    stop_bgm()
                    pygame.mixer.stop()
                    current_card_uid = uid # Process this new card in next IDLE iteration
                    state = STATE_IDLE # Go to IDLE to process the new card
                    button.set_led(LED_ON)
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