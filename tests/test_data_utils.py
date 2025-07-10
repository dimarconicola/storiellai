import unittest
from src.utils.data_utils import load_card_stories
from src.config.app_config import STORIES_FOLDER, BGM_FOLDER, AUDIO_FOLDER, AVAILABLE_TONES

class TestDataUtils(unittest.TestCase):
    def test_load_card_stories_invalid_uid(self):
        # Should return None for a non-existent UID
        self.assertIsNone(load_card_stories("notarealuid"))

if __name__ == "__main__":
    unittest.main()
