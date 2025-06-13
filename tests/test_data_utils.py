import unittest
from src.utils.data_utils import load_card_stories

class TestDataUtils(unittest.TestCase):
    def test_load_card_stories_invalid_uid(self):
        # Should return None for a non-existent UID
        self.assertIsNone(load_card_stories("notarealuid"))

    # Add more tests for valid cases, malformed JSON, etc.

if __name__ == "__main__":
    unittest.main()
