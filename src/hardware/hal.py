import time
import random
# Attempt to import Raspberry Pi specific libraries
IS_RASPBERRY_PI = False
try:
    import RPi.GPIO as GPIO
    # For MCP3008 (ADC for volume knob)
    # import Adafruit_MCP3008
    # For PN532 (NFC Reader)
    # from pn532 import PN532_SPI # This is just an example, actual library may vary
    IS_RASPBERRY_PI = True
    print("[HAL] Raspberry Pi environment detected.")
except ImportError:
    print("[HAL] Not running on Raspberry Pi or required libraries (RPi.GPIO, Adafruit_MCP3008, PN532) not found. Using Mocks.")
except RuntimeError as e:
    print(f"[HAL] Error importing RPi.GPIO: {e}. (Are you root or in gpio group?). Using Mocks.")

# Constants for RealButton event types
BUTTON_NO_EVENT = 0
BUTTON_TAP = 1
BUTTON_DOUBLE_TAP = 2
BUTTON_LONG_PRESS = 3

class MockUIDReader:
    def __init__(self):
        # 10 unique UIDs
        self.uids = [f"{i:06d}" for i in range(10)]
        self.index = 0

    def read_uid(self):
        # Simulate reading a card after 1-2 seconds
        time.sleep(random.uniform(1, 2))
        uid = self.uids[self.index]
        print(f"[HAL_Mock] Card detected! UID={uid}")
        self.index = (self.index + 1) % len(self.uids)
        return uid

    def cleanup(self):
        print("[HAL_Mock] MockUIDReader cleanup.")

class MockButton:
    def __init__(self, button_pin=None, led_pin=None, long_press_duration=1.5, double_tap_window=0.3):
        print(f"[HAL_Mock] Initialized MockButton (Pin: {button_pin}, LED: {led_pin})")
        self._led_state = False
        # To simulate event detection for testing main loop
        self._event_queue = [] 
        self._last_event_time = time.monotonic()

    def get_event(self):
        # Simulate events for testing, e.g., by typing 't' for tap, 'd' for double, 'l' for long
        # For automated simulation, we can queue them up
        if self._event_queue:
            return self._event_queue.pop(0)
        
        # Simple simulation: generate a random event occasionally
        if time.monotonic() - self._last_event_time > 5: # Every 5 seconds, maybe an event
            self._last_event_time = time.monotonic()
            evt = random.choice([BUTTON_NO_EVENT, BUTTON_TAP, BUTTON_DOUBLE_TAP, BUTTON_LONG_PRESS, BUTTON_NO_EVENT, BUTTON_NO_EVENT])
            if evt != BUTTON_NO_EVENT:
                print(f"[HAL_Mock] MockButton: Simulated event {evt}")
                return evt
        return BUTTON_NO_EVENT

    def set_led(self, state):
        self._led_state = bool(state)
        print(f"[HAL_Mock] MockButton: LED set to {'ON' if self._led_state else 'OFF'}")

    def get_led_state(self):
        return self._led_state

    def cleanup(self):
        print("[HAL_Mock] MockButton cleanup.")

class MockVolumeControl:
    def __init__(self, adc_channel=None, spi_port=None, spi_cs=None):
        print(f"[HAL_Mock] Initialized MockVolumeControl (ADC Channel: {adc_channel})")
        self._volume = 0.75 # Default mock volume

    def get_volume(self):
        # Simulate volume changes for testing
        # self._volume = (self._volume + 0.1) % 1.0 
        print(f"[HAL_Mock] MockVolumeControl: Current volume {self._volume:.2f}")
        return self._volume

    def cleanup(self):
        print("[HAL_Mock] MockVolumeControl cleanup.")


