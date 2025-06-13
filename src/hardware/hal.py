# hal.py
"""
Hardware Abstraction Layer for Storyteller Box.
Provides both real (Raspberry Pi) and mock classes for:
- UID (NFC) reader
- Button with LED (tap, double-tap, long-press detection, PWM LED)
- Volume control via MCP3008 ADC

Allows seamless switching between real hardware and mock/testing environments.
"""

import time
import random
# Attempt to import Raspberry Pi specific libraries
IS_RASPBERRY_PI = True  # Force real hardware usage
try:
    # Test RPi.GPIO first as it's a primary indicator
    import RPi.GPIO as GPIO
    # If RPi.GPIO works, then try to import other RPi-specific things for ADC
    import board
    import busio
    import digitalio
    import adafruit_mcp3xxx.mcp3008 as ADConverter_MCP3008_Chip
    from adafruit_mcp3xxx.analog_in import AnalogIn as RealAnalogIn # Import real AnalogIn

    IS_RASPBERRY_PI = True
    print("[HAL] Raspberry Pi environment detected and real ADC libraries imported.")

    # This class, when instantiated, returns a configured MCP3008 chip object
    class MCP3008_HAL_Real_Provider:
        _mcp_chip_instance = None
        def __new__(cls):
            if cls._mcp_chip_instance is None:
                # SPI bus setup
                spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
                
                # Chip Select (CS) pin for MCP3008
                # TODO: Make CS_PIN_MCP3008 configurable via app_config.py
                # Ensure this pin is dedicated to MCP3008 and not conflicting
                # Example: Using GPIO25 (board.D25)
                cs_pin_name = "D25" 
                try:
                    cs = digitalio.DigitalInOut(getattr(board, cs_pin_name))
                except AttributeError:
                    print(f"[HAL_ERROR] CS pin {cs_pin_name} not found on board. Using D5 as fallback.")
                    cs = digitalio.DigitalInOut(board.D5) # Fallback, ensure this is valid
                
                cls._mcp_chip_instance = ADConverter_MCP3008_Chip.MCP3008(spi, cs)
                print(f"[HAL] Real MCP3008 chip initialized on SPI with CS pin {cs_pin_name}.")
            return cls._mcp_chip_instance

    MCP3008 = MCP3008_HAL_Real_Provider # Export this class/factory
    AnalogIn = RealAnalogIn # Export real AnalogIn

except ImportError as e:
    print(f"[HAL] ImportError during RPi setup: {e}. Using Mocks for ADC.")
    IS_RASPBERRY_PI = False 
except RuntimeError as e:
    print(f"[HAL] RuntimeError during RPi setup (likely RPi.GPIO): {e}. Using Mocks for ADC.")
    IS_RASPBERRY_PI = False

if not IS_RASPBERRY_PI:
    # This block executes on macOS or if RPi library imports fail
    class MockMCP3008_HAL_EmulatedChip:
        def __init__(self): # Called by MCP3008() in time_utils.py
            print("[HAL_Mock] MockMCP3008_HAL_EmulatedChip object created (simulates MCP3008 chip).")
            self.bits = 10 # MCP3008 is 10-bit
            self.reference_voltage = 3.3 # Common Vref, used by AnalogIn

        def _read(self, pin_index, is_differential=False):
            # This method is called by AnalogIn.value
            # It should return a raw integer ADC value (0-1023 for 10-bit).
            raw_value = 0
            if pin_index == 0: # Assuming battery voltage is on ADC channel 0
                # Simulate a battery voltage. Example: 3.7V actual, with a 1:2 voltage divider -> 1.85V at ADC pin.
                # Raw ADC value = (voltage_at_pin / adc_reference_voltage) * (2^adc_bits - 1)
                # Raw value = (1.85V / 3.3V) * 1023 = 0.5606 * 1023 = 573.4 ~= 573
                raw_value = 573 
                print(f"[HAL_Mock] MockMCP3008: Reading pin {pin_index} (battery), returning raw value {raw_value}.")
            else:
                # For other pins, return a default mock value, e.g., mid-scale
                raw_value = 512 
                print(f"[HAL_Mock] MockMCP3008: Reading pin {pin_index}, returning default raw value {raw_value}.")
            return raw_value
            
    MCP3008 = MockMCP3008_HAL_EmulatedChip # Export the mock class under the name MCP3008

    class MockAnalogIn:
        def __init__(self, mcp_chip_instance, pin_number, is_differential=False):
            self._mcp = mcp_chip_instance
            self._pin_number = pin_number
            self._is_differential = is_differential
            print(f"[HAL_Mock] MockAnalogIn created for pin {pin_number} on mock MCP chip: {type(self._mcp)}.")

        @property
        def value(self):
            raw_value = self._mcp._read(self._pin_number, self._is_differential)
            return raw_value

        @property
        def voltage(self):
            if not hasattr(self._mcp, 'bits') or not hasattr(self._mcp, 'reference_voltage'):
                print("[HAL_Mock_ERROR] MockMCP chip instance is missing 'bits' or 'reference_voltage' attributes.")
                return 0.0 
            
            val = self.value 
            ref_voltage = self._mcp.reference_voltage
            num_bits = self._mcp.bits
            max_adc_val = (2**num_bits) - 1

            if max_adc_val == 0: # Should not happen with self.bits = 10
                print("[HAL_Mock_ERROR] Max ADC value is zero (bits might be zero). Cannot calculate voltage.")
                return 0.0

            calculated_voltage = (val * ref_voltage) / max_adc_val
            return calculated_voltage
            
    AnalogIn = MockAnalogIn # Export mock AnalogIn

