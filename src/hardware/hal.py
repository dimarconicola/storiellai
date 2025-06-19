# hal.py
"""
Hardware Abstraction Layer (HAL) for interfacing with hardware components
"""

# Constants for button events
BUTTON_NO_EVENT = 0
BUTTON_TAP = 1
BUTTON_DOUBLE_TAP = 2
BUTTON_LONG_PRESS = 3

# Set this to False to use mock implementations
IS_RASPBERRY_PI = False

print("[HAL] Using mock implementations for hardware.")

# Example mock class for MCP3008 (replace with your actual mock if needed)
class MCP3008_HAL_Real_Provider:
    _mcp_chip_instance = None

    def __new__(cls):
        if cls._mcp_chip_instance is None:
            cls._mcp_chip_instance = object()  # Replace with actual mock logic if needed
        return cls._mcp_chip_instance

# Mock MCP3008 class
class MCP3008:
    def __init__(self, *args, **kwargs):
        pass

# Mock AnalogIn class
class AnalogIn:
    def __init__(self, mcp, pin):
        self.value = 0
        self.voltage = 0.0

# Mock UIDReader class
class UIDReader:
    def __init__(self, *args, **kwargs):
        self._called = False
    def read_uid(self):
        if not self._called:
            self._called = True
            print('[DEBUG] UIDReader returning MOCK_UID')
            return "MOCK_UID"
        print('[DEBUG] UIDReader returning None')
        return None
    def cleanup(self):
        pass

# Mock Button class
class Button:
    def __init__(self, *args, **kwargs):
        pass
    def get_event(self):
        return BUTTON_NO_EVENT
    def set_led(self, value):
        pass
    def stop_led_pwm(self):
        pass
    def start_led_pwm(self, *args, **kwargs):
        pass
    def change_led_pwm_duty_cycle(self, *args, **kwargs):
        pass
    def cleanup(self):
        pass

# Mock VolumeControl class
class VolumeControl:
    def __init__(self, *args, **kwargs):
        self.level = 0.5
    def get_level(self):
        return self.level
    def set_level(self, value):
        self.level = value
    def get_volume(self):
        # Mock method: return current level
        return self.level
    def cleanup(self):
        # Mock method: do nothing
        pass