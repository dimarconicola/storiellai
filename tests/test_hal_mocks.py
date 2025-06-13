import unittest
from src.hardware.hal import MockUIDReader, MockButton, BUTTON_TAP

class TestMockUIDReader(unittest.TestCase):
    def test_uid_cycle(self):
        reader = MockUIDReader()
        uids = [reader.read_uid() for _ in range(10)]
        self.assertEqual(len(set(uids)), 10)

class TestMockButton(unittest.TestCase):
    def test_led_state(self):
        button = MockButton()
        button.set_led(True)
        self.assertTrue(button.get_led_state())
        button.set_led(False)
        self.assertFalse(button.get_led_state())

    def test_event_queue(self):
        button = MockButton()
        button._event_queue.append(BUTTON_TAP)
        self.assertEqual(button.get_event(), BUTTON_TAP)

if __name__ == "__main__":
    unittest.main()
