from drivebase import XDrive
import time

def main():
    # Initialize the XDrive without any direction overrides
    robot = XDrive()
    
    def test_motor(name: str, motor, power: int = 30, duration: float = 2.0):
        print(f"\nTesting {name} motor:")
        print(f"PWM Channel: {motor.pwm_ch}")
        print(f"Direction Channel: {motor.dir_ch}")
        print(f"Current direction value: {motor.direction}")
        print(f"Running at {power}% power for {duration} seconds...")
        
        motor.set_power(power)
        time.sleep(duration)
        motor.set_power(0)
        time.sleep(0.5)
        
        # Test reverse direction
        print(f"Running at {-power}% power (reverse) for {duration} seconds...")
        motor.set_power(-power)
        time.sleep(duration)
        motor.set_power(0)
        time.sleep(1)

    try:
        while True:
            print("\n=== Motor Testing Menu ===")
            print("1: Test Back Left Motor")
            print("2: Test Front Left Motor")
            print("3: Test Back Right Motor")
            print("4: Test Front Right Motor")
            print("5: Test All Motors Forward")
            print("6: Test All Motors Backward")
            print("q: Quit")
            
            choice = input("\nEnter your choice (1-6, q): ")
            
            if choice == 'q':
                break
                
            power = 30  # Default power level - adjust if needed
            duration = 2.0  # Default duration - adjust if needed
                
            if choice == '1':
                test_motor("Back Left", robot.BackLeft, power, duration)
            elif choice == '2':
                test_motor("Front Left", robot.FrontLeft, power, duration)
            elif choice == '3':
                test_motor("Back Right", robot.BackRight, power, duration)
            elif choice == '4':
                test_motor("Front Right", robot.FrontRight, power, duration)
            elif choice == '5':
                print("\nRunning all motors forward...")
                for motor in robot._motors:
                    motor.set_power(power)
                time.sleep(duration)
                for motor in robot._motors:
                    motor.set_power(0)
            elif choice == '6':
                print("\nRunning all motors backward...")
                for motor in robot._motors:
                    motor.set_power(-power)
                time.sleep(duration)
                for motor in robot._motors:
                    motor.set_power(0)
            else:
                print("\nInvalid choice. Please try again.")
            
            print("\nTest complete. Motors stopped.")
            time.sleep(1)

    except KeyboardInterrupt:
        # Stop all motors when Ctrl+C is pressed
        print("\nStopping all motors...")
        for motor in robot._motors:
            motor.set_power(0)

if __name__ == "__main__":
    main()
