import time
from enum import Enum, auto

class FSMState(Enum):
    BOOTING = auto()
    IDLE = auto()
    CARD_READ = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    LONG_PRESS = auto()
    END = auto()
    ERROR = auto()

class LedController:
    def set_breathing(self, freq_hz=1, brightness=1.0):
        # Implement hardware-specific breathing effect
        print(f"[LED] Breathing {freq_hz} Hz, brightness {brightness}")

    def set_off(self):
        print("[LED] Off")

    def blink(self, times=1, on_ms=100, off_ms=100):
        for _ in range(times):
            print("[LED] ON")
            time.sleep(on_ms / 1000)
            print("[LED] OFF")
            time.sleep(off_ms / 1000)

    def set_on(self, brightness=1.0):
        print(f"[LED] ON, brightness {brightness}")

    def set_error(self):
        # Blink 8 Hz × 3s
        for _ in range(24):
            print("[LED] ERROR BLINK")
            time.sleep(0.0625)

class ButtonController:
    def is_pressed(self):
        # Return True if button is pressed (hardware)
        return False

    def wait_for_press(self, timeout=None):
        # Block until press or timeout
        pass

    def wait_for_release(self, timeout=None):
        # Block until release or timeout
        pass

class LedButtonFSM:
    def __init__(self, led: LedController, button: ButtonController):
        self.led = led
        self.button = button
        self.state = FSMState.BOOTING

    def set_state(self, new_state):
        self.state = new_state
        self.update_led()

    def update_led(self):
        s = self.state
        if s == FSMState.BOOTING:
            self.led.set_breathing(freq_hz=1, brightness=1.0)
        elif s == FSMState.IDLE:
            self.led.set_off()
        elif s == FSMState.CARD_READ:
            self.led.blink(times=2, on_ms=100, off_ms=100)
            self.led.set_off()
        elif s == FSMState.LOADING:
            self.led.blink(times=0, on_ms=125, off_ms=125)  # 4 Hz blink
        elif s == FSMState.PLAYING:
            self.led.set_breathing(freq_hz=1, brightness=0.4)
        elif s == FSMState.PAUSED:
            self.led.set_breathing(freq_hz=0.5, brightness=0.7)
        elif s == FSMState.LONG_PRESS:
            self.led.blink(times=0, on_ms=250, off_ms=250)  # 2 Hz blink
        elif s == FSMState.END:
            self.led.blink(times=2, on_ms=200, off_ms=800)
            self.led.set_off()
        elif s == FSMState.ERROR:
            self.led.set_error()
            self.led.set_off()

    def button_action(self):
        # Example: call this in your main loop
        if self.state == FSMState.PLAYING and self.button.is_pressed():
            self.set_state(FSMState.PAUSED)
        elif self.state == FSMState.PAUSED and self.button.is_pressed():
            self.set_state(FSMState.PLAYING)
        # Add long-press and other logic as needed

# Example usage:
if __name__ == "__main__":
    led = LedController()
    button = ButtonController()
    fsm = LedButtonFSM(led, button)

    # Simulate state changes
    fsm.set_state(FSMState.BOOTING)
    time.sleep(1)
    fsm.set_state(FSMState.IDLE)
    time.sleep(1)
    fsm.set_state(FSMState.CARD_READ)
    time.sleep(1)
    fsm.set_state(FSMState.LOADING)
    time.sleep(1)
    fsm.set_state(FSMState.PLAYING)
    time.sleep(1)
    fsm.set_state(FSMState.PAUSED)
    time.sleep(1)
    fsm.set_state(FSMState.LONG_PRESS)
    time.sleep(1)
    fsm.set_state(FSMState.END)
    time.sleep(1)
    fsm.set_state(FSMState.ERROR)