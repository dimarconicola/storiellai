import time

class MockUIDReader:
    def __init__(self):
        # 10 unique UIDs
        self.uids = [f"{i:06d}" for i in range(10)]
        self.index = 0

    def read_uid(self):
        # Simulate reading a card after 2 seconds
        time.sleep(2)
        uid = self.uids[self.index]
        print(f"Mock: Card detected! UID={uid}")
        self.index = (self.index + 1) % len(self.uids)
        return uid

class MockButton:
    def wait_for_tap(self):
        # Simulate a button tap after 1 second
        time.sleep(1)
        print("Mock: Button tapped!")
        return True

if __name__ == "__main__":
    reader = MockUIDReader()
    button = MockButton()
    for _ in range(10):
        reader.read_uid()
    button.wait_for_tap()