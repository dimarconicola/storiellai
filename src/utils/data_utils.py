# data_utils.py
"""
Data and file management utilities for Storyteller Box.
Handles JSON loading, file verification, and data validation.
"""

import json
from pathlib import Path
from config.app_config import STORIES_FOLDER, BGM_FOLDER, AUDIO_FOLDER, AVAILABLE_TONES


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


def verify_audio_files():
    """Verify all audio files exist and are valid"""
    print("[INFO] Starting audio file verification...")
    
    # Check BGM files
    bgm_folder = BGM_FOLDER
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
            print(f"[ERROR] Invalid JSON format in {json_file}")
        except Exception as e:
            print(f"[ERROR] Failed to process {json_file}: {e}")
    
    if invalid_audio:
        print(f"[WARNING] Missing audio files: {len(invalid_audio)}/{stories_checked} stories")
        for item in invalid_audio:
            print(f"  - {item}")
    else:
        print(f"[INFO] All {stories_checked} narration audio files found")
