# rfid_test_read.py
"""
Simple script to test RFID card reading on Raspberry Pi.
Continuously reads and prints UID and text from any card tapped.
"""
import time
from src.hardware.hal import UIDReader

if __name__ == "__main__":
    reader = UIDReader()
    print("[RFID TEST] Place a card near the reader...")
    try:
        while True:
            uid, text = reader.read()
            if uid:
                print(f"[RFID] UID: {uid} | Text: {text}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[RFID TEST] Stopped.")
        reader.cleanup()
