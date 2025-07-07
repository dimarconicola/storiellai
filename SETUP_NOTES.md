# Storyteller Box - Quick Setup Notes

## 🚀 COPY-PASTE SETUP FOR FRESH RASPBERRY PI

```bash
# 1. Update and install packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-pip python3-pygame libasound2-dev python3-dev libgpiod2

# 2. Enable SPI (for NFC and ADC)
sudo raspi-config nonint do_spi 0

# 3. Clone and setup project
cd /home/pi
git clone https://github.com/dimarconicola/storiellai.git
cd storiellai
pip3 install -r requirements.txt --break-system-packages

# 4. Test in mock mode (safe)
cd src
python3 box.py  # Ctrl+C to stop

# 5. Enable real hardware mode (after wiring)
cd hardware
sed -i 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' hal.py

# 6. Setup auto-start service
cd /home/pi/storiellai
sudo cp systemd/storyteller.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable storyteller.service
sudo systemctl start storyteller.service
```

## 🔧 MOCK vs REAL HARDWARE

### Check current mode:
```bash
cd /home/pi/storiellai/src/hardware
grep "IS_RASPBERRY_PI" hal.py
```

### Switch to mock mode (development/testing):
```bash
sed -i 's/IS_RASPBERRY_PI = True/IS_RASPBERRY_PI = False/' hal.py
```

### Switch to real hardware mode:
```bash
sed -i 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' hal.py
```

## 🔴 4-PIN BUTTON WIRING (GPIO 23 + 24)

```
LED wiring:  Pi GPIO 24 → 330Ω resistor → Button LED+ pin
             Button LED- pin → Pi GND

Button wiring: Pi GPIO 23 → Button pin
               Other button pin → Pi GND
```

### Quick button/LED test:
```bash
# Test LED (GPIO 24)
echo "24" > /sys/class/gpio/export
echo "out" > /sys/class/gpio/gpio24/direction
echo "1" > /sys/class/gpio/gpio24/value  # LED on
echo "0" > /sys/class/gpio/gpio24/value  # LED off
echo "24" > /sys/class/gpio/unexport

# Test button (GPIO 23)
echo "23" > /sys/class/gpio/export
echo "in" > /sys/class/gpio/gpio23/direction
watch -n 0.1 'cat /sys/class/gpio/gpio23/value'  # Press button
echo "23" > /sys/class/gpio/unexport
```

## 🔍 TROUBLESHOOTING COMMANDS

```bash
# Check service status
sudo systemctl status storyteller.service

# View service logs
journalctl -u storyteller.service -f

# Check application logs
cd /home/pi/storiellai/src
cat storyteller.log

# Test mock mode
cd /home/pi/storiellai/src/hardware
sed -i 's/IS_RASPBERRY_PI = True/IS_RASPBERRY_PI = False/' hal.py
cd ../
python3 box.py

# Re-enable real hardware
cd hardware
sed -i 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' hal.py
```

## 🚨 COMMON ISSUES

1. **"externally-managed-environment" error**: Add `--break-system-packages` to pip commands
2. **LED not working**: Check polarity (LED+ via resistor to GPIO 24, LED- to GND)
3. **Button not responding**: Try swapping the two button pin connections
4. **Mock mode confusion**: Always check `grep "IS_RASPBERRY_PI" hal.py` first
5. **Service not starting**: Check paths in `/etc/systemd/system/storyteller.service`

## 📋 HARDWARE CHECKLIST

- [ ] PN532 NFC reader connected via SPI
- [ ] 4-pin LED button: LED via 330Ω resistor to GPIO 24, button to GPIO 23
- [ ] MCP3008 ADC for volume control and battery monitoring
- [ ] Speaker + PAM8302A amplifier
- [ ] All GND connections shared
- [ ] SPI enabled in raspi-config
- [ ] All components powered appropriately (3.3V vs 5V)
