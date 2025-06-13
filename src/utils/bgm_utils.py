import pygame
from pathlib import Path
import time

BGM_FOLDER = Path(__file__).parent / "bgm"

TONE_TO_BGM = {
    "calmo": "calmo_loop.mp3",
    "calm": "calmo_loop.mp3",
    "avventuroso": "avventuroso_loop.mp3",
    "divertente": "divertente_loop.mp3",
    "misterioso": "misterioso_loop.mp3",
    "tenero": "tenero_loop.mp3",
}

BGM_INTRO_VOLUME = 0.7
BGM_NARRATION_VOLUME = 0.10  # Was 0.15
BGM_OUTRO_VOLUME = 0.2

def get_bgm_file_for_tone(tone):
    """
    Return the BGM file path for a given story tone.
    """
    filename = TONE_TO_BGM.get(tone.lower(), "calmo_loop.mp3")
    return BGM_FOLDER / filename

def play_bgm_loop(bgm_path, volume=0.7):
    """
    Play a BGM file in a loop at the specified volume.
    """
    pygame.mixer.init()
    pygame.mixer.music.load(str(bgm_path))
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(-1)

def set_bgm_volume(volume):
    """
    Set the current BGM volume.
    """
    pygame.mixer.music.set_volume(volume)

def fade_bgm_to(target_volume, duration=1.0, steps=10):
    """
    Fade the BGM volume smoothly to the target value over the given duration.
    """
    current = pygame.mixer.music.get_volume()
    step = (target_volume - current) / steps
    for i in range(steps):
        pygame.mixer.music.set_volume(current + step * (i+1))
        time.sleep(duration / steps)

def stop_bgm():
    """
    Stop the currently playing BGM.
    """
    pygame.mixer.music.stop()

def start_bgm_for_story(tone):
    """
    Start BGM for a given story tone, with intro and fade to narration volume.
    """
    bgm_path = get_bgm_file_for_tone(tone)
    play_bgm_loop(bgm_path, volume=BGM_INTRO_VOLUME)
    time.sleep(0.5)
    fade_bgm_to(BGM_NARRATION_VOLUME, duration=0.5)

# start_bgm_for_story(selected_story["tone"])