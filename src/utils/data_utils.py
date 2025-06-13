# data_utils.py
"""
Data and file management utilities for Storyteller Box.
Handles JSON loading, file verification, and data validation.
"""

import json
from pathlib import Path
from config.app_config import STORIES_FOLDER, BGM_FOLDER, AUDIO_FOLDER, AVAILABLE_TONES
import logging
from utils.log_utils import logger


def load_card_stories(uid):
    """
    Load stories for a card from JSON file.
    
    Args:
        uid (str): Card UID
        
    Returns:
        dict or None: Card data if found and valid, None otherwise
    """
    path = STORIES_FOLDER / f"card_{uid}.json"
    logger.debug(f"Looking for JSON file: {path}")
    
    if not path.exists():
        logger.error(f"JSON file not found: {path}")
        return None
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Successfully loaded JSON for card {uid}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {path}: {e}")
        logger.debug(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")
        return None
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def verify_audio_files():
    """Verify all audio files exist and are valid"""
    logger.info("Starting audio file verification...")
    
    # Check BGM files
    bgm_folder = BGM_FOLDER
    missing_bgm = []
    for tone in ["calmo", "avventuroso", "divertente", "misterioso", "tenero"]:
        bgm_path = bgm_folder / f"{tone}_loop.mp3"
        if not bgm_path.exists():
            missing_bgm.append(tone)
    
    if missing_bgm:
        logger.warning(f"Missing BGM files for: {', '.join(missing_bgm)}")
    else:
        logger.info("All required BGM files found")
    
    # Check narration files
    logger.info("Checking narration files...")
    stories_folder = STORIES_FOLDER
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
                        audio_path = stories_folder.parent / story["audio"]
                        if not audio_path.exists():
                            invalid_audio.append(f"{story['title']} ({audio_path})")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in {json_file}")
        except Exception as e:
            logger.error(f"Failed to process {json_file}: {e}")
    
    if invalid_audio:
        logger.warning(f"Missing audio files: {len(invalid_audio)}/{stories_checked} stories")
        for item in invalid_audio:
            logger.info(f"  - {item}")
    else:
        logger.info(f"All {stories_checked} narration audio files found")
