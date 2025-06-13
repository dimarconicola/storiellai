# time_utils.py
"""
Time-related utilities for Storyteller Box.
Handles time-based logic and story selection based on time of day.
"""

import time
import random
import os
from config.app_config import CALM_TIME_START, CALM_TIME_END
from utils.story_utils import pick_story
from utils.audio_utils import stop_bgm
from hardware.hal import MCP3008, AnalogIn


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


# Constants for battery management
LOW_BATTERY_THRESHOLD = 3.3  # Voltage level for low battery warning
CRITICAL_BATTERY_THRESHOLD = 3.0  # Voltage level for critical battery shutdown

# Initialize MCP3008 ADC (assuming channel 0 is used for battery voltage)
mcp = MCP3008()
battery_channel = AnalogIn(mcp, 0)


def read_battery_voltage():
    """Read the battery voltage from the ADC."""
    voltage = battery_channel.voltage * 2  # Adjust for voltage divider
    print(f"[DEBUG] Battery voltage: {voltage:.2f}V")
    return voltage


# Function to handle battery management
def handle_battery_status(adc, led_manager=None):
    """
    Check battery status and handle low/critical levels with LED feedback.
    
    Args:
        adc: The ADC instance for reading battery voltage
        led_manager: Optional LedPatternManager to show battery status
    
    Returns:
        tuple: (voltage, percentage, status)
            voltage: Current battery voltage
            percentage: Battery level as percentage (0-100)
            status: String indicating status ('normal', 'low', 'critical')
    """
    # If no ADC provided or on mock hardware, simulate values
    if adc is None:
        # In simulation mode, alternate between normal and low battery
        import random
        voltage = random.choice([3.5, 3.3, 3.2])
    else:
        try:
            voltage = read_battery_voltage()
        except Exception as e:
            from utils.log_utils import logger
            logger.error(f"Failed to read battery voltage: {e}")
            voltage = 3.8  # Default to a safe value on error
    
    # Calculate battery percentage (approximate)
    # LiPo battery is ~3.7V nominal, ~4.2V full, ~3.0V empty
    percentage = max(0, min(100, (voltage - 3.0) / (4.2 - 3.0) * 100))
    
    status = 'normal'
    if voltage <= CRITICAL_BATTERY_THRESHOLD:
        status = 'critical'
        from utils.log_utils import logger
        logger.warning(f"Critical battery level ({voltage:.2f}V, {percentage:.0f}%)! Initiating shutdown...")
        
        # Show critical battery warning if LED manager available
        if led_manager:
            led_manager.set_pattern('sos', count=1, next_pattern='error')
            
        # Safe shutdown procedure
        stop_bgm()
        import pygame
        pygame.mixer.stop()
        
        # Delay before shutdown to allow warning to be seen
        time.sleep(2)
        
        if os.path.exists("/usr/bin/sudo"):
            # Safe shutdown on Raspberry Pi
            os.system("sudo shutdown now")
        else:
            # On development platforms, just log
            logger.info("[SIMULATE] sudo shutdown now")
            
    elif voltage <= LOW_BATTERY_THRESHOLD:
        status = 'low'
        from utils.log_utils import logger
        logger.warning(f"Low battery level ({voltage:.2f}V, {percentage:.0f}%)! Please recharge soon.")
        
        # Show low battery warning if LED manager available
        if led_manager:
            current_pattern = led_manager.pattern
            # Only show warning if not already showing an error pattern
            if current_pattern not in ['error', 'sos', 'attention']:
                led_manager.set_battery_warning(int(percentage))
    
    return voltage, percentage, status
