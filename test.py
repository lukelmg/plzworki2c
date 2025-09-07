from smbus2 import SMBus
import time

# ---- PCA9685 low-level helpers ----
MODE1 = 0x00
MODE2 = 0x01
LED0_ON_L = 0x06
PRE_SCALE = 0xFE

# MODE1 bits
RESTART = 0x80
SLEEP = 0x10
AI = 0x20  # Auto-increment

# MODE2 bits
OUTDRV = 0x04  # Totem pole


def find_pca_addr(bus, candidates=(0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x31)):
    for addr in candidates:
        try:
            bus.read_byte_data(addr, MODE1)
            return addr
        except Exception:
            continue
    raise RuntimeError("PCA9685 not found on I2C bus among addresses 0x40-0x47")


# Initialize I2C bus (usually bus 1 on Raspberry Pi and many SBCs)
bus = SMBus(1)
PCA_ADDR = find_pca_addr(bus)


def set_mode_defaults():
    """Set MODE1/2 for normal operation and push-pull outputs."""
    oldmode = bus.read_byte_data(PCA_ADDR, MODE1)
    # Go to sleep to safely change prescaler later if needed
    bus.write_byte_data(PCA_ADDR, MODE1, (oldmode & ~RESTART) | SLEEP)
    # MODE2 push-pull, non-inverted
    bus.write_byte_data(PCA_ADDR, MODE2, OUTDRV)
    # MODE1: enable auto-increment, keep sleep for now
    bus.write_byte_data(PCA_ADDR, MODE1, (oldmode & ~RESTART) | SLEEP | AI)


def set_pwm_freq(freq_hz: int):
    """Set PWM frequency (approx up to ~1526 Hz)."""
    prescaleval = 25000000.0 / (4096.0 * float(freq_hz)) - 1.0
    prescale = int(prescaleval + 0.5)
    oldmode = bus.read_byte_data(PCA_ADDR, MODE1)
    bus.write_byte_data(PCA_ADDR, MODE1, (oldmode & ~RESTART) | SLEEP | AI)
    bus.write_byte_data(PCA_ADDR, PRE_SCALE, prescale)
    # Wake up
    bus.write_byte_data(PCA_ADDR, MODE1, (oldmode & ~SLEEP) | AI)
    time.sleep(0.005)
    # Restart
    bus.write_byte_data(PCA_ADDR, MODE1, ((oldmode & ~SLEEP) | RESTART | AI) & 0xFF)


def _write_channel_raw(ch: int, on: int, off: int):
    base = LED0_ON_L + 4 * ch
    bus.write_byte_data(PCA_ADDR, base + 0, on & 0xFF)
    bus.write_byte_data(PCA_ADDR, base + 1, (on >> 8) & 0x0F)
    bus.write_byte_data(PCA_ADDR, base + 2, off & 0xFF)
    bus.write_byte_data(PCA_ADDR, base + 3, (off >> 8) & 0x0F)


def set_channel_pwm(ch: int, duty: int):
    """Set a channel's PWM duty 0..4095. 0=full off, 4095=full on."""
    duty = max(0, min(4095, int(duty)))
    if duty <= 0:
        # Full off: set OFF full-bit
        base = LED0_ON_L + 4 * ch
        bus.write_byte_data(PCA_ADDR, base + 0, 0)
        bus.write_byte_data(PCA_ADDR, base + 1, 0)
        bus.write_byte_data(PCA_ADDR, base + 2, 0)
        bus.write_byte_data(PCA_ADDR, base + 3, 0x10)  # FULL-OFF
    elif duty >= 4095:
        # Full on: set ON full-bit
        base = LED0_ON_L + 4 * ch
        bus.write_byte_data(PCA_ADDR, base + 0, 0)
        bus.write_byte_data(PCA_ADDR, base + 1, 0x10)  # FULL-ON
        bus.write_byte_data(PCA_ADDR, base + 2, 0)
        bus.write_byte_data(PCA_ADDR, base + 3, 0)
    else:
        _write_channel_raw(ch, 0, duty)


def set_channel_digital(ch: int, high: bool):
    """Drive a channel as a digital pin using full-on/full-off bits."""
    set_channel_pwm(ch, 4095 if high else 0)


# ---- Motor mapping per your wiring ----
# pca9685:
# port 0: motor 1 pwm
# port 1: motor 2 pwm
# port 2: motor 1 direction
# port 3: motor 2 direction
# port 15: motor 4 pwm
# port 14: motor 3 pwm
# port 13: motor 4 direction
# port 12: motor 3 direction
MOTORS = {
    1: {"pwm": 0, "dir": 2},
    2: {"pwm": 1, "dir": 3},
    3: {"pwm": 14, "dir": 12},
    4: {"pwm": 15, "dir": 13},
}


def motor_set_percent(motor: int, percent: int):
    """
    Set motor speed with signed percent [-100..100].
    Negative = reverse, positive = forward, 0 = stop.
    """
    if motor not in MOTORS:
        raise ValueError(f"Unknown motor {motor}")
    percent = max(-100, min(100, int(percent)))
    ch_pwm = MOTORS[motor]["pwm"]
    ch_dir = MOTORS[motor]["dir"]

    if percent == 0:
        set_channel_pwm(ch_pwm, 0)
        return

    forward = percent > 0
    set_channel_digital(ch_dir, forward)
    duty = int(abs(percent) * 4095 / 100)
    set_channel_pwm(ch_pwm, duty)


def all_stop():
    for m in MOTORS:
        motor_set_percent(m, 0)


def initialize(f_pwm_hz: int = 1000):
    print(f"Configuring PCA9685 at 0x{PCA_ADDR:02X}")
    set_mode_defaults()
    set_pwm_freq(f_pwm_hz)
    # Default all direction low and PWM off
    for m in MOTORS.values():
        set_channel_digital(m["dir"], False)
        set_channel_pwm(m["pwm"], 0)
    time.sleep(0.05)
    # Debug: confirm awake and prescale
    mode1 = bus.read_byte_data(PCA_ADDR, MODE1)
    pres = bus.read_byte_data(PCA_ADDR, PRE_SCALE)
    print(f"MODE1=0x{mode1:02X} (SLEEP bit should be 0), PRESCALE=0x{pres:02X}")


if __name__ == "__main__":
    # Use a higher PWM freq for DC motors (audible-range avoidance)
    initialize(1000)

    print("Testing each motor forward 50% for 2s, then reverse 50% for 2s...")
    for i in range(1, 5):
        print(f"Motor {i}: forward")
        motor_set_percent(i, 50)
        time.sleep(2)
        print(f"Motor {i}: reverse")
        motor_set_percent(i, -50)
        time.sleep(2)
        motor_set_percent(i, 0)
        time.sleep(0.5)

    print("All stop")
    all_stop()