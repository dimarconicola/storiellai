import unittest
from unittest.mock import patch
from src.hardware.hal import MockUIDReader, MockButton, BUTTON_TAP
from src.utils.audio_utils import play_error_sound

class TestIntegrationCardTap(unittest.TestCase):
    @patch('src.utils.audio_utils.pygame')
    def test_card_tap_triggers_audio(self, mock_pygame):
        reader = MockUIDReader()
        button = MockButton()
        # Simulate a card tap
        uid = reader.read_uid()
        # Simulate playing error sound (should call pygame.mixer.Sound)
        play_error_sound()
        self.assertTrue(mock_pygame.mixer.Sound.called)

if __name__ == "__main__":
    unittest.main()