if IS_RASPBERRY_PI:
    # Ensure GPIO is cleaned up properly on exit, though systemd services might handle this differently
    # GPIO.setwarnings(False) # Disable warnings if they are noisy

    class RealUIDReader:
        def __init__(self, spi_port=0, spi_cs_pin=0, irq_pin=None, rst_pin=None):
            # Example using a generic PN532 library structure
            # self.pn532 = PN532_SPI(cs=spi_cs_pin, irq=irq_pin, reset=rst_pin) # spi_port might be implicit
            # self.pn532.SAM_configuration()
            # print(f"[HAL] Initialized RealUIDReader (SPI{spi_port}-CS{spi_cs_pin})")
            print(f"[HAL] RealUIDReader initialized (NOT IMPLEMENTED) SPI{spi_port}-CS{spi_cs_pin}, IRQ:{irq_pin}, RST:{rst_pin}")


        def read_uid(self):
            # uid_bytes = self.pn532.read_passive_target(timeout=0.5) # ms or s depends on lib
            # if uid_bytes is None:
            #     return None
            # # Convert UID to string, format might vary (hex, decimal, etc.)
            # uid_string = "".join([format(i, "02x") for i in uid_bytes])
            # print(f"[HAL] RealUIDReader: Card detected! UID={uid_string}")
            # return uid_string
            print("[HAL] RealUIDReader: read_uid() called (NOT IMPLEMENTED)")
            time.sleep(1) # Simulate scan delay
            # Simulate finding a card occasionally for testing purposes
            if random.random() < 0.3: # 30% chance to "find" a card
                found_uid = f"{random.randint(0,999999):06d}"
                print(f"[HAL] RealUIDReader: Simulated card found UID={found_uid}")
                return found_uid
            return None


        def cleanup(self):
            # Specific cleanup for the NFC reader if needed
            print("[HAL] RealUIDReader cleanup.")
            pass

    class RealButton:
        def __init__(self, button_pin, led_pin=None, long_press_duration=1.5, double_tap_window=0.3):
            self.button_pin = button_pin
            self.led_pin = led_pin
            self.long_press_duration = long_press_duration
            self.double_tap_window = double_tap_window

            self._button_state = GPIO.HIGH # Assuming pull-up resistor (pressed is LOW)
            self._led_state = False
            
            self._last_press_time = 0
            self._last_release_time = 0
            self._press_count = 0
            self._long_press_pending = False
            self._last_event_check_time = time.monotonic()

            GPIO.setmode(GPIO.BCM) # Use Broadcom pin numbering
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            if self.led_pin:
                GPIO.setup(self.led_pin, GPIO.OUT)
                GPIO.output(self.led_pin, GPIO.LOW) # LED off initially
            print(f"[HAL] Initialized RealButton on GPIO {self.button_pin} (LED: {self.led_pin})")

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT
            
            # Read current physical state of the button
            physical_button_state = GPIO.input(self.button_pin)

            # Edge detection: State changed from HIGH to LOW (pressed)
            if self._button_state == GPIO.HIGH and physical_button_state == GPIO.LOW:
                self._last_press_time = current_time
                self._long_press_pending = True
                self._press_count += 1
                print(f"[HAL_DEBUG] Button pressed at {self._last_press_time}, count: {self._press_count}")

            # Edge detection: State changed from LOW to HIGH (released)
            elif self._button_state == GPIO.LOW and physical_button_state == GPIO.HIGH:
                self._last_release_time = current_time
                self._long_press_pending = False
                print(f"[HAL_DEBUG] Button released at {self._last_release_time}")

                if self._press_count == 1: # First press in a potential double tap sequence
                    # Wait for double_tap_window to see if a second press occurs
                    # This simple get_event won't handle this well without more state/delay
                    # For now, a release after one press is a TAP, unless it was long
                    # This part needs refinement for robust double tap
                    pass # Handled by timeout logic below

            # Update internal button state
            self._button_state = physical_button_state

            # Check for long press
            if self._long_press_pending and (current_time - self._last_press_time) > self.long_press_duration:
                if self._button_state == GPIO.LOW: # Still pressed
                    print("[HAL] RealButton: Long press detected.")
                    event = BUTTON_LONG_PRESS
                    self._long_press_pending = False # Event triggered
                    self._press_count = 0 # Reset sequence
            
            # Check for tap or double tap (after button release or window expiry)
            if event == BUTTON_NO_EVENT and self._press_count > 0 and physical_button_state == GPIO.HIGH: # Button is released
                if (current_time - self._last_press_time) < self.long_press_duration: # Not a long press
                    if self._press_count == 1 and (current_time - self._last_release_time) > self.double_tap_window :
                        # Single tap if double tap window has passed since its release
                        print("[HAL] RealButton: Tap detected.")
                        event = BUTTON_TAP
                        self._press_count = 0
                    elif self._press_count >= 2 and (current_time - self._last_press_time) < self.double_tap_window: # Check time from first press
                        # This logic is tricky; a proper state machine is better.
                        # Let's simplify: if two presses occurred quickly.
                        # This needs to be based on time between releases or presses.
                        # A simpler approach: if _press_count is 2 and last_release_time is recent
                        if self._press_count == 2: # Simplified: second release
                             print("[HAL] RealButton: Double tap detected.")
                             event = BUTTON_DOUBLE_TAP
                             self._press_count = 0

            # Reset press_count if too much time has passed since last activity
            if self._press_count > 0 and (current_time - self._last_press_time) > (self.double_tap_window + 0.1): # A bit more than window
                 if physical_button_state == GPIO.HIGH and event == BUTTON_NO_EVENT and (current_time - self._last_release_time) > self.double_tap_window:
                    # If it was a single press and window expired, it's a tap
                    if (self._last_press_time > self._last_release_time and self._press_count ==1 ): # pressed but not yet released for tap
                        pass # still waiting for release or long press
                    elif self._press_count == 1: # it was released, window passed
                        print("[HAL] RealButton: Tap detected (timeout).")
                        event = BUTTON_TAP
                        self._press_count = 0


            self._last_event_check_time = current_time
            return event

        def set_led(self, state):
            if self.led_pin:
                new_state = bool(state)
                if self._led_state != new_state:
                    GPIO.output(self.led_pin, GPIO.HIGH if new_state else GPIO.LOW)
                    self._led_state = new_state
                    # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def get_led_state(self):
            return self._led_state

        def cleanup(self):
            if self.led_pin:
                GPIO.output(self.led_pin, GPIO.LOW)
            # GPIO.cleanup([self.button_pin, self.led_pin]) # Clean up specific pins
            print(f"[HAL] RealButton cleanup for pins: {self.button_pin}, {self.led_pin}")
            pass # GPIO.cleanup() should be called once globally if at all for long running scripts

    class RealVolumeControl:
        def __init__(self, adc_channel=0, spi_port=0, spi_cs=0, spi_clk=None, spi_miso=None, spi_mosi=None):
            # For MCP3008, you'd typically use a library like Adafruit_MCP3008
            # Example:
            # SPI_PORT   = spi_port
            # SPI_DEVICE = spi_cs # This usually means CS0 or CS1, not a GPIO number directly for hardware SPI
            # if spi_clk and spi_miso and spi_mosi: # Software SPI
            #    self.mcp = Adafruit_MCP3008.MCP3008(clk=spi_clk, cs=spi_cs, miso=spi_miso, mosi=spi_mosi)
            # else: # Hardware SPI
            #    self.mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
            self.adc_channel = adc_channel
            # print(f"[HAL] Initialized RealVolumeControl (ADC Channel: {self.adc_channel})")
            print(f"[HAL] RealVolumeControl initialized (NOT IMPLEMENTED) ADC Channel: {self.adc_channel}, SPI{spi_port}-CS{spi_cs}")


        def get_volume(self):
            # value = self.mcp.read_adc(self.adc_channel) # Value from 0 to 1023
            # # Normalize to 0.0 - 1.0
            # normalized_volume = value / 1023.0
            # print(f"[HAL] RealVolumeControl: Raw ADC {value}, Volume {normalized_volume:.2f}")
            # return normalized_volume
            print("[HAL] RealVolumeControl: get_volume() called (NOT IMPLEMENTED)")
            return 0.75 # Placeholder

        def cleanup(self):
            print("[HAL] RealVolumeControl cleanup.")
            pass