# Constants for RealButton event types
BUTTON_NO_EVENT = 0
BUTTON_TAP = 1
BUTTON_DOUBLE_TAP = 2
BUTTON_LONG_PRESS = 3

class MockUIDReader:
    """
    Mock NFC UID reader for development/testing without hardware.
    Simulates 10 unique UIDs, cycles through them on each read.
    """
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
    """
    Mock button with LED for development/testing.
    Simulates button events and LED state, including PWM for breathing/blink effects.
    """
    def __init__(self, button_pin=None, led_pin=None, long_press_duration=1.5, double_tap_window=0.3):
        print(f"[HAL_Mock] Initialized MockButton (Pin: {button_pin}, LED: {led_pin})")
        self._led_state = False
        self._led_pwm_active = False
        self._led_pwm_dc = 0
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
        self._led_pwm_active = False
        self._led_state = bool(state)
        print(f"[HAL_Mock] MockButton: LED set to {'ON' if self._led_state else 'OFF'} (PWM disabled)")

    def start_led_pwm(self, duty_cycle_percent, frequency=50):
        self._led_state = True # Consider LED on
        self._led_pwm_active = True
        self._led_pwm_dc = duty_cycle_percent
        print(f"[HAL_Mock] MockButton: LED PWM started at {frequency}Hz, {duty_cycle_percent}% duty cycle.")

    def stop_led_pwm(self):
        self._led_pwm_active = False
        self._led_state = False
        print(f"[HAL_Mock] MockButton: LED PWM stopped, LED OFF.")

    def change_led_pwm_duty_cycle(self, duty_cycle_percent):
        if self._led_pwm_active:
            self._led_pwm_dc = duty_cycle_percent
            print(f"[HAL_Mock] MockButton: LED PWM duty cycle changed to {duty_cycle_percent}%.")
        else:
            print(f"[HAL_Mock] MockButton: PWM not active, cannot change duty cycle.")

    def get_led_state(self):
        return self._led_state

    def cleanup(self):
        print("[HAL_Mock] MockButton cleanup.")

