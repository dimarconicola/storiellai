"""
LED utilities for the Storyteller Box.
Manages LED feedback patterns (solid, blink, breathing) for visual feedback.
"""

import time
import math


class LedPatternManager:
    """
    Manages LED feedback patterns (solid, blink, breathing) for the button LED.
    Call update() frequently from the main loop to keep the pattern smooth.
    """
    def __init__(self, button):
        self.button = button
        self.pattern = 'solid'  # solid, off, blink, breathing
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

    def set_pattern(self, pattern, **kwargs):
        """
        Set LED pattern with optional parameters.
        
        Args:
            pattern (str): Pattern type ('solid', 'off', 'blink', 'breathing')
            **kwargs: Pattern-specific parameters
        """
        self.pattern = pattern
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
            self.last_update = time.monotonic()
            self.blink_on = False
            self.button.set_led(False)
            self.button.stop_led_pwm()
        elif pattern == 'breathing':
            self.breathing_period = kwargs.get('period', 2.5)
            self.button.start_led_pwm(0)
            self._last_breath = time.monotonic()
        else:
            self.button.set_led(False)
            self.button.stop_led_pwm()

    def update(self):
        """Update LED pattern state - call this frequently from main loop"""
        now = time.monotonic()
        if self.pattern == 'solid':
            self.button.set_led(self.solid_state)
        elif self.pattern == 'off':
            self.button.set_led(False)
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
        else:
            self.button.set_led(False)
