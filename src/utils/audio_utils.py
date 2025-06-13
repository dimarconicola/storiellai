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


def crossfade_bgm_to_narration(bgm_path, narration_path, tone):
    """Play BGM with narration using crossfade technique"""
    global master_volume_level
    logger.debug(f"Starting crossfade playback: {tone} with master_volume: {master_volume_level:.2f}")
    
    try:
        pygame.mixer.music.load(str(bgm_path))
        # BGM_INTRO_VOLUME is a factor (e.g. 1.0), scale by master_volume_level
        pygame.mixer.music.set_volume(BGM_INTRO_VOLUME * master_volume_level)
        pygame.mixer.music.play(-1)
        logger.debug(f"BGM started at volume {BGM_INTRO_VOLUME * master_volume_level:.2f}")
    except Exception as e:
        logger.error(f"Failed to play BGM: {e}")
        return
    
    time.sleep(1.5)
    try:
        narration = pygame.mixer.Sound(str(narration_path))
        narration.set_volume(master_volume_level)  # Set narration volume based on master
        logger.debug(f"Narration loaded: {narration_path.name}, volume: {master_volume_level:.2f}")
    except Exception as e:
        logger.error(f"Failed to load narration: {e}")
        stop_bgm()
        return
    
    # Fade BGM to its narration level, scaled by master_volume
    fade_bgm_to(BGM_NARRATION_VOLUME * master_volume_level, duration=1.0)
    logger.debug(f"BGM faded to {BGM_NARRATION_VOLUME * master_volume_level:.2f} for narration")
    time.sleep(0.3)
    
    try:
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