else: # Not on Raspberry Pi, ensure Real classes are not used if IS_RASPBERRY_PI is False
    class RealUIDReader: # Define as placeholder if not on Pi
        def __init__(self, *args, **kwargs): raise NotImplementedError("RealUIDReader only available on Raspberry Pi")
        def read_uid(self): raise NotImplementedError()
        def cleanup(self): raise NotImplementedError()

    class RealButton: # Define as placeholder
        def __init__(self, *args, **kwargs): raise NotImplementedError("RealButton only available on Raspberry Pi")
        def get_event(self): raise NotImplementedError()
        def set_led(self, state): raise NotImplementedError()
        def get_led_state(self): raise NotImplementedError()
        def cleanup(self): raise NotImplementedError()

    class RealVolumeControl: # Define as placeholder
        def __init__(self, *args, **kwargs): raise NotImplementedError("RealVolumeControl only available on Raspberry Pi")
        def get_volume(self): raise NotImplementedError()
        def cleanup(self): raise NotImplementedError()

# Example usage (for testing HAL itself)
if __name__ == "__main__":
    print(f"Running on Raspberry Pi: {IS_RASPBERRY_PI}")

    if IS_RASPBERRY_PI:
        # IMPORTANT: Replace with your actual GPIO pin numbers
        BUTTON_GPIO = 23 
        LED_GPIO = 24
        NFC_IRQ = 25
        NFC_RST = 17
        ADC_CHANNEL = 0 # For volume on MCP3008 channel 0

        reader = RealUIDReader(spi_port=0, spi_cs_pin=0, irq_pin=NFC_IRQ, rst_pin=NFC_RST)
        button = RealButton(button_pin=BUTTON_GPIO, led_pin=LED_GPIO)
        volume_ctrl = RealVolumeControl(adc_channel=ADC_CHANNEL)
        
        try:
            print("Testing Real HAL components (stubs for now)...")
            print("Reading UID (stubbed):", reader.read_uid())
            
            print("Press button for events (stubbed logic)...")
            # This test loop for RealButton needs refinement as get_event is non-blocking
            # for _ in range(200): # Test for 20 seconds
            #     event = button.get_event()
            #     if event != BUTTON_NO_EVENT:
            #         print(f"Button Event Detected: {event}")
            #     time.sleep(0.1)

            print("Getting volume (stubbed):", volume_ctrl.get_volume())
            button.set_led(True)
            time.sleep(1)
            button.set_led(False)
        finally:
            reader.cleanup()
            button.cleanup()
            volume_ctrl.cleanup()
            if IS_RASPBERRY_PI:
                 GPIO.cleanup() # General cleanup if no other components are using GPIO
                 print("[HAL] GPIO.cleanup() called.")
    else:
        mock_reader = MockUIDReader()
        mock_button = MockButton()
        mock_volume = MockVolumeControl()

        print("Testing Mock HAL components...")
        print("Reading UID (mock):", mock_reader.read_uid())
        # Simulate adding events to mock button for testing
        mock_button._event_queue.extend([BUTTON_TAP, BUTTON_NO_EVENT, BUTTON_LONG_PRESS])
        print("Button Event (mock):", mock_button.get_event())
        print("Button Event (mock):", mock_button.get_event())
        print("Button Event (mock):", mock_button.get_event())
        mock_button.set_led(True)
        print("Getting volume (mock):", mock_volume.get_volume())
        
        mock_reader.cleanup()
        mock_button.cleanup()
        mock_volume.cleanup()