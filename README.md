# Fishing Macro

A simple GUI-based automation tool for a fishing mini-game. It uses image recognition to detect when to reel in a fish and includes features to prevent AFK detection.

## Features

- Simple GUI for easy setup and control.
- Automated casting and reeling in using image recognition.
- Intelligent anti-AFK mechanism with randomized movements and timing.
- UI countdown timer for the next anti-AFK action.
- Safety stop that automatically halts the macro if the character's position is lost.
- Cross-platform support for Windows and Linux.

## How to Run

There are two ways to run the application.

### Option 1: Using the Executable (Recommended)

This is the simplest method. The executable file includes all necessary dependencies.

1.  Navigate to the `dist/` folder.
2.  Run the `FishingMacro.exe` file on Windows.

### Option 2: Running from Source

This method is for users who want to view or modify the code.

1.  **Prerequisites:**
    - Python 3.8+ installed.
    - (For Linux) Ensure `tkinter` and `scrot` are installed:
      ```sh
      sudo apt-get update
      sudo apt-get install python3-tk scrot
      ```

2.  **Setup:**
    - Clone or download the project files.
    - Open a terminal in the project directory.
    - Create and activate a virtual environment (recommended):
      ```sh
      python -m venv venv
      # On Windows
      .\venv\Scripts\activate
      # On Linux/macOS
      source venv/bin/activate
      ```
    - Install the required Python libraries:
      ```sh
      pip install -r requirements.txt
      ```

3.  **Run:**
    - Execute the main script:
      ```sh
      python fishing_macro.py
      ```

## How to Build the Executable

You can package the script into a single executable file using `PyInstaller`.

### Prerequisites

1. **Install Required Packages:**
   ```sh
   pip install pyinstaller pyautogui pydirectinput opencv-python numpy Pillow mss pynput
   ```

### Building the Executable

1. **Using the Provided Spec File:**
   ```sh
   pyinstaller --clean --noconfirm FishingMacro.spec
   ```

2. **Alternative: Generate a New Spec File (if needed):**
   ```sh
   pyinstaller --name FishingMacro --onefile --windowed --add-data "assets;assets" fishing_macro.py
   ```

### Troubleshooting

#### Common Issues and Solutions:

1. **Permission Errors:**
   - Close any running instances of the application
   - Run the command prompt as Administrator
   - Temporarily disable your antivirus software

2. **Missing Dependencies:**
   Ensure all required packages are installed:
   ```sh
   pip install -r requirements.txt
   ```

3. **Build Cleanup:**
   If you encounter issues, clean the build directories:
   ```sh
   # On Windows
   rmdir /s /q build dist
   # On Linux/macOS
   rm -rf build dist
   ```

### Finding the Executable
- The final executable will be located in the `dist/` folder.
- On Windows, look for `FishingMacro/FishingMacro.exe`
- The application will create a `logs` directory for error logging

### Note for Development
- The `FishingMacro.spec` file contains all build configurations
- To modify build settings, edit the spec file and rebuild
