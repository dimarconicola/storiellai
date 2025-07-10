import board
import busio
from adafruit_pn532.i2c import PN532_I2C

i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)

firmware_version = pn532.firmware_version
if firmware_version:
    print("PN532 detected! Firmware version:", [hex(i) for i in firmware_version])
else:
    print("PN532 NOT detected. Check wiring and power.")
