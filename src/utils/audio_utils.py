"""
Audio utilities for the Storyteller Box.
Handles audio engine initialization, volume control, preloading, and playback orchestration.
"""

import pygame
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging

from config.app_config import (
    AUDIO_FREQUENCY, AUDIO_BUFFER, AUDIO_CHANNELS, MAX_AUDIO_CHANNELS,
    MIN_SOFTWARE_VOLUME, MAX_SOFTWARE_VOLUME, BGM_FOLDER, AUDIO_FOLDER, STORIES_FOLDER
)
from utils.bgm_utils import (
    fade_bgm_to, stop_bgm,
    BGM_INTRO_VOLUME, BGM_NARRATION_VOLUME, BGM_OUTRO_VOLUME
)
from utils.log_utils import logger

# Audio cache to reduce loading times
BGM_CACHE: Dict[str, pygame.mixer.Sound] = {}
NARRATION_CACHE: Dict[str, pygame.mixer.Sound] = {}

# Master volume level for the system
master_volume_level: float = MAX_SOFTWARE_VOLUME
master_volume_level = MAX_SOFTWARE_VOLUME
BGM_CACHE = {}
NARRATION_CACHE = {}


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
        logger.info("Audio engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize audio engine: {e}")
        logger.debug(f"{traceback.format_exc()}")
        return False


def set_system_volume(level, current_bgm_volume_factor=1.0):
    """Set master volume for Pygame, respecting software limits."""
    global master_volume_level
    
    # Level is 0.0 to 1.0 from volume knob
    # Scale it to our desired min/max software range
    effective_volume = MIN_SOFTWARE_VOLUME + (level * (MAX_SOFTWARE_VOLUME - MIN_SOFTWARE_VOLUME))
    
    # Apply to BGM (music channel)
    pygame.mixer.music.set_volume(effective_volume)
    
    # Store the master volume for use by narration
    master_volume_level = effective_volume
    
    logger.info(f"System volume set to {effective_volume:.2f} (raw knob: {level:.2f})")


def preload_bgm():
    """Preload background music into memory"""
    logger.debug("Starting BGM preload...")
    bgm_loaded = 0
    
    for tone in ["calmo", "avventuroso", "divertente", "misterioso", "tenero"]:
        bgm_path = BGM_FOLDER / f"{tone}_loop.mp3"
        if bgm_path.exists():
            try:
                BGM_CACHE[tone] = pygame.mixer.Sound(str(bgm_path))
                bgm_loaded += 1
                logger.info(f"Preloaded BGM: {tone}")
            except Exception as e:
                logger.error(f"Failed to preload BGM {tone}: {e}")
    
    logger.info(f"Preloaded {bgm_loaded}/5 BGM files")


def preload_narration(uid):
    """Preload narration files for a specific card"""
    from utils.data_utils import load_card_stories
    
    logger.debug(f"Preloading narration for card {uid}...")
    card_data = load_card_stories(uid)
    if not card_data or not card_data.get("stories"):
        logger.warning(f"No stories found for card {uid}, skipping narration preload")
        return
    
    stories_loaded = 0
    stories_failed = 0
    
    for story in card_data["stories"]:
        narration_path = Path(__file__).parent.parent / story["audio"]
        if narration_path.exists():
            try:
                key = f"{uid}_{story['id']}"
                NARRATION_CACHE[key] = pygame.mixer.Sound(str(narration_path))
                stories_loaded += 1
                logger.info(f"Preloaded narration: {story['title']}")
            except Exception as e:
                stories_failed += 1
                logger.error(f"Failed to preload narration {story['title']}: {e}")
    
    logger.info(f"Preloaded {stories_loaded} narrations ({stories_failed} failed)")


