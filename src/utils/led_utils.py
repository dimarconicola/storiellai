"""
LED utilities for the Storyteller Box.
Manages LED feedback patterns (solid, blink, breathing, pulse, fade, heartbeat, and more)
for visual feedback about system states.
"""

import time
import math
from typing import Callable, Optional, List


class LedPatternManager:
    """
    Manages LED feedback patterns for the button LED.
    Call update() frequently from the main loop to keep the pattern smooth.
    
    Supported patterns:
    - solid: Static on/off
    - off: LED turned off
    - blink: Regular on/off blinking
    - breathing: Smooth sinusoidal breathing effect
    - pulse: Quick pulse with fade in/out
    - heartbeat: Double pulse like a heartbeat
    - morse: Custom morse code pattern
    - fadeout: Gradually fade from bright to off
    - sos: SOS emergency pattern (... --- ...)
    - progress: Visual progress indicator
    - rainbow: Smooth color transition between virtual RGB values (simulated with brightness)
    - colorshift: Transition between different brightness levels to simulate color shifting
    - countdown: Visual countdown timer with decreasing brightness
    - attention: Pattern designed to grab attention (fast pulses with pauses)
    - success: Visual indication of successful operation (3 ascending pulses)
    - error: Visual indication of error (decreasing brightness pulses)
    """
    def __init__(self, button):
        self.button = button
        self.pattern = 'solid'  # Current pattern name
        self.last_update = time.monotonic()
        self.blink_on = False
        self.blink_period = 1.0
        self.blink_duty = 0.5
        self.breathing_period = 2.5
        self.solid_state = True
        self._last_breath = 0
        self._blink_count = 0
        self._blink_target = None
        self._blink_callback = None
        
        # Pattern-specific variables
        self._pulse_stage = 0
        self._pulse_stages = 10
        self._heartbeat_stage = 0
        self._morse_pattern = []
        self._morse_index = 0
        self._morse_element_start = 0
        self._morse_dot_duration = 0.2
        self._fadeout_start = 0
        self._fadeout_duration = 2.0
        self._fadeout_initial = 100
        self._progress_percent = 0
        self._progress_update_time = 0
        self._next_pattern = None  # For auto-transitioning patterns
        self._transition_callback = None
        
        # SOS pattern timing
        self._sos_sequence = [True, False, True, False, True, False,  # S (...)
                              False, False,  # pause
                              True, False, True, False, True, False,  # O (---)
                              False, False,  # pause
                              True, False, True, False, True, False]  # S (...)
        self._sos_index = 0
        self._sos_element_duration = 0.2  # duration of each element
        
        # New pattern variables
        self._rainbow_hue = 0  # Virtual hue for rainbow effect (0-360)
        self._rainbow_speed = 1.0  # Speed multiplier for rainbow transition
        self._rainbow_start_time = 0
        
        self._colorshift_values = [20, 50, 80, 100]  # Brightness levels for color shift
        self._colorshift_index = 0
        self._colorshift_duration = 0.3  # Time per color
        self._colorshift_last_change = 0
        
        self._countdown_start = 0
        self._countdown_duration = 5.0  # Total countdown duration
        self._countdown_initial_brightness = 100
        
        self._attention_phase = 0
        self._attention_last_change = 0
        self._attention_sequence = [
            (100, 0.05),  # (brightness, duration)
            (0, 0.05),
            (100, 0.05),
            (0, 0.05),
            (100, 0.05),
            (0, 0.4),     # Longer pause
        ]
        
        self._success_phase = 0
        self._success_last_change = 0
        self._success_sequence = [
            (30, 0.1),   # Low brightness, short
            (0, 0.05),
            (60, 0.15),  # Medium brightness, medium
            (0, 0.05),
            (100, 0.3),  # Full brightness, longer
            (0, 0.2),    # Off, then repeat or transition
        ]
        
        self._error_phase = 0
        self._error_last_change = 0
        self._error_sequence = [
            (100, 0.1),  # Full brightness, short
            (0, 0.05),
            (70, 0.1),   # Lower brightness
            (0, 0.05),
            (40, 0.1),   # Even lower
            (0, 0.3),    # Off, then repeat or transition
        ]

    def set_pattern(self, pattern, **kwargs):
        """
        Set LED pattern with optional parameters.
        
        Args:
            pattern (str): Pattern type
            **kwargs: Pattern-specific parameters
                - state (bool): For 'solid' pattern
                - period (float): Cycle time for patterns
                - duty (float): Duty cycle for blink
                - count (int): Number of iterations before auto-transition
                - callback (callable): Function to call after pattern completes
                - next_pattern (str): Pattern to transition to after completion
                - intensity (float): Light intensity (0.0-1.0)
                - message (str): For morse pattern
                - duration (float): For timed patterns
                - percent (float): For progress pattern (0-100)
                - speed (float): For animation speed control
                - levels (list): For custom brightness levels
                - sequence (list): For custom pattern sequences
        """
        self.pattern = pattern
        self.last_update = time.monotonic()
        self._next_pattern = kwargs.get('next_pattern', None)
        self._transition_callback = kwargs.get('callback', None)
        
        if pattern == 'solid':
            self.solid_state = kwargs.get('state', True)
            self.button.set_led(self.solid_state)
            self.button.stop_led_pwm()
            
        elif pattern == 'off':
            self.button.set_led(False)
            self.button.stop_led_pwm()
            
        elif pattern == 'blink':
            self.blink_period = kwargs.get('period', 0.5)
            self.blink_duty = kwargs.get('duty', 0.5)
            self._blink_count = 0
            self._blink_target = kwargs.get('count', None)
            self._blink_callback = kwargs.get('callback', None)
            self.blink_on = False
            self.button.set_led(False)
            self.button.stop_led_pwm()
            
        elif pattern == 'breathing':
            self.breathing_period = kwargs.get('period', 2.5)
            self.button.start_led_pwm(0)
            self._last_breath = time.monotonic()
            
        elif pattern == 'pulse':
            self._pulse_stage = 0
            self._pulse_stages = kwargs.get('stages', 10)
            self.button.start_led_pwm(0)
            
        elif pattern == 'heartbeat':
            self._heartbeat_stage = 0
            self.button.start_led_pwm(0)
            
        elif pattern == 'morse':
            # Convert message to morse sequence
            message = kwargs.get('message', 'SOS')
            self._morse_pattern = self._text_to_morse(message)
            self._morse_index = 0
            self._morse_element_start = time.monotonic()
            self._morse_dot_duration = kwargs.get('dot_duration', 0.2)
            self.button.set_led(False)
            self.button.stop_led_pwm()
            
        elif pattern == 'fadeout':
            self._fadeout_start = time.monotonic()
            self._fadeout_duration = kwargs.get('duration', 2.0)
            self._fadeout_initial = kwargs.get('initial', 100)
            self.button.start_led_pwm(self._fadeout_initial)
            
        elif pattern == 'sos':
            self._sos_index = 0
            self._sos_element_duration = kwargs.get('element_duration', 0.2)
            self.button.set_led(True)  # Start with first element (on)
            self.button.stop_led_pwm()
            
        elif pattern == 'progress':
            self._progress_percent = kwargs.get('percent', 0)
            self._progress_update_time = time.monotonic()
            self.button.start_led_pwm(self._calculate_progress_duty())
            
        # New patterns
        elif pattern == 'rainbow':
            self._rainbow_hue = kwargs.get('start_hue', 0)
            self._rainbow_speed = kwargs.get('speed', 1.0)
            self._rainbow_start_time = time.monotonic()
            self.button.start_led_pwm(50)  # Start at middle brightness
            
        elif pattern == 'colorshift':
            self._colorshift_values = kwargs.get('levels', [20, 50, 80, 100])
            self._colorshift_duration = kwargs.get('duration', 0.3)
            self._colorshift_index = 0
            self._colorshift_last_change = time.monotonic()
            self.button.start_led_pwm(self._colorshift_values[0])
            
        elif pattern == 'countdown':
            self._countdown_start = time.monotonic()
            self._countdown_duration = kwargs.get('duration', 5.0)
            self._countdown_initial_brightness = kwargs.get('initial_brightness', 100)
            self.button.start_led_pwm(self._countdown_initial_brightness)
            
        elif pattern == 'attention':
            self._attention_phase = 0
            self._attention_last_change = time.monotonic()
            custom_sequence = kwargs.get('sequence', None)
            if custom_sequence:
                self._attention_sequence = custom_sequence
            self.button.start_led_pwm(self._attention_sequence[0][0])
            
        elif pattern == 'success':
            self._success_phase = 0
            self._success_last_change = time.monotonic()
            custom_sequence = kwargs.get('sequence', None)
            if custom_sequence:
                self._success_sequence = custom_sequence
            self.button.start_led_pwm(self._success_sequence[0][0])
            
        elif pattern == 'error':
            self._error_phase = 0
            self._error_last_change = time.monotonic()
            custom_sequence = kwargs.get('sequence', None)
            if custom_sequence:
                self._error_sequence = custom_sequence
            self.button.start_led_pwm(self._error_sequence[0][0])
            
        else:
            # Default to off if unknown pattern
            self.button.set_led(False)
            self.button.stop_led_pwm()

    def update(self):
        """Update LED pattern state - call this frequently from main loop"""
        now = time.monotonic()
        
        if self.pattern == 'solid':
            # Static on/off - no updates needed
            pass
            
        elif self.pattern == 'off':
            # LED off - no updates needed
            pass
            
        elif self.pattern == 'blink':
            elapsed = now - self.last_update
            period = self.blink_period
            duty = self.blink_duty
            on_time = period * duty
            
            if self.blink_on:
                if elapsed >= on_time:
                    self.button.set_led(False)
                    self.blink_on = False
                    self.last_update = now
                    if self._blink_target is not None:
                        self._blink_count += 1
                        if self._blink_count >= self._blink_target:
                            if self._blink_callback:
                                self._blink_callback()
                            if self._next_pattern:
                                self.set_pattern(self._next_pattern)
                            else:
                                self.set_pattern('solid', state=True)
            else:
                if elapsed >= (period - on_time):
                    self.button.set_led(True)
                    self.blink_on = True
                    self.last_update = now
                    
        elif self.pattern == 'breathing':
            t = (now - self._last_breath) % self.breathing_period
            # Breathing: duty cycle varies sinusoidally between 10% and 100%
            duty = 10 + 90 * 0.5 * (1 - math.cos(2 * math.pi * t / self.breathing_period))
            self.button.change_led_pwm_duty_cycle(duty)
            
        elif self.pattern == 'pulse':
            # Pulse: Quick rise, longer fall
            t = (now - self.last_update)
            pulse_duration = 0.8  # Total duration of one pulse
            
            if t > pulse_duration:
                self.last_update = now
                self._pulse_stage = 0
                
            elif t < 0.2:  # Fast rise (25% of pulse)
                duty = min(100, t * 500)  # 0 to 100 in 0.2s
                self.button.change_led_pwm_duty_cycle(duty)
                
            else:  # Slower fall (75% of pulse)
                decay = (t - 0.2) / 0.6  # 0 to 1 over 0.6s
                duty = max(0, 100 * (1 - decay))
                self.button.change_led_pwm_duty_cycle(duty)
                
        elif self.pattern == 'heartbeat':
            # Double pulse like a heartbeat
            t = (now - self.last_update) % 1.6  # 1.6s per full heartbeat
            
            if t < 0.15:  # First beat rise
                duty = min(100, t * 667)  # 0 to 100 in 0.15s
                self.button.change_led_pwm_duty_cycle(duty)
                
            elif t < 0.3:  # First beat fall
                decay = (t - 0.15) / 0.15
                duty = max(0, 100 * (1 - decay))
                self.button.change_led_pwm_duty_cycle(duty)
                
            elif t < 0.45:  # Brief pause
                self.button.change_led_pwm_duty_cycle(0)
                
            elif t < 0.6:  # Second beat rise
                rise = (t - 0.45) / 0.15
                duty = min(100, rise * 100)
                self.button.change_led_pwm_duty_cycle(duty)
                
            elif t < 0.8:  # Second beat fall
                decay = (t - 0.6) / 0.2
                duty = max(0, 100 * (1 - decay))
                self.button.change_led_pwm_duty_cycle(duty)
                
            else:  # Long pause
                self.button.change_led_pwm_duty_cycle(0)
                
        elif self.pattern == 'morse':
            if not self._morse_pattern:
                if self._next_pattern:
                    self.set_pattern(self._next_pattern)
                return
                
            element_elapsed = now - self._morse_element_start
            current_element = self._morse_pattern[self._morse_index]
            
            # Dot = 1 unit, Dash = 3 units, Space between elements = 1 unit,
            # Space between letters = 3 units, Space between words = 7 units
            element_duration = self._morse_dot_duration
            if current_element == '.':
                if element_elapsed < element_duration:
                    self.button.set_led(True)
                else:
                    self.button.set_led(False)
                    self._morse_index += 1
                    self._morse_element_start = now
            elif current_element == '-':
                if element_elapsed < 3 * element_duration:
                    self.button.set_led(True)
                else:
                    self.button.set_led(False)
                    self._morse_index += 1
                    self._morse_element_start = now
            elif current_element == ' ':
                if element_elapsed < element_duration:
                    self.button.set_led(False)
                else:
                    self._morse_index += 1
                    self._morse_element_start = now
            elif current_element == '/':  # Word space
                if element_elapsed < 7 * element_duration:
                    self.button.set_led(False)
                else:
                    self._morse_index += 1
                    self._morse_element_start = now
                    
            # Check if we've completed the pattern
            if self._morse_index >= len(self._morse_pattern):
                self._morse_index = 0
                self._morse_element_start = now
                if self._blink_target is not None:
                    self._blink_count += 1
                    if self._blink_count >= self._blink_target:
                        if self._transition_callback:
                            self._transition_callback()
                        if self._next_pattern:
                            self.set_pattern(self._next_pattern)
                        else:
                            self.set_pattern('solid', state=True)
                            
        elif self.pattern == 'fadeout':
            elapsed = now - self._fadeout_start
            if elapsed >= self._fadeout_duration:
                self.button.change_led_pwm_duty_cycle(0)
                if self._next_pattern:
                    self.set_pattern(self._next_pattern)
                else:
                    self.set_pattern('off')
            else:
                progress = elapsed / self._fadeout_duration
                duty = self._fadeout_initial * (1 - progress)
                self.button.change_led_pwm_duty_cycle(duty)
                
        elif self.pattern == 'sos':
            elapsed = now - self.last_update
            if elapsed >= self._sos_element_duration:
                self._sos_index = (self._sos_index + 1) % len(self._sos_sequence)
                self.button.set_led(self._sos_sequence[self._sos_index])
                self.last_update = now
                
                # Complete cycle check
                if self._sos_index == 0 and self._blink_target is not None:
                    self._blink_count += 1
                    if self._blink_count >= self._blink_target:
                        if self._transition_callback:
                            self._transition_callback()
                        if self._next_pattern:
                            self.set_pattern(self._next_pattern)
                        else:
                            self.set_pattern('solid', state=True)
                            
        elif self.pattern == 'progress':
            # Progress indicator updates periodically
            if now - self._progress_update_time > 0.05:  # Update every 50ms
                self.button.change_led_pwm_duty_cycle(self._calculate_progress_duty())
                self._progress_update_time = now
                
        elif self.pattern == 'rainbow':
            # Rainbow effect simulated through brightness
            elapsed = now - self._rainbow_start_time
            # Map virtual hue (0-360) to brightness (0-100)
            # This creates a smooth oscillation between brightness levels
            self._rainbow_hue = (elapsed * 90 * self._rainbow_speed) % 360
            # Map hue to brightness using a sine wave for smooth transitions
            brightness = 50 + 50 * math.sin(math.radians(self._rainbow_hue))
            self.button.change_led_pwm_duty_cycle(brightness)
            
        elif self.pattern == 'colorshift':
            # Shift between different brightness levels to simulate color shifting
            elapsed = now - self._colorshift_last_change
            if elapsed >= self._colorshift_duration:
                self._colorshift_index = (self._colorshift_index + 1) % len(self._colorshift_values)
                new_brightness = self._colorshift_values[self._colorshift_index]
                self.button.change_led_pwm_duty_cycle(new_brightness)
                self._colorshift_last_change = now
                
                # Check for pattern completion
                if self._colorshift_index == 0 and self._blink_target is not None:
                    self._blink_count += 1
                    if self._blink_count >= self._blink_target:
                        if self._transition_callback:
                            self._transition_callback()
                        if self._next_pattern:
                            self.set_pattern(self._next_pattern)
            
        elif self.pattern == 'countdown':
            # Visual countdown timer
            elapsed = now - self._countdown_start
            if elapsed >= self._countdown_duration:
                self.button.change_led_pwm_duty_cycle(0)
                if self._next_pattern:
                    self.set_pattern(self._next_pattern)
                else:
                    self.set_pattern('off')
            else:
                # Linear decrease in brightness
                progress = elapsed / self._countdown_duration
                brightness = self._countdown_initial_brightness * (1 - progress)
                self.button.change_led_pwm_duty_cycle(brightness)
                
        elif self.pattern == 'attention':
            # Attention-grabbing pattern
            elapsed = now - self._attention_last_change
            current_phase = self._attention_phase
            current_duration = self._attention_sequence[current_phase][1]
            
            if elapsed >= current_duration:
                # Move to next phase
                self._attention_phase = (self._attention_phase + 1) % len(self._attention_sequence)
                next_brightness = self._attention_sequence[self._attention_phase][0]
                self.button.change_led_pwm_duty_cycle(next_brightness)
                self._attention_last_change = now
                
                # Check for pattern completion (one full cycle)
                if self._attention_phase == 0 and self._blink_target is not None:
                    self._blink_count += 1
                    if self._blink_count >= self._blink_target:
                        if self._transition_callback:
                            self._transition_callback()
                        if self._next_pattern:
                            self.set_pattern(self._next_pattern)
                
        elif self.pattern == 'success':
            # Success indication pattern
            elapsed = now - self._success_last_change
            current_phase = self._success_phase
            current_duration = self._success_sequence[current_phase][1]
            
            if elapsed >= current_duration:
                # Move to next phase
                self._success_phase = (self._success_phase + 1) % len(self._success_sequence)
                next_brightness = self._success_sequence[self._success_phase][0]
                self.button.change_led_pwm_duty_cycle(next_brightness)
                self._success_last_change = now
                
                # Check for pattern completion (one full cycle)
                if self._success_phase == 0 and self._blink_target is not None:
                    self._blink_count += 1
                    if self._blink_count >= self._blink_target:
                        if self._transition_callback:
                            self._transition_callback()
                        if self._next_pattern:
                            self.set_pattern(self._next_pattern)
                            
        elif self.pattern == 'error':
            # Error indication pattern
            elapsed = now - self._error_last_change
            current_phase = self._error_phase
            current_duration = self._error_sequence[current_phase][1]
            
            if elapsed >= current_duration:
                # Move to next phase
                self._error_phase = (self._error_phase + 1) % len(self._error_sequence)
                next_brightness = self._error_sequence[self._error_phase][0]
                self.button.change_led_pwm_duty_cycle(next_brightness)
                self._error_last_change = now
                
                # Check for pattern completion (one full cycle)
                if self._error_phase == 0 and self._blink_target is not None:
                    self._blink_count += 1
                    if self._blink_count >= self._blink_target:
                        if self._transition_callback:
                            self._transition_callback()
                        if self._next_pattern:
                            self.set_pattern(self._next_pattern)
                
        else:
            # Unknown pattern defaults to off
            self.button.set_led(False)

    def _calculate_progress_duty(self):
        """Calculate duty cycle for progress pattern"""
        # Map progress percentage to duty cycle with a minimum brightness
        return max(10, min(100, self._progress_percent))
        
    def set_progress(self, percent):
        """Update progress percentage for progress pattern"""
        self._progress_percent = max(0, min(100, percent))
        
    def _text_to_morse(self, text):
        """Convert text to morse code sequence"""
        morse_dict = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 
            'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 
            'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 
            'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 
            'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---', 
            '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...', 
            '8': '---..', '9': '----.', ' ': '/'
        }
        
        result = []
        for char in text.upper():
            if char in morse_dict:
                morse = morse_dict[char]
                for symbol in morse:
                    result.append(symbol)
                    result.append(' ')  # Space between symbols
                result.append(' ')  # Extra space between letters (3 units total)
            elif char == ' ':
                result.append('/')  # Word space
                result.append(' ')
                
        return result
        
    def set_sos(self, count=2, next_pattern='breathing'):
        """Shortcut to set SOS emergency pattern"""
        self.set_pattern('sos', count=count, next_pattern=next_pattern)
        
    def set_boot_sequence(self):
        """Sequence for system boot: triple pulse then breathing"""
        self.set_pattern('blink', period=0.3, duty=0.7, count=3, next_pattern='breathing')
        
    def set_card_recognized(self):
        """Pattern for successful card recognition: quick double pulse"""
        self.set_pattern('pulse', count=2, next_pattern='solid')
        
    def set_shutdown(self):
        """Sequence for system shutdown: fade out"""
        self.set_pattern('fadeout', duration=3.0)
        
    def set_success_pattern(self, next_pattern='solid'):
        """Visual indication of successful operation"""
        self.set_pattern('success', count=1, next_pattern=next_pattern)
        
    def set_error_pattern(self, count=2, next_pattern='breathing'):
        """Visual indication of error condition"""
        self.set_pattern('error', count=count, next_pattern=next_pattern)
        
    def set_attention_pattern(self, count=1, next_pattern='breathing'):
        """Show attention-grabbing pattern for important notifications"""
        self.set_pattern('attention', count=count, next_pattern=next_pattern)
        
    def set_loading_pattern(self, duration=None):
        """Show loading/processing pattern using rainbow effect"""
        self.set_pattern('rainbow', speed=1.5)
        
    def set_card_sequence(self, is_valid=True):
        """Show appropriate pattern for card recognition
        
        Args:
            is_valid: True for valid card, False for invalid card
        """
        if is_valid:
            # Valid card pattern: quick colorshift then solid
            self.set_pattern('colorshift', 
                            levels=[30, 60, 100, 60, 30], 
                            duration=0.12, 
                            count=1, 
                            next_pattern='solid')
        else:
            # Invalid card pattern: error sequence
            self.set_pattern('colorshift', 
                            levels=[100, 0, 100, 0, 100, 0], 
                            duration=0.1, 
                            count=1, 
                            next_pattern='breathing')
    
    def set_battery_warning(self, level):
        """Show appropriate battery warning based on level
        
        Args:
            level: Battery percentage (0-100)
        """
        if level < 15:
            # Critical battery: SOS pattern
            self.set_sos(count=1, next_pattern='breathing')
        elif level < 30:
            # Low battery: double pulse repeated twice
            self.set_pattern('colorshift', 
                            levels=[100, 0, 100, 0, 0, 0], 
                            duration=0.15, 
                            count=2, 
                            next_pattern='breathing')
