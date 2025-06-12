from hardware.hal import MockUIDReader, MockButton
from utils.tts import text_to_speech
from utils.story_utils import load_card_stories, pick_story
from utils.bgm_utils import (
    get_bgm_file_for_tone, play_bgm_loop, stop_bgm,
    set_bgm_volume, fade_bgm_to,
    BGM_INTRO_VOLUME, BGM_NARRATION_VOLUME, BGM_OUTRO_VOLUME
)
import datetime
import sys
import random
import time
import re
import json
from pathlib import Path


def is_calm_time():
    now = datetime.datetime.now().time()
    start = datetime.time(20, 30)
    end = datetime.time(6, 30)
    result = start <= now or now < end
    print(f"[DEBUG] Ora attuale: {now.strftime('%H:%M:%S')} | Fascia calma? {result}")
    return result


def main():
    reader = MockUIDReader()
    button = MockButton()
    state = "idle"
    print(f"State: {state}")

    while True:
        try:
            if state == "idle":
                uid = reader.read_uid()
                card_data = load_card_stories(uid)
                if not card_data or not card_data.get("stories"):
                    print("Nessuna storia disponibile per questa card.")
                    state = "idle"
                    continue
                stories = card_data["stories"]
                if is_calm_time():
                    selected_story = pick_story(stories, tone="calm")
                else:
                    selected_story = pick_story(stories, exclude_tone="calm")
                print(f"Storia selezionata: {selected_story['title']} (tono: {selected_story['tone']})")
                # --- Start BGM ---
                tone = selected_story["tone"]
                bgm_path = Path(__file__).parent / "bgm" / f"{tone}_loop.mp3"
                print(f"Playing BGM: {bgm_path}")
                play_bgm_loop(bgm_path, volume=BGM_INTRO_VOLUME)  # start at intro volume
                time.sleep(0.5)                      # very short intro (adjust as needed)
                fade_bgm_to(BGM_NARRATION_VOLUME, duration=0.5)       # fade quickly to mid volume for narration
                state = "tts"
                print(f"State: {state}")

            if state == "tts":
                print(f"Leggo il titolo: {selected_story['title']}")
                text_to_speech(selected_story["title"])
                fade_bgm_to(0.4, duration=0.5)  # Lower BGM for narration
                print("Leggo il resto della storia...")
                sentences = split_story_into_sentences(selected_story["text"])
                for sentence in sentences:
                    text_to_speech(sentence)
                    time.sleep(0.2)  # short pause for natural effect
                state = "playing"
                print(f"State: {state}")

            if state == "playing":
                print("Playing story... (premi il pulsante per terminare)")
                button.wait_for_tap()
                print("Playback ended.")
                fade_bgm_to(BGM_OUTRO_VOLUME, duration=1.0)       # fade to outro volume
                time.sleep(1)                        # let outro play for a moment
                stop_bgm()
                break
        except KeyboardInterrupt:
            print("Interruzione manuale: esco dal programma.")
            stop_bgm()
            break
        except Exception as e:
            print(f"Errore inatteso: {e}")
            stop_bgm()
            state = "idle"


def pick_story(stories, tone=None, exclude_tone=None):
    if tone:
        filtered = [s for s in stories if tone.lower() in s.get("tone", "").lower()]
        print(f"Filtered stories for tone '{tone}': {[s['title'] for s in filtered]}")
        if filtered:
            return random.choice(filtered)
    if exclude_tone:
        filtered = [s for s in stories if exclude_tone.lower() not in s.get("tone", "").lower()]
        print(f"Filtered stories excluding tone '{exclude_tone}': {[s['title'] for s in filtered]}")
        if filtered:
            return random.choice(filtered)
    return random.choice(stories)


def split_story_into_sentences(text):
    # Splits text into sentences for Italian/English
    return re.split(r'(?<=[.!?]) +', text)


def load_card_stories(uid):
    base = Path(__file__).parent.resolve() / "stories"
    path = base / f"card_{uid}.json"
    if not path.exists():
        print(f"Nessuna storia trovata per la card {uid} ({path})")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


base = Path(__file__).parent.parent.resolve() / "stories"

if __name__ == "__main__":
    main()