def preload_narration_async(uid):
    """
    Preload narration files for a specific card asynchronously.
    This function is designed to be called in a separate thread.
    
    Args:
        uid (str): Card UID to preload
    """
    try:
        logger.debug(f"[ASYNC] Preloading narration for card {uid}...")
        from utils.data_utils import load_card_stories
        
        card_data = load_card_stories(uid)
        if not card_data or not card_data.get("stories"):
            logger.debug(f"[ASYNC] No stories found for card {uid}, skipping narration preload")
            return
        
        stories_loaded = 0
        stories_failed = 0
        
        for story in card_data["stories"]:
            if "audio" in story:
                audio_path = Path(__file__).parent.parent / story["audio"]
                if audio_path.exists():
                    # Only preload if not already in cache
                    if str(audio_path) not in NARRATION_CACHE:
                        try:
                            # Use low-level pygame methods for better control
                            NARRATION_CACHE[str(audio_path)] = pygame.mixer.Sound(str(audio_path))
                            stories_loaded += 1
                            logger.debug(f"[ASYNC] Preloaded narration: {story['title']}")
                        except Exception as e:
                            stories_failed += 1
                            logger.error(f"[ASYNC] Failed to preload narration {audio_path}: {e}")
        
        if stories_loaded > 0:
            logger.info(f"[ASYNC] Preloaded {stories_loaded} narration files for card {uid} ({stories_failed} failed)")
        else:
            logger.warning(f"[ASYNC] No narration files preloaded for card {uid}")
    
    except Exception as e:
        logger.error(f"[ASYNC] Error in async narration preload for {uid}: {e}")
        logger.debug(traceback.format_exc())


def crossfade_bgm_to_narration(bgm_path, narration_path, tone):
    """Play BGM with narration using crossfade technique"""
    global master_volume_level
    logger.debug(f"Starting crossfade playback: {tone} with master_volume: {master_volume_level:.2f}")
    
    # Use cached BGM if available for faster response
    if tone in BGM_CACHE:
        logger.debug(f"Using cached BGM for tone: {tone}")
        pygame.mixer.music.load(str(bgm_path))
    else:
        try:
            pygame.mixer.music.load(str(bgm_path))
            # Try to add to cache for future use if not already there
            if tone not in BGM_CACHE:
                try:
                    BGM_CACHE[tone] = pygame.mixer.Sound(str(bgm_path))
                    logger.debug(f"Added BGM to cache: {tone}")
                except:
                    pass  # Non-critical if caching fails
        except Exception as e:
            logger.error(f"Failed to play BGM: {e}")
            return
    
    # Start BGM at intro volume
    pygame.mixer.music.set_volume(BGM_INTRO_VOLUME * master_volume_level)
    pygame.mixer.music.play(-1)
    logger.debug(f"BGM started at volume {BGM_INTRO_VOLUME * master_volume_level:.2f}")
    
    # Short intro period (reduced from 1.5s to 1.0s for responsiveness)
    time.sleep(1.0)
    
    # Check cache for narration sound
    narration_path_str = str(narration_path)
    narration = None
    
    if narration_path_str in NARRATION_CACHE:
        logger.debug(f"Using cached narration: {narration_path.name}")
        narration = NARRATION_CACHE[narration_path_str]
    else:
        try:
            narration = pygame.mixer.Sound(str(narration_path))
            # Add to cache for future use
            NARRATION_CACHE[narration_path_str] = narration
            logger.debug(f"Added narration to cache: {narration_path.name}")
        except Exception as e:
            logger.error(f"Failed to load narration: {e}")
            stop_bgm()
            return
    
    # Fade BGM to its narration level, scaled by master_volume
    fade_bgm_to(BGM_NARRATION_VOLUME * master_volume_level, duration=0.75)  # Faster fade
    logger.debug(f"BGM faded to {BGM_NARRATION_VOLUME * master_volume_level:.2f} for narration")
    time.sleep(0.2)  # Reduced delay
    
    try:
        narration.set_volume(master_volume_level)  # Set narration volume based on master
        narration_channel = narration.play()
        logger.info("Narration started")
        
        # Wait for narration to finish
        while narration_channel and narration_channel.get_busy():
            time.sleep(0.1)
        logger.info("Narration finished")
    except Exception as e:
        logger.error(f"Narration playback error: {e}")
    
    # Raise BGM, scaled by master_volume
    fade_bgm_to(BGM_INTRO_VOLUME * 0.8 * master_volume_level, duration=1.5)
    logger.debug(f"BGM raised after narration to {BGM_INTRO_VOLUME * 0.8 * master_volume_level:.2f}")
    
    # Let BGM play for a short outro period
    time.sleep(2.0)
    
    # Fade out completely
    fade_bgm_to(0.0, duration=1.5)
    time.sleep(1.5)
    stop_bgm()
    logger.debug("Playback completed")


