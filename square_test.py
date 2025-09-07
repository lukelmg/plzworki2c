from drivebase import XDrive
import time

def main():
    # Initialize the XDrive
    robot = XDrive()
    
    # Function to drive in one direction for a specific time
    def drive_segment(x: float, y: float, duration: float):
        robot.drive(x, y, 0)  # No heading correction for this simple test
        time.sleep(duration)
        robot.drive(0, 0, 0)  # Stop
        time.sleep(0.5)  # Small pause between movements
    
    # Drive in a square pattern:
    # Forward, Right, Backward, Left
    try:
        while True:
            # Forward
            speed = 80

            print("Moving forward...")
            drive_segment(0, speed, 2)

            # Right
            print("Moving right...")
            drive_segment(speed, 0, 2)
            
            # Backward
            print("Moving backward...")
            drive_segment(0, -speed, 2)
            
            # Left
            print("Moving left...")
            drive_segment(-speed, 0, 2)

            print("Square complete! Starting again...")
            time.sleep(1)  # Pause before next square
            
    except KeyboardInterrupt:
        # Stop the robot when Ctrl+C is pressed
        print("\nStopping robot...")
        robot.drive(0, 0, 0)

if __name__ == "__main__":
    main()