class MockVolumeControl:
    """
    Mock volume control for development/testing.
    Simulates a volume knob (returns a fixed or changing value).
    """
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
        """
        Real NFC UID reader (skeleton, to be implemented for actual hardware).
        """
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
        """
        Real button with LED for Raspberry Pi.
        - Handles tap, double-tap, long-press detection with debouncing
        - Supports PWM for breathing/blink LED patterns
        """
        def __init__(self, button_pin, led_pin=None, long_press_duration=1.5, double_tap_window=0.3, debounce_time=0.05):
            self.button_pin = button_pin
            self.led_pin = led_pin
            self.long_press_duration = long_press_duration
            self.double_tap_window = double_tap_window
            self.debounce_time = debounce_time # Time to wait for debounce

            self._led_state = False
            self.pwm_instance = None # For LED PWM control
            self.pwm_frequency = 50 # Default PWM frequency (Hz)

            # Button state variables
            self._physical_button_state = GPIO.HIGH # Current physical reading
            self._debounced_button_state = GPIO.HIGH # State after debouncing
            self._last_state_change_time = 0 # Time of last confirmed state change
            
            # Event detection state machine variables
            self._button_event_state = "IDLE" # States: IDLE, PRESSED, WAITING_FOR_SECOND_TAP
            self._first_press_time = 0
            self._first_release_time = 0

            GPIO.setmode(GPIO.BCM) # Use Broadcom pin numbering
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            if self.led_pin:
                GPIO.setup(self.led_pin, GPIO.OUT)
                GPIO.output(self.led_pin, GPIO.LOW) # LED off initially
            print(f"[HAL] Initialized RealButton on GPIO {self.button_pin} (LED: {self.led_pin}, Debounce: {self.debounce_time*1000:.0f}ms)")

        def _stop_pwm_if_active(self):
            if self.pwm_instance:
                self.pwm_instance.stop()
                self.pwm_instance = None
                # print("[HAL_DEBUG] PWM stopped.")

        def set_led(self, state):
            if self.led_pin:
                self._stop_pwm_if_active()
                new_gpio_state = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(self.led_pin, new_gpio_state)
                self._led_state = bool(state)
                # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def start_led_pwm(self, duty_cycle_percent, frequency=None):
            if not self.led_pin:
                return
            self._stop_pwm_if_active() # Stop any existing PWM or solid state
            
            active_frequency = frequency if frequency is not None else self.pwm_frequency
            if active_frequency <= 0: active_frequency = 50 # Ensure valid frequency
            
            self.pwm_instance = GPIO.PWM(self.led_pin, active_frequency)
            self.pwm_instance.start(max(0, min(100, duty_cycle_percent))) # Clamp duty cycle 0-100
            self._led_state = True # Consider PWM as LED being active
            # print(f"[HAL_DEBUG] PWM started at {active_frequency}Hz, {duty_cycle_percent}% duty cycle.")

        def stop_led_pwm(self):
            if not self.led_pin:
                return
            self._stop_pwm_if_active()
            GPIO.output(self.led_pin, GPIO.LOW) # Ensure LED is off after stopping PWM
            self._led_state = False

        def change_led_pwm_duty_cycle(self, duty_cycle_percent):
            if self.pwm_instance and self.led_pin:
                self.pwm_instance.ChangeDutyCycle(max(0, min(100, duty_cycle_percent))) # Clamp
                # print(f"[HAL_DEBUG] PWM duty cycle changed to {duty_cycle_percent}%.")
            elif self.led_pin: # If PWM not active, but trying to change, maybe start it?
                # For now, only change if already started. Or one could start it here.
                # print("[HAL_DEBUG] PWM not active, cannot change duty cycle. Call start_led_pwm first.")
                pass 

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT

            # --- Debouncing Logic ---
            raw_state = GPIO.input(self.button_pin)
            if raw_state != self._physical_button_state:
                # Physical state changed, reset debounce timer
                self._physical_button_state = raw_state
                self._last_state_change_time = current_time
                # print(f"[HAL_DEBUG] Button raw state: {'RELEASED' if raw_state == GPIO.HIGH else 'PRESSED'}")

            # If debounce time has passed since last raw change, confirm the state
            if (current_time - self._last_state_change_time) > self.debounce_time:
                if self._debounced_button_state != self._physical_button_state:
                    # print(f"[HAL_DEBUG] Button debounced state changed: {'RELEASED' if self._physical_button_state == GPIO.HIGH else 'PRESSED'}")
                    self._debounced_button_state = self._physical_button_state
                    # This is where we act on a confirmed press or release
                    
                    # --- Event State Machine based on debounced state changes ---
                    if self._debounced_button_state == GPIO.LOW: # Button Pressed
                        if self._button_event_state == "IDLE":
                            self._button_event_state = "PRESSED"
                            self._first_press_time = current_time
                            # print(f"[HAL_DEBUG] Event state: IDLE -> PRESSED at {self._first_press_time}")
                        elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                            # This is the second press for a double tap
                            if (current_time - self._first_press_time) < self.double_tap_window:
                                print("[HAL] RealButton: Double tap detected.")
                                event = BUTTON_DOUBLE_TAP
                                self._button_event_state = "IDLE" # Reset state
                            else:
                                # Too late for a double tap, treat as a new single press sequence
                                # print("[HAL_DEBUG] Second press too late for double tap, new press sequence.")
                                self._button_event_state = "PRESSED"
                                self._first_press_time = current_time 
                    
                    else: # Button Released (self._debounced_button_state == GPIO.HIGH)
                        if self._button_event_state == "PRESSED":
                            # Released after a press. Could be tap or start of double tap window.
                            # Check if it was a long press first (before release was detected)
                            # Note: Long press is typically checked while button is still held.
                            # This release signifies the end of a press that wasn't long enough to be a long press yet.
                            self._button_event_state = "WAITING_FOR_SECOND_TAP"
                            self._first_release_time = current_time
                            # print(f"[HAL_DEBUG] Event state: PRESSED -> WAITING_FOR_SECOND_TAP at {self._first_release_time}")
                        # If it was WAITING_FOR_SECOND_TAP and released, it means nothing (already released)
                        # If it was IDLE and released, it means nothing (already released)

            # --- Timeout and Long Press Logic (checked every call, regardless of debounced state change) ---
            if self._button_event_state == "PRESSED":
                if (current_time - self._first_press_time) > self.long_press_duration:
                    # print(f"[HAL_DEBUG] Checking for long press: current_time={current_time}, first_press_time={self._first_press_time}, diff={(current_time - self._first_press_time)}")
                    if self._debounced_button_state == GPIO.LOW: # Still pressed
                        print("[HAL] RealButton: Long press detected.")
                        event = BUTTON_LONG_PRESS
                        self._button_event_state = "IDLE" # Reset state after long press
            
            elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                # If window for double tap expires, it was a single tap
                if (current_time - self._first_press_time) > self.double_tap_window: 
                    # Ensure it's based on time from first press to allow for second press to occur and be processed
                    # More accurately, time from first release might be (current_time - self._first_release_time)
                    if (current_time - self._first_release_time) > self.double_tap_window: # Check from release time
                        print("[HAL] RealButton: Tap detected (double tap window expired).")
                        event = BUTTON_TAP
                        self._button_event_state = "IDLE" # Reset state

            return event

        def set_led(self, state):
            if self.led_pin:
                self._stop_pwm_if_active()
                new_gpio_state = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(self.led_pin, new_gpio_state)
                self._led_state = bool(state)
                # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def start_led_pwm(self, duty_cycle_percent, frequency=None):
            if not self.led_pin:
                return
            self._stop_pwm_if_active() # Stop any existing PWM or solid state
            
            active_frequency = frequency if frequency is not None else self.pwm_frequency
            if active_frequency <= 0: active_frequency = 50 # Ensure valid frequency
            
            self.pwm_instance = GPIO.PWM(self.led_pin, active_frequency)
            self.pwm_instance.start(max(0, min(100, duty_cycle_percent))) # Clamp duty cycle 0-100
            self._led_state = True # Consider PWM as LED being active
            # print(f"[HAL_DEBUG] PWM started at {active_frequency}Hz, {duty_cycle_percent}% duty cycle.")

        def stop_led_pwm(self):
            if not self.led_pin:
                return
            self._stop_pwm_if_active()
            GPIO.output(self.led_pin, GPIO.LOW) # Ensure LED is off after stopping PWM
            self._led_state = False

        def change_led_pwm_duty_cycle(self, duty_cycle_percent):
            if self.pwm_instance and self.led_pin:
                self.pwm_instance.ChangeDutyCycle(max(0, min(100, duty_cycle_percent))) # Clamp
                # print(f"[HAL_DEBUG] PWM duty cycle changed to {duty_cycle_percent}%.")
            elif self.led_pin: # If PWM not active, but trying to change, maybe start it?
                # For now, only change if already started. Or one could start it here.
                # print("[HAL_DEBUG] PWM not active, cannot change duty cycle. Call start_led_pwm first.")
                pass 

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT

            # --- Debouncing Logic ---
            raw_state = GPIO.input(self.button_pin)
            if raw_state != self._physical_button_state:
                # Physical state changed, reset debounce timer
                self._physical_button_state = raw_state
                self._last_state_change_time = current_time
                # print(f"[HAL_DEBUG] Button raw state: {'RELEASED' if raw_state == GPIO.HIGH else 'PRESSED'}")

            # If debounce time has passed since last raw change, confirm the state
            if (current_time - self._last_state_change_time) > self.debounce_time:
                if self._debounced_button_state != self._physical_button_state:
                    # print(f"[HAL_DEBUG] Button debounced state changed: {'RELEASED' if self._physical_button_state == GPIO.HIGH else 'PRESSED'}")
                    self._debounced_button_state = self._physical_button_state
                    # This is where we act on a confirmed press or release
                    
                    # --- Event State Machine based on debounced state changes ---
                    if self._debounced_button_state == GPIO.LOW: # Button Pressed
                        if self._button_event_state == "IDLE":
                            self._button_event_state = "PRESSED"
                            self._first_press_time = current_time
                            # print(f"[HAL_DEBUG] Event state: IDLE -> PRESSED at {self._first_press_time}")
                        elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                            # This is the second press for a double tap
                            if (current_time - self._first_press_time) < self.double_tap_window:
                                print("[HAL] RealButton: Double tap detected.")
                                event = BUTTON_DOUBLE_TAP
                                self._button_event_state = "IDLE" # Reset state
                            else:
                                # Too late for a double tap, treat as a new single press sequence
                                # print("[HAL_DEBUG] Second press too late for double tap, new press sequence.")
                                self._button_event_state = "PRESSED"
                                self._first_press_time = current_time 
                    
                    else: # Button Released (self._debounced_button_state == GPIO.HIGH)
                        if self._button_event_state == "PRESSED":
                            # Released after a press. Could be tap or start of double tap window.
                            # Check if it was a long press first (before release was detected)
                            # Note: Long press is typically checked while button is still held.
                            # This release signifies the end of a press that wasn't long enough to be a long press yet.
                            self._button_event_state = "WAITING_FOR_SECOND_TAP"
                            self._first_release_time = current_time
                            # print(f"[HAL_DEBUG] Event state: PRESSED -> WAITING_FOR_SECOND_TAP at {self._first_release_time}")
                        # If it was WAITING_FOR_SECOND_TAP and released, it means nothing (already released)
                        # If it was IDLE and released, it means nothing (already released)

            # --- Timeout and Long Press Logic (checked every call, regardless of debounced state change) ---
            if self._button_event_state == "PRESSED":
                if (current_time - self._first_press_time) > self.long_press_duration:
                    # print(f"[HAL_DEBUG] Checking for long press: current_time={current_time}, first_press_time={self._first_press_time}, diff={(current_time - self._first_press_time)}")
                    if self._debounced_button_state == GPIO.LOW: # Still pressed
                        print("[HAL] RealButton: Long press detected.")
                        event = BUTTON_LONG_PRESS
                        self._button_event_state = "IDLE" # Reset state after long press
            
            elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                # If window for double tap expires, it was a single tap
                if (current_time - self._first_press_time) > self.double_tap_window: 
                    # Ensure it's based on time from first press to allow for second press to occur and be processed
                    # More accurately, time from first release might be (current_time - self._first_release_time)
                    if (current_time - self._first_release_time) > self.double_tap_window: # Check from release time
                        print("[HAL] RealButton: Tap detected (double tap window expired).")
                        event = BUTTON_TAP
                        self._button_event_state = "IDLE" # Reset state

            return event

        def set_led(self, state):
            if self.led_pin:
                self._stop_pwm_if_active()
                new_gpio_state = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(self.led_pin, new_gpio_state)
                self._led_state = bool(state)
                # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def start_led_pwm(self, duty_cycle_percent, frequency=None):
            if not self.led_pin:
                return
            self._stop_pwm_if_active() # Stop any existing PWM or solid state
            
            active_frequency = frequency if frequency is not None else self.pwm_frequency
            if active_frequency <= 0: active_frequency = 50 # Ensure valid frequency
            
            self.pwm_instance = GPIO.PWM(self.led_pin, active_frequency)
            self.pwm_instance.start(max(0, min(100, duty_cycle_percent))) # Clamp duty cycle 0-100
            self._led_state = True # Consider PWM as LED being active
            # print(f"[HAL_DEBUG] PWM started at {active_frequency}Hz, {duty_cycle_percent}% duty cycle.")

        def stop_led_pwm(self):
            if not self.led_pin:
                return
            self._stop_pwm_if_active()
            GPIO.output(self.led_pin, GPIO.LOW) # Ensure LED is off after stopping PWM
            self._led_state = False

        def change_led_pwm_duty_cycle(self, duty_cycle_percent):
            if self.pwm_instance and self.led_pin:
                self.pwm_instance.ChangeDutyCycle(max(0, min(100, duty_cycle_percent))) # Clamp
                # print(f"[HAL_DEBUG] PWM duty cycle changed to {duty_cycle_percent}%.")
            elif self.led_pin: # If PWM not active, but trying to change, maybe start it?
                # For now, only change if already started. Or one could start it here.
                # print("[HAL_DEBUG] PWM not active, cannot change duty cycle. Call start_led_pwm first.")
                pass 

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT

            # --- Debouncing Logic ---
            raw_state = GPIO.input(self.button_pin)
            if raw_state != self._physical_button_state:
                # Physical state changed, reset debounce timer
                self._physical_button_state = raw_state
                self._last_state_change_time = current_time
                # print(f"[HAL_DEBUG] Button raw state: {'RELEASED' if raw_state == GPIO.HIGH else 'PRESSED'}")

            # If debounce time has passed since last raw change, confirm the state
            if (current_time - self._last_state_change_time) > self.debounce_time:
                if self._debounced_button_state != self._physical_button_state:
                    # print(f"[HAL_DEBUG] Button debounced state changed: {'RELEASED' if self._physical_button_state == GPIO.HIGH else 'PRESSED'}")
                    self._debounced_button_state = self._physical_button_state
                    # This is where we act on a confirmed press or release
                    
                    # --- Event State Machine based on debounced state changes ---
                    if self._debounced_button_state == GPIO.LOW: # Button Pressed
                        if self._button_event_state == "IDLE":
                            self._button_event_state = "PRESSED"
                            self._first_press_time = current_time
                            # print(f"[HAL_DEBUG] Event state: IDLE -> PRESSED at {self._first_press_time}")
                        elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                            # This is the second press for a double tap
                            if (current_time - self._first_press_time) < self.double_tap_window:
                                print("[HAL] RealButton: Double tap detected.")
                                event = BUTTON_DOUBLE_TAP
                                self._button_event_state = "IDLE" # Reset state
                            else:
                                # Too late for a double tap, treat as a new single press sequence
                                # print("[HAL_DEBUG] Second press too late for double tap, new press sequence.")
                                self._button_event_state = "PRESSED"
                                self._first_press_time = current_time 
                    
                    else: # Button Released (self._debounced_button_state == GPIO.HIGH)
                        if self._button_event_state == "PRESSED":
                            # Released after a press. Could be tap or start of double tap window.
                            # Check if it was a long press first (before release was detected)
                            # Note: Long press is typically checked while button is still held.
                            # This release signifies the end of a press that wasn't long enough to be a long press yet.
                            self._button_event_state = "WAITING_FOR_SECOND_TAP"
                            self._first_release_time = current_time
                            # print(f"[HAL_DEBUG] Event state: PRESSED -> WAITING_FOR_SECOND_TAP at {self._first_release_time}")
                        # If it was WAITING_FOR_SECOND_TAP and released, it means nothing (already released)
                        # If it was IDLE and released, it means nothing (already released)

            # --- Timeout and Long Press Logic (checked every call, regardless of debounced state change) ---
            if self._button_event_state == "PRESSED":
                if (current_time - self._first_press_time) > self.long_press_duration:
                    # print(f"[HAL_DEBUG] Checking for long press: current_time={current_time}, first_press_time={self._first_press_time}, diff={(current_time - self._first_press_time)}")
                    if self._debounced_button_state == GPIO.LOW: # Still pressed
                        print("[HAL] RealButton: Long press detected.")
                        event = BUTTON_LONG_PRESS
                        self._button_event_state = "IDLE" # Reset state after long press
            
            elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                # If window for double tap expires, it was a single tap
                if (current_time - self._first_press_time) > self.double_tap_window: 
                    # Ensure it's based on time from first press to allow for second press to occur and be processed
                    # More accurately, time from first release might be (current_time - self._first_release_time)
                    if (current_time - self._first_release_time) > self.double_tap_window: # Check from release time
                        print("[HAL] RealButton: Tap detected (double tap window expired).")
                        event = BUTTON_TAP
                        self._button_event_state = "IDLE" # Reset state

            return event

        def set_led(self, state):
            if self.led_pin:
                self._stop_pwm_if_active()
                new_gpio_state = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(self.led_pin, new_gpio_state)
                self._led_state = bool(state)
                # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def start_led_pwm(self, duty_cycle_percent, frequency=None):
            if not self.led_pin:
                return
            self._stop_pwm_if_active() # Stop any existing PWM or solid state
            
            active_frequency = frequency if frequency is not None else self.pwm_frequency
            if active_frequency <= 0: active_frequency = 50 # Ensure valid frequency
            
            self.pwm_instance = GPIO.PWM(self.led_pin, active_frequency)
            self.pwm_instance.start(max(0, min(100, duty_cycle_percent))) # Clamp duty cycle 0-100
            self._led_state = True # Consider PWM as LED being active
            # print(f"[HAL_DEBUG] PWM started at {active_frequency}Hz, {duty_cycle_percent}% duty cycle.")

        def stop_led_pwm(self):
            if not self.led_pin:
                return
            self._stop_pwm_if_active()
            GPIO.output(self.led_pin, GPIO.LOW) # Ensure LED is off after stopping PWM
            self._led_state = False

        def change_led_pwm_duty_cycle(self, duty_cycle_percent):
            if self.pwm_instance and self.led_pin:
                self.pwm_instance.ChangeDutyCycle(max(0, min(100, duty_cycle_percent))) # Clamp
                # print(f"[HAL_DEBUG] PWM duty cycle changed to {duty_cycle_percent}%.")
            elif self.led_pin: # If PWM not active, but trying to change, maybe start it?
                # For now, only change if already started. Or one could start it here.
                # print("[HAL_DEBUG] PWM not active, cannot change duty cycle. Call start_led_pwm first.")
                pass 

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT

            # --- Debouncing Logic ---
            raw_state = GPIO.input(self.button_pin)
            if raw_state != self._physical_button_state:
                # Physical state changed, reset debounce timer
                self._physical_button_state = raw_state
                self._last_state_change_time = current_time
                # print(f"[HAL_DEBUG] Button raw state: {'RELEASED' if raw_state == GPIO.HIGH else 'PRESSED'}")

            # If debounce time has passed since last raw change, confirm the state
            if (current_time - self._last_state_change_time) > self.debounce_time:
                if self._debounced_button_state != self._physical_button_state:
                    # print(f"[HAL_DEBUG] Button debounced state changed: {'RELEASED' if self._physical_button_state == GPIO.HIGH else 'PRESSED'}")
                    self._debounced_button_state = self._physical_button_state
                    # This is where we act on a confirmed press or release
                    
                    # --- Event State Machine based on debounced state changes ---
                    if self._debounced_button_state == GPIO.LOW: # Button Pressed
                        if self._button_event_state == "IDLE":
                            self._button_event_state = "PRESSED"
                            self._first_press_time = current_time
                            # print(f"[HAL_DEBUG] Event state: IDLE -> PRESSED at {self._first_press_time}")
                        elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                            # This is the second press for a double tap
                            if (current_time - self._first_press_time) < self.double_tap_window:
                                print("[HAL] RealButton: Double tap detected.")
                                event = BUTTON_DOUBLE_TAP
                                self._button_event_state = "IDLE" # Reset state
                            else:
                                # Too late for a double tap, treat as a new single press sequence
                                # print("[HAL_DEBUG] Second press too late for double tap, new press sequence.")
                                self._button_event_state = "PRESSED"
                                self._first_press_time = current_time 
                    
                    else: # Button Released (self._debounced_button_state == GPIO.HIGH)
                        if self._button_event_state == "PRESSED":
                            # Released after a press. Could be tap or start of double tap window.
                            # Check if it was a long press first (before release was detected)
                            # Note: Long press is typically checked while button is still held.
                            # This release signifies the end of a press that wasn't long enough to be a long press yet.
                            self._button_event_state = "WAITING_FOR_SECOND_TAP"
                            self._first_release_time = current_time
                            # print(f"[HAL_DEBUG] Event state: PRESSED -> WAITING_FOR_SECOND_TAP at {self._first_release_time}")
                        # If it was WAITING_FOR_SECOND_TAP and released, it means nothing (already released)
                        # If it was IDLE and released, it means nothing (already released)

            # --- Timeout and Long Press Logic (checked every call, regardless of debounced state change) ---
            if self._button_event_state == "PRESSED":
                if (current_time - self._first_press_time) > self.long_press_duration:
                    # print(f"[HAL_DEBUG] Checking for long press: current_time={current_time}, first_press_time={self._first_press_time}, diff={(current_time - self._first_press_time)}")
                    if self._debounced_button_state == GPIO.LOW: # Still pressed
                        print("[HAL] RealButton: Long press detected.")
                        event = BUTTON_LONG_PRESS
                        self._button_event_state = "IDLE" # Reset state after long press
            
            elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                # If window for double tap expires, it was a single tap
                if (current_time - self._first_press_time) > self.double_tap_window: 
                    # Ensure it's based on time from first press to allow for second press to occur and be processed
                    # More accurately, time from first release might be (current_time - self._first_release_time)
                    if (current_time - self._first_release_time) > self.double_tap_window: # Check from release time
                        print("[HAL] RealButton: Tap detected (double tap window expired).")
                        event = BUTTON_TAP
                        self._button_event_state = "IDLE" # Reset state

            return event

        def set_led(self, state):
            if self.led_pin:
                self._stop_pwm_if_active()
                new_gpio_state = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(self.led_pin, new_gpio_state)
                self._led_state = bool(state)
                # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def start_led_pwm(self, duty_cycle_percent, frequency=None):
            if not self.led_pin:
                return
            self._stop_pwm_if_active() # Stop any existing PWM or solid state
            
            active_frequency = frequency if frequency is not None else self.pwm_frequency
            if active_frequency <= 0: active_frequency = 50 # Ensure valid frequency
            
            self.pwm_instance = GPIO.PWM(self.led_pin, active_frequency)
            self.pwm_instance.start(max(0, min(100, duty_cycle_percent))) # Clamp duty cycle 0-100
            self._led_state = True # Consider PWM as LED being active
            # print(f"[HAL_DEBUG] PWM started at {active_frequency}Hz, {duty_cycle_percent}% duty cycle.")

        def stop_led_pwm(self):
            if not self.led_pin:
                return
            self._stop_pwm_if_active()
            GPIO.output(self.led_pin, GPIO.LOW) # Ensure LED is off after stopping PWM
            self._led_state = False

        def change_led_pwm_duty_cycle(self, duty_cycle_percent):
            if self.pwm_instance and self.led_pin:
                self.pwm_instance.ChangeDutyCycle(max(0, min(100, duty_cycle_percent))) # Clamp
                # print(f"[HAL_DEBUG] PWM duty cycle changed to {duty_cycle_percent}%.")
            elif self.led_pin: # If PWM not active, but trying to change, maybe start it?
                # For now, only change if already started. Or one could start it here.
                # print("[HAL_DEBUG] PWM not active, cannot change duty cycle. Call start_led_pwm first.")
                pass 

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT

            # --- Debouncing Logic ---
            raw_state = GPIO.input(self.button_pin)
            if raw_state != self._physical_button_state:
                # Physical state changed, reset debounce timer
                self._physical_button_state = raw_state
                self._last_state_change_time = current_time
                # print(f"[HAL_DEBUG] Button raw state: {'RELEASED' if raw_state == GPIO.HIGH else 'PRESSED'}")

            # If debounce time has passed since last raw change, confirm the state
            if (current_time - self._last_state_change_time) > self.debounce_time:
                if self._debounced_button_state != self._physical_button_state:
                    # print(f"[HAL_DEBUG] Button debounced state changed: {'RELEASED' if self._physical_button_state == GPIO.HIGH else 'PRESSED'}")
                    self._debounced_button_state = self._physical_button_state
                    # This is where we act on a confirmed press or release
                    
                    # --- Event State Machine based on debounced state changes ---
                    if self._debounced_button_state == GPIO.LOW: # Button Pressed
                        if self._button_event_state == "IDLE":
                            self._button_event_state = "PRESSED"
                            self._first_press_time = current_time
                            # print(f"[HAL_DEBUG] Event state: IDLE -> PRESSED at {self._first_press_time}")
                        elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                            # This is the second press for a double tap
                            if (current_time - self._first_press_time) < self.double_tap_window:
                                print("[HAL] RealButton: Double tap detected.")
                                event = BUTTON_DOUBLE_TAP
                                self._button_event_state = "IDLE" # Reset state
                            else:
                                # Too late for a double tap, treat as a new single press sequence
                                # print("[HAL_DEBUG] Second press too late for double tap, new press sequence.")
                                self._button_event_state = "PRESSED"
                                self._first_press_time = current_time 
                    
                    else: # Button Released (self._debounced_button_state == GPIO.HIGH)
                        if self._button_event_state == "PRESSED":
                            # Released after a press. Could be tap or start of double tap window.
                            # Check if it was a long press first (before release was detected)
                            # Note: Long press is typically checked while button is still held.
                            # This release signifies the end of a press that wasn't long enough to be a long press yet.
                            self._button_event_state = "WAITING_FOR_SECOND_TAP"
                            self._first_release_time = current_time
                            # print(f"[HAL_DEBUG] Event state: PRESSED -> WAITING_FOR_SECOND_TAP at {self._first_release_time}")
                        # If it was WAITING_FOR_SECOND_TAP and released, it means nothing (already released)
                        # If it was IDLE and released, it means nothing (already released)

            # --- Timeout and Long Press Logic (checked every call, regardless of debounced state change) ---
            if self._button_event_state == "PRESSED":
                if (current_time - self._first_press_time) > self.long_press_duration:
                    # print(f"[HAL_DEBUG] Checking for long press: current_time={current_time}, first_press_time={self._first_press_time}, diff={(current_time - self._first_press_time)}")
                    if self._debounced_button_state == GPIO.LOW: # Still pressed
                        print("[HAL] RealButton: Long press detected.")
                        event = BUTTON_LONG_PRESS
                        self._button_event_state = "IDLE" # Reset state after long press
            
            elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                # If window for double tap expires, it was a single tap
                if (current_time - self._first_press_time) > self.double_tap_window: 
                    # Ensure it's based on time from first press to allow for second press to occur and be processed
                    # More accurately, time from first release might be (current_time - self._first_release_time)
                    if (current_time - self._first_release_time) > self.double_tap_window: # Check from release time
                        print("[HAL] RealButton: Tap detected (double tap window expired).")
                        event = BUTTON_TAP
                        self._button_event_state = "IDLE" # Reset state

            return event

        def set_led(self, state):
            if self.led_pin:
                self._stop_pwm_if_active()
                new_gpio_state = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(self.led_pin, new_gpio_state)
                self._led_state = bool(state)
                # print(f"[HAL] RealButton: LED set to {'ON' if self._led_state else 'OFF'}")

        def start_led_pwm(self, duty_cycle_percent, frequency=None):
            if not self.led_pin:
                return
            self._stop_pwm_if_active() # Stop any existing PWM or solid state
            
            active_frequency = frequency if frequency is not None else self.pwm_frequency
            if active_frequency <= 0: active_frequency = 50 # Ensure valid frequency
            
            self.pwm_instance = GPIO.PWM(self.led_pin, active_frequency)
            self.pwm_instance.start(max(0, min(100, duty_cycle_percent))) # Clamp duty cycle 0-100
            self._led_state = True # Consider PWM as LED being active
            # print(f"[HAL_DEBUG] PWM started at {active_frequency}Hz, {duty_cycle_percent}% duty cycle.")

        def stop_led_pwm(self):
            if not self.led_pin:
                return
            self._stop_pwm_if_active()
            GPIO.output(self.led_pin, GPIO.LOW) # Ensure LED is off after stopping PWM
            self._led_state = False

        def change_led_pwm_duty_cycle(self, duty_cycle_percent):
            if self.pwm_instance and self.led_pin:
                self.pwm_instance.ChangeDutyCycle(max(0, min(100, duty_cycle_percent))) # Clamp
                # print(f"[HAL_DEBUG] PWM duty cycle changed to {duty_cycle_percent}%.")
            elif self.led_pin: # If PWM not active, but trying to change, maybe start it?
                # For now, only change if already started. Or one could start it here.
                # print("[HAL_DEBUG] PWM not active, cannot change duty cycle. Call start_led_pwm first.")
                pass 

        def get_event(self):
            current_time = time.monotonic()
            event = BUTTON_NO_EVENT

            # --- Debouncing Logic ---
            raw_state = GPIO.input(self.button_pin)
            if raw_state != self._physical_button_state:
                # Physical state changed, reset debounce timer
                self._physical_button_state = raw_state
                self._last_state_change_time = current_time
                # print(f"[HAL_DEBUG] Button raw state: {'RELEASED' if raw_state == GPIO.HIGH else 'PRESSED'}")

            # If debounce time has passed since last raw change, confirm the state
            if (current_time - self._last_state_change_time) > self.debounce_time:
                if self._debounced_button_state != self._physical_button_state:
                    # print(f"[HAL_DEBUG] Button debounced state changed: {'RELEASED' if self._physical_button_state == GPIO.HIGH else 'PRESSED'}")
                    self._debounced_button_state = self._physical_button_state
                    # This is where we act on a confirmed press or release
                    
                    # --- Event State Machine based on debounced state changes ---
                    if self._debounced_button_state == GPIO.LOW: # Button Pressed
                        if self._button_event_state == "IDLE":
                            self._button_event_state = "PRESSED"
                            self._first_press_time = current_time
                            # print(f"[HAL_DEBUG] Event state: IDLE -> PRESSED at {self._first_press_time}")
                        elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                            # This is the second press for a double tap
                            if (current_time - self._first_press_time) < self.double_tap_window:
                                print("[HAL] RealButton: Double tap detected.")
                                event = BUTTON_DOUBLE_TAP
                                self._button_event_state = "IDLE" # Reset state
                            else:
                                # Too late for a double tap, treat as a new single press sequence
                                # print("[HAL_DEBUG] Second press too late for double tap, new press sequence.")
                                self._button_event_state = "PRESSED"
                                self._first_press_time = current_time 
                    
                    else: # Button Released (self._debounced_button_state == GPIO.HIGH)
                        if self._button_event_state == "PRESSED":
                            # Released after a press. Could be tap or start of double tap window.
                            # Check if it was a long press first (before release was detected)
                            # Note: Long press is typically checked while button is still held.
                            # This release signifies the end of a press that wasn't long enough to be a long press yet.
                            self._button_event_state = "WAITING_FOR_SECOND_TAP"
                            self._first_release_time = current_time
                            # print(f"[HAL_DEBUG] Event state: PRESSED -> WAITING_FOR_SECOND_TAP at {self._first_release_time}")
                        # If it was WAITING_FOR_SECOND_TAP and released, it means nothing (already released)
                        # If it was IDLE and released, it means nothing (already released)

            # --- Timeout and Long Press Logic (checked every call, regardless of debounced state change) ---
            if self._button_event_state == "PRESSED":
                if (current_time - self._first_press_time) > self.long_press_duration:
                    # print(f"[HAL_DEBUG] Checking for long press: current_time={current_time}, first_press_time={self._first_press_time}, diff={(current_time - self._first_press_time)}")
                    if self._debounced_button_state == GPIO.LOW: # Still pressed
                        print("[HAL] RealButton: Long press detected.")
                        event = BUTTON_LONG_PRESS
                        self._button_event_state = "IDLE" # Reset state after long press
            
            elif self._button_event_state == "WAITING_FOR_SECOND_TAP":
                # If window for double tap expires, it was a single tap
                if (current_time - self._first_press_time) > self.double_tap_window: 
                    # Ensure it's based on time from first press to allow for second press to occur and be processed
                    # More accurately, time from first release might be (current_time - self._first_release_time)
                    if (current_time - self._first_release_time) > self.double_tap_window: # Check from release time
                        print("[HAL] RealButton: Tap detected (double tap window expired).")
                        event = BUTTON_TAP
                        self._button_event_state = "IDLE" # Reset state

            return event

        def cleanup(self):
            self._stop_pwm_if_active()
            if self.led_pin:
                GPIO.output(self.led_pin, GPIO.LOW)
            # GPIO.cleanup([self.button_pin, self.led_pin]) # Clean up specific pins
            print(f"[HAL] RealButton cleanup for pins: {self.button_pin}, {self.led_pin}")
            pass # GPIO.cleanup() should be called once globally if at all for long running scripts

    class RealVolumeControl:
        """
        Real volume control using MCP3008 ADC (skeleton, to be implemented for actual hardware).
        """
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