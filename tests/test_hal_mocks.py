import sys
import unittest
import os
from src.hardware.hal import UIDReader, Button, BUTTON_TAP

@unittest.skipIf(os.environ.get("STORYTELLER_PI", "False").lower() != "true", "Skip hardware tests on non-Pi systems")
class TestMockUIDReader(unittest.TestCase):
    def test_uid_cycle(self):
        reader = UIDReader()
        uids = [reader.read_uid() for _ in range(2)]
        self.assertTrue(uids[0] == "MOCK_UID" or uids[0] is None)

class TestMockButton(unittest.TestCase):
    def test_event(self):
        button = Button()
        self.assertEqual(button.get_event(), 0)

if __name__ == "__main__":
    unittest.main()
