"""
Drivebase module using the existing SMBus/PCA9685 I2C helper code from test.py.

Provides:
- Motor: simple signed-percent control (-100..100) using one PWM channel and one direction channel on the PCA9685.
- XDrive: convenience wrapper for a 4-motor X-drive with named wheels and a drive(x, y, heading_correction) helper.

This reuses the low-level I2C/PCA9685 functions already present in test.py (no Adafruit library).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable, Tuple

# Lazy accessors to the existing I2C + PCA9685 helpers defined in test.py.
# This avoids import-time failures on dev hosts without smbus2; actual hardware
# calls will import on-demand.
_ll_cache: Optional[Tuple[Callable, Callable, Callable]] = None


def _get_lowlevel() -> Tuple[Callable, Callable, Callable]:
    global _ll_cache
    if _ll_cache is None:
        try:
            from test import (
                set_channel_pwm,
                set_channel_digital,
                initialize as pca_initialize,
            )
        except Exception as e:  # pragma: no cover - useful error message
            raise ImportError(
                "drivebase.py requires I2C/PCA9685 helpers from test.py; "
                "ensure test.py is present and its dependencies (e.g., smbus2) are installed"
            ) from e
        _ll_cache = (set_channel_pwm, set_channel_digital, pca_initialize)
    return _ll_cache


@dataclass
class Motor:
    """
    One motor driven by the PCA9685: one PWM channel for speed and one channel as a digital dir pin.

    - pwm_ch: PCA9685 channel index for PWM (0..15)
    - dir_ch: PCA9685 channel index for direction (0..15)
    - direction: +1 or -1 to flip motor polarity so that positive commands move the robot forward
    - max_percent: safety limit on output magnitude (default 40%)
    - deadband: percent within which command is treated as 0 (default 2%)
    """

    pwm_ch: int
    dir_ch: int
    direction: int = 1
    max_percent: int = 40
    deadband: int = 2

    def set_power(self, power: float | int) -> None:
        """Set motor power as signed percent [-100..100]."""
        set_channel_pwm, set_channel_digital, _ = _get_lowlevel()
        # Signed command with polarity
        try:
            cmd = float(power)
        except Exception:
            raise ValueError("power must be a number")

        effective = cmd * (1 if self.direction >= 0 else -1)

        # Direction bit: True = forward, False = reverse
        forward = effective >= 0
        set_channel_digital(self.dir_ch, forward)

        # Scale magnitude with deadband and safety cap
        magnitude = abs(effective)
        if magnitude <= self.deadband:
            # Stop
            set_channel_pwm(self.pwm_ch, 0)
            return

        magnitude = min(self.max_percent, magnitude)
        # Map 0..100% -> 0..4095 duty
        duty = int((magnitude / 100.0) * 4095)
        set_channel_pwm(self.pwm_ch, duty)

    # Optional camelCase alias for compatibility with example
    def setPower(self, power: float | int) -> None:
        self.set_power(power)

    @staticmethod
    def percentage_to_12bit(percentage: float | int) -> int:
        """Utility to convert 0..100 to 0..4095 (not used by default)."""
        p = max(0.0, min(100.0, float(percentage)))
        return int((p / 100.0) * 4095)


class XDrive:
    """
    4-motor X-drive using the PCA9685 for both PWM and direction.

    Wheels are named BackLeft, FrontLeft, BackRight, FrontRight.
    Use drive(x, y, heading_correction) with x=strafe, y=forward.
    """

    def __init__(
        self,
        initialize_hw: bool = True,
        pwm_frequency_hz: int = 1000,
        motor_directions: Optional[dict[str, int]] = None,
    ) -> None:
        """
        initialize_hw: if True, configures PCA9685 and zeros outputs
        pwm_frequency_hz: recommended 500-1000Hz for DC motors
        motor_directions: optional overrides for motor polarity by name
        """
        if initialize_hw:
            # Configure PCA9685, set frequency, zero outputs/dirs per test.initialize
            _, _, pca_initialize = _get_lowlevel()
            pca_initialize(pwm_frequency_hz)

        # Default polarities to match the user's original example
        default_dirs = {
            "BackLeft": 1,      # Updated for swapped position
            "FrontLeft": 1,     # Updated for correct direction
            "BackRight": -1,    # Unchanged
            "FrontRight": -1,   # Updated for correct direction
        }
        if motor_directions:
            default_dirs.update(motor_directions)

        # Updated channel mapping:
        # pca9685:
        # 1: BL pwm, 3: BL dir  (swapped)
        # 0: FL pwm, 2: FL dir  (swapped)
        # 14: BR pwm, 13: BR dir
        # 15: FR pwm, 12: FR dir
        self.BackLeft = Motor(pwm_ch=1, dir_ch=3, direction=default_dirs["BackLeft"])  
        self.FrontLeft = Motor(pwm_ch=0, dir_ch=2, direction=default_dirs["FrontLeft"])  
        self.BackRight = Motor(pwm_ch=14, dir_ch=13, direction=default_dirs["BackRight"])  
        self.FrontRight = Motor(pwm_ch=15, dir_ch=12, direction=default_dirs["FrontRight"])  

        self._motors = [self.BackLeft, self.FrontLeft, self.BackRight, self.FrontRight]

    def setPower(
        self,
        backLeftPower: float | int,
        frontLeftPower: float | int,
        backRightPower: float | int,
        frontRightPower: float | int,
    ) -> None:
        self.BackLeft.set_power(backLeftPower)
        self.FrontLeft.set_power(frontLeftPower)
        self.BackRight.set_power(backRightPower)
        self.FrontRight.set_power(frontRightPower)

    def drive(self, x: float | int, y: float | int, heading_correction: float | int) -> None:
        # Same math as the example
        bl = y - x - heading_correction
        fl = y + x + heading_correction
        br = y + x - heading_correction
        fr = y - x + heading_correction
        self.setPower(bl, fl, br, fr)

    def all_stop(self) -> None:
        for m in self._motors:
            m.set_power(0)

    def cleanup(self) -> None:
        """Stop all motors and set direction lines low."""
        set_channel_pwm, set_channel_digital, _ = _get_lowlevel()
        # Zero PWM on all channels
        for ch in range(16):
            try:
                set_channel_pwm(ch, 0)
            except Exception:
                pass
        # Drive known dir channels low
        for ch in (2, 3, 12, 13):
            try:
                set_channel_digital(ch, False)
            except Exception:
                pass


__all__ = ["Motor", "XDrive"]