def play_narration_with_bgm(narration_path, tone):
    """
    Play narration with background music.
    
    Args:
        narration_path (Path): Path to narration file
        tone (str): Mood tone for selecting BGM
    """
    bgm_path = BGM_FOLDER / f"{tone}_loop.mp3"
    if not bgm_path.exists():
        logger.error(f"BGM not found for tone '{tone}': {bgm_path}")
        return False
    
    crossfade_bgm_to_narration(bgm_path, narration_path, tone)
    return True


def test_audio_performance():
    """Test audio engine performance"""
    logger.info("Testing audio performance...")
    
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
        
        logger.info(f"BGM load time: {load_time:.4f}s, play startup: {play_time:.4f}s")
    else:
        logger.warning("Cannot test BGM performance, file not found")
    
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
        
        logger.info(f"Sound load time: {load_time:.4f}s, play startup: {play_time:.4f}s")
    else:
        logger.warning("Cannot test Sound performance, no files found")

def play_error_sound():
    """Play a default error sound if available."""
    error_path = AUDIO_FOLDER / "error.mp3"
    if error_path.exists():
        try:
            sound = pygame.mixer.Sound(str(error_path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played error sound.")
            # Wait briefly to let the error sound play
            pygame.time.wait(700)
        except Exception as e:
            logger.error(f"Failed to play error sound: {e}")
    else:
        logger.error("Error sound file missing: error.mp3")

def play_card_valid_sound():
    """Play a sound for valid card recognition."""
    path = AUDIO_FOLDER / "card_valid.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played card valid sound.")
            pygame.time.wait(400)
        except Exception as e:
            logger.error(f"Failed to play card valid sound: {e}")
    else:
        logger.warning("Card valid sound file missing: card_valid.mp3")

def play_card_invalid_sound():
    """Play a sound for invalid card recognition."""
    path = AUDIO_FOLDER / "card_invalid.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played card invalid sound.")
            pygame.time.wait(400)
        except Exception as e:
            logger.error(f"Failed to play card invalid sound: {e}")
    else:
        logger.warning("Card invalid sound file missing: card_invalid.mp3")

def play_transition_sound():
    """Play a short transition sound between stories."""
    path = AUDIO_FOLDER / "transition.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played transition sound.")
            pygame.time.wait(350)
        except Exception as e:
            logger.error(f"Failed to play transition sound: {e}")
    else:
        logger.warning("Transition sound file missing: transition.mp3")

def play_boot_sound():
    """Play a sound at system boot."""
    path = AUDIO_FOLDER / "boot.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played boot sound.")
            pygame.time.wait(600)
        except Exception as e:
            logger.error(f"Failed to play boot sound: {e}")
    else:
        logger.warning("Boot sound file missing: boot.mp3")

def play_shutdown_sound():
    """Play a sound at system shutdown."""
    path = AUDIO_FOLDER / "shutdown.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played shutdown sound.")
            pygame.time.wait(600)
        except Exception as e:
            logger.error(f"Failed to play shutdown sound: {e}")
    else:
        logger.warning("Shutdown sound file missing: shutdown.mp3")

def play_pause_sound():
    """Play a sound when pausing playback."""
    path = AUDIO_FOLDER / "pause.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played pause sound.")
            pygame.time.wait(350)
        except Exception as e:
            logger.error(f"Failed to play pause sound: {e}")
    else:
        logger.warning("Pause sound file missing: pause.mp3")

def play_resume_sound():
    """Play a sound when resuming playback."""
    path = AUDIO_FOLDER / "resume.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played resume sound.")
            pygame.time.wait(350)
        except Exception as e:
            logger.error(f"Failed to play resume sound: {e}")
    else:
        logger.warning("Resume sound file missing: resume.mp3")

def play_success_sound():
    """Play a sound for successful operations."""
    path = AUDIO_FOLDER / "success.mp3"
    if path.exists():
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(1.0)
            sound.play()
            logger.info("Played success sound.")
            pygame.time.wait(400)
        except Exception as e:
            logger.error(f"Failed to play success sound: {e}")
    else:
        logger.warning("Success sound file missing: success.mp3")
