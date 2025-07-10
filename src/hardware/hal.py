# hal.py
"""
Hardware Abstraction Layer (HAL) for interfacing with hardware components
"""

import os

# Constants for button events
BUTTON_NO_EVENT = 0
BUTTON_TAP = 1
BUTTON_DOUBLE_TAP = 2
BUTTON_LONG_PRESS = 3

# Set this to True to use real implementations
IS_RASPBERRY_PI = os.environ.get("STORYTELLER_PI", "False").lower() == "true"

if IS_RASPBERRY_PI:
    import board
    import busio
    from digitalio import DigitalInOut
    from adafruit_pn532.spi import PN532_SPI
    from adafruit_mcp3xxx.mcp3008 import MCP3008
    from adafruit_mcp3xxx.analog_in import AnalogIn

    # SPI setup for RFID
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D5)
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()

    # SPI setup for MCP3008
    cs = board.D8 # Using a different CS pin for the MCP3008
    mcp = MCP3008(spi, cs)

    class UIDReader:
        def __init__(self, *args, **kwargs):
            pass

        def read(self):
            """Read both UID and text from the card. Returns (uid, text)"""
            uid = pn532.read_passive_target(timeout=0.5)
            if uid is None:
                return None, None

            uid_str = "".join([hex(i)[2:] for i in uid])
            print(f"[DEBUG] Found card with UID: {uid_str}")

            # Try to read data from the card
            try:
                # Authenticate with the default key
                if not pn532.mifare_classic_authenticate_block(uid, 4, 0x60, b'\xFF\xFF\xFF\xFF\xFF\xFF'):
                    print("[ERROR] Failed to authenticate block 4")
                    return uid_str, None
                
                data = pn532.mifare_classic_read_block(4)
                if data:
                    text = data.decode('utf-8').strip('\x00')
                    print(f"[DEBUG] Read text from card: {text}")
                    return uid_str, text
                else:
                    print("[DEBUG] No data found on card")
                    return uid_str, None

            except Exception as e:
                print(f"[ERROR] Error reading from card: {e}")
                return uid_str, None
        
        def read_uid(self):
            """Legacy method that only returns the UID"""
            uid = pn532.read_passive_target(timeout=0.5)
            if uid is None:
                return None
            return "".join([hex(i)[2:] for i in uid])

        def cleanup(self):
            pass

else:
    print("[HAL] Using mock implementations for hardware.")

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
        
        def read(self):
            """Read both UID and text from the card. Returns (uid, text)"""
            if not self._called:
                self._called = True
                print('[DEBUG] UIDReader returning MOCK_UID and "000001"')
                return "MOCK_UID", "000001"
            print('[DEBUG] UIDReader returning None')
            return None, None
        
        def read_uid(self):
            """Legacy method that only returns the UID"""
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