"""
Story selection utilities for Storyteller Box.
Provides logic to pick a story from a list, optionally filtered by tone or other criteria.
"""

import json
import random
from pathlib import Path

def load_card_stories(uid):
    base = Path.cwd() / "src" / "storiesoffline"  # Corrected path
    print(f"[DEBUG] Listing files in: {base}")
    print(f"[DEBUG] Files: {list(base.glob('*.json'))}")
    path = base / f"card_{uid}.json"
    print(f"[DEBUG] Looking for JSON file: {path}")
    if not path.exists():
        print(f"[ERROR] JSON file not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"[DEBUG] Loaded JSON data: {data}")
        return data

def pick_story(stories, tone=None, exclude_tone=None):
    if tone:
        filtered = [s for s in stories if s.get("tone", "").lower() == tone.lower()]
        print(f"Filtered stories for tone '{tone}': {[s['title'] for s in filtered]}")
        if filtered:
            return random.choice(filtered)
    elif exclude_tone:
        filtered = [s for s in stories if s.get("tone", "").lower() != exclude_tone.lower()]
        print(f"Filtered stories excluding tone '{exclude_tone}': {[s['title'] for s in filtered]}")
        if filtered:
            return random.choice(filtered)
    return random.choice(stories)

# Debugging JSON validation
base = Path.cwd() / "src" / "storiesoffline"  # Corrected path for validation loop
for json_file in base.glob("*.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[VALID] {json_file}")
    except json.JSONDecodeError as e:
        print(f"[INVALID] {json_file}: {e}")