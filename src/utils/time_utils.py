# time_utils.py
"""
Time-related utilities for Storyteller Box.
Handles time-based logic and story selection based on time of day.
"""

import time
import random
from config.app_config import CALM_TIME_START, CALM_TIME_END
from utils.story_utils import pick_story


def is_calm_time():
    """Check if current time is within calm period (20:30-06:30)"""
    now = time.localtime()
    hour, minute = now.tm_hour, now.tm_min
    now_minutes = hour * 60 + minute
    start = CALM_TIME_START[0] * 60 + CALM_TIME_START[1]  # 20:30 in minutes
    end = CALM_TIME_END[0] * 60 + CALM_TIME_END[1]        # 6:30 in minutes
    result = now_minutes >= start or now_minutes < end
    print(f"[DEBUG] Current time: {hour:02}:{minute:02} | Calm period? {result}")
    return result


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
