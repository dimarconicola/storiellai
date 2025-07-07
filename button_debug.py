import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("Testing button wiring:")
print("- Pin 1 should be connected to GPIO 23")
print("- Pin 2 should be connected to 3.3V") 
print("- 10kΩ resistor from GPIO 23 to GND")
print("")
print("Current GPIO 23 value (should be 0 when not pressed):", GPIO.input(23))
print("Now press and HOLD the button...")

for i in range(50):  # 5 seconds
    value = GPIO.input(23)
    print(f"GPIO 23 = {value}", end="\r")
    if value == 1:
        print(f"\n✓ SUCCESS! Button press detected (value = 1)")
        break
    time.sleep(0.1)
else:
    print(f"\n❌ No button press detected. Check Pin 2 connection to 3.3V")

GPIO.cleanup()
