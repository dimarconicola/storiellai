import board
import busio
import digitalio
from adafruit_pn532.spi import PN532_SPI

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs_pin = digitalio.DigitalInOut(board.D8)  # GPIO8 (Pin 24)
pn532 = PN532_SPI(spi, cs_pin, debug=False)

firmware_version = pn532.firmware_version
if firmware_version:
    print("PN532 detected! Firmware version:", [hex(i) for i in firmware_version])
else:
    print("PN532 NOT detected. Check wiring and power.")
