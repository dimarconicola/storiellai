#!/usr/bin/env python3
"""
Phase 1: Simple LED Test
Goal: Verify Pi GPIO output works before testing integrated components
"""

import sys
import os
if os.environ.get("STORYTELLER_PI", "False").lower() != "true":
    import pytest
    pytest.skip("Skipping GPIO test on non-Pi systems", allow_module_level=True)

import RPi.GPIO as GPIO
import time

LED_PIN = 24

def test_led():
    print("🔴 Phase 1: Simple LED Test")
    print("=" * 50)
    print("Goal: Verify GPIO 24 can control an external LED")
    print()
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_PIN, GPIO.OUT)
        
        print("Testing LED on GPIO 24...")
        print("You should see the LED blink 5 times")
        print()
        
        # Blink LED 5 times
        for i in range(5):
            print(f"LED ON  (blink {i+1}/5)")
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.5)
            
            print(f"LED OFF (blink {i+1}/5)")
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.5)
        
        print()
        print("✅ LED test completed!")
        print("If you saw the LED blink 5 times, Phase 1 is successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error during LED test: {e}")
        return False
        
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    print("Make sure you have:")
    print("- LED connected to GPIO 24 (pin 18)")
    print("- 220Ω resistor in series with LED")
    print("- LED cathode (short leg) to GND")
    print("- LED anode (long leg) to resistor to GPIO 24")
    print()
    
    input("Press Enter when LED is connected and Pi is powered on...")
    
    success = test_led()
    
    if success:
        print()
        print("🎉 Phase 1 Complete! Ready for Phase 2 (4-pin button)")
        sys.exit(0)
    else:
        print()
        print("🔧 Phase 1 Failed. Check wiring and try again.")
        sys.exit(1)
