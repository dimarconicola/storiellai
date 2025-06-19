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

# Add other mock classes or logic as needed for your application