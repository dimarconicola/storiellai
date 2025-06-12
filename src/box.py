import os
import random
import time
import traceback  # Added for better error logging
from pathlib import Path
import pygame
from hardware.hal import MockUIDReader, MockButton
from utils.story_utils import pick_story
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
AUDIO_FREQUENCY = 44100  # Hz (CD quality)
AUDIO_BUFFER = 2048      # Larger for more stability, smaller for lower latency
AUDIO_CHANNELS = 2       # Stereo
MAX_AUDIO_CHANNELS = 8   # Maximum number of simultaneous sounds

# State machine states
STATE_IDLE = "idle"
STATE_PLAYING = "playing"

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
    """
    Play background music with narration using smooth crossfading.
    
    Args:
        bgm_path (Path): Path to BGM file
        narration_path (Path): Path to narration file
        tone (str): Mood tone for the narration
    """
    print(f"[DEBUG] Starting crossfade playback: {tone}")
    
    if not pygame.mixer.get_init():
        print("[WARNING] Mixer not initialized, initializing now")
        initialize_audio_engine()
    
    # Start BGM at full volume
    try:
        pygame.mixer.music.load(str(bgm_path))
        pygame.mixer.music.set_volume(BGM_INTRO_VOLUME)
        pygame.mixer.music.play(-1)  # Loop indefinitely
        print(f"[DEBUG] BGM started at volume {BGM_INTRO_VOLUME}")
    except Exception as e:
        print(f"[ERROR] Failed to play BGM: {e}")
        return
    
    # Let the BGM play for a moment to establish the mood
    time.sleep(1.5)
    
    # Prepare narration
    try:
        narration = pygame.mixer.Sound(str(narration_path))
        print(f"[DEBUG] Narration loaded: {narration_path.name}")
    except Exception as e:
        print(f"[ERROR] Failed to load narration: {e}")
        stop_bgm()
        return
    
    # Gradually lower BGM volume before narration starts
    fade_bgm_to(BGM_NARRATION_VOLUME, duration=1.0)
    print(f"[DEBUG] BGM faded to {BGM_NARRATION_VOLUME} for narration")
    time.sleep(0.3)  # Short pause for effect
    
    # Play narration
    try:
        narration_channel = narration.play()
        print("[INFO] Narration started")
        
        # Wait for narration to finish
        while narration_channel and narration_channel.get_busy():
            time.sleep(0.1)
        print("[INFO] Narration finished")
    except Exception as e:
        print(f"[ERROR] Narration playback error: {e}")
    
    # Gently raise BGM volume after narration
    fade_bgm_to(BGM_INTRO_VOLUME * 0.8, duration=1.5)
    print("[DEBUG] BGM raised after narration")
    
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
    # Initialize audio engine
    if not initialize_audio_engine():
        print("[CRITICAL] Failed to initialize audio. Exiting.")
        return
    
    # Preload BGM for all tones
    preload_bgm()
    
    reader = MockUIDReader()
    button = MockButton()
    state = STATE_IDLE
    print(f"[INFO] System started, state: {state}")

    while True:
        try:
            if state == STATE_IDLE:
                print("[DEBUG] Waiting for card...")
                uid = reader.read_uid()
                print(f"[INFO] Card detected: {uid}")
                
                # Preload narration for this card
                preload_narration(uid)
                
                # Load and validate card data
                card_data = load_card_stories(uid)
                if not card_data:
                    print(f"[ERROR] Failed to load data for card {uid}")
                    continue
                    
                if not card_data.get("stories"):
                    print(f"[ERROR] No stories found in card data for {uid}")
                    continue
                
                # Select appropriate story based on time
                stories = card_data["stories"]
                try:
                    selected_story = select_story_for_time(stories, is_calm_time())
                    print(f"[INFO] Selected story: {selected_story['title']} (tone: {selected_story['tone']})")
                except Exception as e:
                    print(f"[ERROR] Failed to select story: {e}")
                    print(f"[DEBUG] {traceback.format_exc()}")
                    continue
                
                # Validate audio file
                tone = selected_story.get("tone", "calmo")  # Default to calmo if missing
                if not "audio" in selected_story:
                    print(f"[ERROR] No audio path in selected story {selected_story['id']}")
                    continue
                    
                narration_path = Path(__file__).parent / selected_story["audio"]
                if not narration_path.exists():
                    print(f"[ERROR] Audio file not found: {narration_path}")
                    continue
                    
                print(f"[INFO] Transitioning to PLAYING state")
                state = STATE_PLAYING
                print(f"[INFO] Playing story: {selected_story['title']} with {tone} BGM")
                
                # Play the narration with background music
                success = play_narration_with_bgm(narration_path, tone)
                if not success:
                    print("[ERROR] Failed to play narration with BGM")
                    state = STATE_IDLE
                    continue

            elif state == STATE_PLAYING:
                print("[DEBUG] In PLAYING state, waiting for button press...")
                button.wait_for_tap()
                print("[INFO] Button pressed, stopping playback")
                fade_bgm_to(BGM_OUTRO_VOLUME, duration=1.0)
                time.sleep(1)
                stop_bgm()
                print("[INFO] Transitioning to IDLE state")
                state = STATE_IDLE

        except KeyboardInterrupt:
            print("[INFO] Manual interruption: exiting program.")
            stop_bgm()
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            print(f"[DEBUG] {traceback.format_exc()}")
            stop_bgm()
            print("[INFO] Resetting to IDLE state due to error")
            state = STATE_IDLE

def run_with_verification():
    """Run the application with initial verification"""
    print("[INFO] Starting Storellai-1 with verification checks")
    verify_audio_files()
    # Remove or comment out the test playback step:
    # test_audio_performance()
    main()

if __name__ == "__main__":
    run_with_verification()