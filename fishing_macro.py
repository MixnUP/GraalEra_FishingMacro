import tkinter as tk
from tkinter import ttk
import pyautogui
import pydirectinput
import cv2
import numpy as np
import platform
import random
import threading
import time
from typing import Optional, Tuple
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FishingMacro:
    def __init__(self, root):
        """Initialize the fishing macro application."""
        self.root = root
        self.root.title("Fishing Macro")
        
        # State
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.click_point: Optional[Tuple[int, int]] = None
        self.character_point: Optional[Tuple[int, int]] = None
        self.character_marker_id: Optional[int] = None
        self.running: bool = False
        self.overlay = None
        self.last_afk_prevent_time: Optional[float] = None # Changed from start_time
        self.afk_prevention_interval_min = 3 * 60 # 3 minutes
        self.afk_prevention_interval_max = 5 * 60 # 5 minutes
        self.next_afk_time: Optional[float] = None
        self.timer_var = tk.StringVar(value="--:-- until next move")
        
        # Create minimal UI
        self.create_ui()
        
        # Make window stay on top and small
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
    
    def create_ui(self):
        """Create the main UI components."""
        # Main frame with minimal padding
        self.frame = ttk.Frame(self.root, padding="5")
        self.frame.pack(padx=5, pady=5)
        
        # Control buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.start_btn = ttk.Button(
            btn_frame, 
            text="Start", 
            command=self.start_macro,
            width=8,
            state=tk.DISABLED # Initially disabled
        )
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(
            btn_frame,
            text="Stop",
            command=self.stop_macro,
            state=tk.DISABLED,
            width=8
        )
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.reset_btn = ttk.Button(
            btn_frame,
            text="Reset Selection",
            command=self.setup_region,
            width=15,
            state=tk.DISABLED # Initially disabled
        )
        self.reset_btn.pack(side=tk.LEFT, padx=2)
        
        # Status label (minimal)
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(
            self.frame,
            textvariable=self.status_var,
            font=('TkDefaultFont', 10, 'bold'),
            foreground='blue'
        )
        status.pack(pady=(5, 0))

        # Timer display
        timer_label = ttk.Label(
            self.frame,
            textvariable=self.timer_var,
            font=('TkDefaultFont', 12, 'bold'),
            foreground='green'
        )
        timer_label.pack(pady=(5, 0))
        
        # Start with region selection
        self.setup_region()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        
    def setup_region(self):
        """Open a transparent overlay to select the screen region."""
        self.reset_selection() # Ensure a clean slate for new selection

        # Create overlay window
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.3)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.overlay,
            highlightthickness=0,
            cursor='cross',
            bg='black',  # Set a valid background color
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Selection state
        self.selection_start = None
        self.selection_rect_id = None
        self.click_point = None
        self.click_marker_ids = []
        self.character_point = None
        self.character_marker_id = None
        
        # Instructions
        screen_width = self.overlay.winfo_screenwidth()
        self.instruction_text = self.canvas.create_text(
            screen_width // 2, 30,
            text="1. Drag to select the fishing area.\n2. Left-click to set the bobber's click point.\n3. Right-click to set your character's position.\n4. Press Enter to confirm, or Esc to cancel.",
            fill="white",
            font=('Arial', 12, 'bold'),
            anchor='center',
            justify='center',
            tags='instruction'
        )
        
        # Bind events
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<Button-3>', self.on_right_click) # Added for character position
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.overlay.bind('<Escape>', self.cancel_selection)
        self.overlay.bind('<Return>', self.confirm_region)
        
        # Prevent interaction with main window
        self.overlay.grab_set()
        
    def on_click(self, event):
        """Handle mouse clicks for region and click point selection."""
        if self.selection_rect_id is None:
            # Start new selection
            self.selection_start = (event.x, event.y)
        else:
            # Set click point
            self.set_click_point(event.x, event.y)
    
    def on_drag(self, event):
        """Handle mouse drag for region selection."""
        if not self.selection_start:
            return
            
        x1, y1 = self.selection_start
        x2, y2 = event.x, event.y
        
        # Ensure x1 <= x2 and y1 <= y2
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Update or create selection rectangle
        if self.selection_rect_id:
            self.canvas.coords(self.selection_rect_id, x1, y1, x2, y2)
        else:
            self.selection_rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline='white',
                fill='blue',
                stipple='gray50',
                width=2,
                dash=(4, 4),
                tags='selection'
            )
    
    def on_release(self, event):
        """Finalize region selection on mouse release."""
        if not (self.selection_start and self.selection_rect_id):
            return
            
        x1, y1, x2, y2 = self.canvas.coords(self.selection_rect_id)
        
        # Ensure minimum size
        if abs(x2 - x1) < 20 or abs(y2 - y1) < 20:
            self.status_var.set("Selection too small. Please drag a larger area.")
            return
    
    def set_click_point(self, x, y):
        """Set the click point and update the marker."""
        self.click_point = (x, y)
        
        # Clear previous markers
        for marker_id in self.click_marker_ids:
            self.canvas.delete(marker_id)
        self.click_marker_ids = []
        
        # Draw crosshair
        size = 10
        self.click_marker_ids = [
            # Crosshair lines
            self.canvas.create_line(x-size, y, x+size, y, fill='lime', width=1, tags='click_point'),
            self.canvas.create_line(x, y-size, x, y+size, fill='lime', width=1, tags='click_point'),
            # Outer circle
            self.canvas.create_oval(
                x-5, y-5, x+5, y+5,
                outline='lime',
                width=1,
                tags='click_point'
            )
        ]
        
        self.status_var.set(f"Click point set at ({x}, {y}). Right-click to set character position.")

    def on_right_click(self, event):
        """Handle right-click for character position selection."""
        if self.selection_rect_id is not None:
            self.set_character_point(event.x, event.y)

    def set_character_point(self, x, y):
        """Set the character's position and update the marker."""
        self.character_point = (x, y)

        # Clear previous marker
        if self.character_marker_id:
            self.canvas.delete(self.character_marker_id)

        # Draw a square marker
        size = 7
        self.character_marker_id = self.canvas.create_rectangle(
            x - size, y - size, x + size, y + size,
            outline='red',
            fill='red',
            stipple='gray25',
            width=2,
            tags='character_point'
        )
        
        self.status_var.set(f"Character position set at ({x}, {y}). Press Enter to confirm.")
    
    def confirm_region(self, event=None):
        """Finalize the region and click point selection."""
        if not self.selection_rect_id:
            self.status_var.set("Error: Please select a fishing region first.")
            return
            
        if not self.click_point:
            self.status_var.set("Error: Please set a click point within the region.")
            return

        if not self.character_point:
            self.status_var.set("Error: Please right-click to set your character's position.")
            return
            
        # Get the final region
        x1, y1, x2, y2 = self.canvas.coords(self.selection_rect_id)
        self.region = (
            int(min(x1, x2)),  # left
            int(min(y1, y2)),  # top
            int(abs(x2 - x1)),  # width
            int(abs(y2 - y1))   # height
        )
        
        # Clear visual elements from overlay
        self.clear_overlay_elements()
        
        # Clean up overlay window
        self.cleanup_overlay()
        
        # Update status
        self.status_var.set("Ready to start")
        self.start_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.NORMAL)
    
    def clear_overlay_elements(self): 
        """Clear only the visual elements from the overlay."""
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            try:
                self.canvas.delete('selection')
                self.canvas.delete('click_point')
                self.canvas.delete('character_point')
                self.canvas.delete('instruction')
            except (tk.TclError, AttributeError):
                pass

    def reset_selection(self): 
        """Reset the current selection and its state variables."""
        self.clear_overlay_elements()
        self.selection_start = None
        self.selection_rect_id = None
        self.click_point = None
        self.click_marker_ids = []
        self.character_point = None
        self.character_marker_id = None
        self.region = None # Also reset the region
        self.status_var.set("Ready")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.DISABLED)
        # Reset timer
        self.last_afk_prevent_time = None
        self.next_afk_time = None
        self.timer_var.set("--:-- until next move")

    def cancel_selection(self, event=None):
        """Cancel the selection process and reset state."""
        self.reset_selection()
        self.cleanup_overlay()

    def cleanup_overlay(self):
        """Clean up the overlay window without resetting selection state."""
        if hasattr(self, 'overlay') and self.overlay:
            try:
                self.overlay.grab_release()
                self.overlay.destroy()
            except tk.TclError:
                pass
            self.overlay = None

    def update_timer(self):
        """Update the countdown display for the next AFK prevention move."""
        if self.running and self.next_afk_time is not None:
            remaining_seconds = int(self.next_afk_time - time.time())
            
            if remaining_seconds < 0:
                remaining_seconds = 0

            hours, remainder = divmod(remaining_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_var.set(f"{hours:02}:{minutes:02}:{seconds:02} until next move")
            
            # Schedule the next update
            self.root.after(1000, self.update_timer)
    
    def start_macro(self):
        """Start the fishing macro."""
        if not self.region or not self.click_point or not self.character_point:
            self.status_var.set("Error: All points not set. Please reset and select again.")
            return
            
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.DISABLED)
        self.status_var.set("Running...")
        
        # Start timer
        self.last_afk_prevent_time = time.time()
        
        # Start the macro in a separate thread
        self.macro_thread = threading.Thread(target=self.run_macro, daemon=True)
        self.macro_thread.start()
    
    def stop_macro(self):
        """Stop the fishing macro."""
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.NORMAL)
        self.status_var.set("Stopped")
        self.last_afk_prevent_time = None

    def prevent_afk(self):
        """Simulate intelligent, randomized movement to prevent being flagged as AFK."""
        if not self.character_point or not self.click_point:
            return

        self.root.after(0, lambda: self.status_var.set("Moving to prevent AFK..."))

        # Determine primary direction and its opposite
        char_x, char_y = self.character_point
        click_x, click_y = self.click_point
        delta_x = click_x - char_x
        delta_y = click_y - char_y

        if abs(delta_x) > abs(delta_y):  # Horizontal
            if delta_x > 0:
                facing_direction = 'right'
                opposite_direction = 'left'
            else:
                facing_direction = 'left'
                opposite_direction = 'right'
        else:  # Vertical
            if delta_y > 0:
                facing_direction = 'down'
                opposite_direction = 'up'
            else:
                facing_direction = 'up'
                opposite_direction = 'down'
        
        # Randomly choose a movement pattern
        move_patterns = [self._move_opposite, self._move_sideways]
        chosen_move = random.choice(move_patterns)

        if chosen_move == self._move_sideways:
            chosen_move(facing_direction)
        else:
            chosen_move(facing_direction, opposite_direction)

    def _move_opposite(self, facing_direction, opposite_direction):
        """Move one step opposite and immediately return, repeating 1-3 times."""
        repeat_times = random.randint(1, 3)
        for _ in range(repeat_times):
            if platform.system() == "Windows":
                pydirectinput.keyDown(opposite_direction)
                time.sleep(0.02)
                pydirectinput.keyUp(opposite_direction)
                
                pydirectinput.keyDown(facing_direction)
                time.sleep(0.02)
                pydirectinput.keyUp(facing_direction)
            else:
                pyautogui.keyDown(opposite_direction)
                time.sleep(0.02)
                pyautogui.keyUp(opposite_direction)

                pyautogui.keyDown(facing_direction)
                time.sleep(0.02)
                pyautogui.keyUp(facing_direction)

    def _move_sideways(self, facing_direction):
        """Move one step sideways and immediately return, with randomization."""
        if facing_direction in ['up', 'down']:
            side_keys = ['left', 'right']
        else:
            side_keys = ['up', 'down']
        
        random.shuffle(side_keys) # Randomize the order of movement
        side1, side2 = side_keys

        if platform.system() == "Windows":
            pydirectinput.keyDown(side1)
            time.sleep(0.02)
            pydirectinput.keyUp(side1)
            
            pydirectinput.keyDown(side2)
            time.sleep(0.02)
            pydirectinput.keyUp(side2)
        else:
            pyautogui.keyDown(side1)
            time.sleep(0.02)
            pyautogui.keyUp(side1)
            
            pyautogui.keyDown(side2)
            time.sleep(0.02)
            pyautogui.keyUp(side2)

    
    def run_macro(self):
        """Main macro loop."""
        bobber_present_templates = ['bobber.png', 'bobber2.png', 'bobber3.png', 'bobber4.png']
        bite_templates = ['capture.PNG', 'capture2.PNG', 'capture3.PNG', 'capture4.PNG', 'capture5.PNG']

        # Helper to detect any of the given templates
        def detect_any_template(screenshot, templates, confidence=0.8):
            for template_file in templates:
                try:
                    template_path = resource_path(f'assets/{template_file}')
                    template = cv2.imread(template_path)
                    if template is None:
                        continue
                        
                    # Check if template is larger than screenshot
                    if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
                        # Skip this template if it's larger than the screenshot
                        continue
                        
                    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    if max_val > confidence:
                        return True
                except Exception as e:
                    print(f"Error processing template {template_file}: {e}")
                    continue
            return False

        last_action = time.time() # Initialize last_action
        consecutive_bobber_failures = 0 # New counter for consecutive failures
        
        # Set the first random interval and next AFK time
        afk_check_interval = random.randint(self.afk_prevention_interval_min, self.afk_prevention_interval_max)
        self.next_afk_time = time.time() + afk_check_interval
        self.root.after(0, self.update_timer) # Start the UI timer

        while self.running:
            try:
                # --- AFK Prevention Check ---
                if time.time() > self.next_afk_time:
                    self.prevent_afk()
                    # Set the next random interval and AFK time
                    afk_check_interval = random.randint(self.afk_prevention_interval_min, self.afk_prevention_interval_max)
                    self.next_afk_time = time.time() + afk_check_interval
                    # After moving, it's safer to recast
                    self.root.after(0, lambda: self.status_var.set("AFK prevention done. Recasting..."))
                    continue # Skip to the next loop iteration to recast

                # --- Phase 1: Cast and wait for bobber to appear ---
                self.root.after(0, lambda: self.status_var.set("Casting..."))
                pyautogui.click(*self.click_point) # Cast
                last_action = time.time() # Update last_action after casting

                self.root.after(0, lambda: self.status_var.set("Casting... Detecting bobber."))
                bobber_found = False
                start_waiting_time = time.time()
                wait_timeout = 1 # seconds to wait for bobber

                while self.running and not bobber_found and (time.time() - start_waiting_time < wait_timeout):
                    screenshot = pyautogui.screenshot(region=self.region)
                    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    if detect_any_template(screenshot, bobber_present_templates):
                        bobber_found = True
                        break
                    time.sleep(0.05) # Small delay to prevent high CPU during waiting

                if not bobber_found:
                    consecutive_bobber_failures += 1
                    self.root.after(0, lambda: self.status_var.set(f"Bobber not detected ({consecutive_bobber_failures}/3)."))
                    if consecutive_bobber_failures >= 3:
                        # 1. Announce pause and wait 15 seconds
                        self.root.after(0, lambda: self.status_var.set("Bobber not found. Pausing for 15s..."))
                        time.sleep(15)

                        # 2. After delay, verify water position
                        self.root.after(0, lambda: self.status_var.set("Verifying water position..."))
                        screenshot = pyautogui.screenshot(region=self.region)
                        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                        water_templates = ['water.png', 'water2.png', 'water3.png']

                        # 3. Check for water
                        if detect_any_template(screenshot_cv, water_templates, confidence=0.2):
                            # 4. Water is present, continue the loop
                            self.root.after(0, lambda: self.status_var.set("Water found. Resuming fishing..."))
                            consecutive_bobber_failures = 0 # Reset for the retry
                            continue # Go to next loop iteration
                        else:
                            # 5. Water not found, this is a fatal error
                            self.root.after(0, lambda: self.status_var.set("Position Lost! No water detected."))
                            self.root.after(0, self.stop_macro)
                            break # Exit the main while loop
                    continue # Go back to the beginning of the main while loop to re-cast
                else:
                    consecutive_bobber_failures = 0 # Reset counter on success

                self.root.after(0, lambda: self.status_var.set("Bobber present. Waiting for bite..."))

                # --- Phase 2: Monitor for bite or bobber disappearance ---
                while self.running and bobber_found: # Loop while bobber is present
                    screenshot = pyautogui.screenshot(region=self.region)
                    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                    # Check for bite
                    if detect_any_template(screenshot, bite_templates):
                        if time.time() - last_action > 1.0: # Prevent rapid clicks
                            pyautogui.click(*self.click_point) # Reel in
                            time.sleep(0.2) # Delay after reeling in
                            self.root.after(0, lambda: self.status_var.set("Bite detected! Reeling in..."))
                            bobber_found = False # Bobber is now gone, exit inner loop to re-cast
                            break # Exit inner loop to go back to casting phase
                    else:
                        # If no bite, check if bobber is still present
                        if not detect_any_template(screenshot, bobber_present_templates, confidence=0.7): # Lower confidence for presence check
                            consecutive_bobber_failures += 1
                            self.root.after(0, lambda: self.status_var.set(f"Bobber disappeared ({consecutive_bobber_failures}/3)."))
                            bobber_found = False # Bobber is gone, exit inner loop to re-cast
                            if consecutive_bobber_failures >= 3:
                                # 1. Announce pause and wait 15 seconds
                                self.root.after(0, lambda: self.status_var.set("Bobber disappeared. Pausing for 15s..."))
                                time.sleep(15)

                                # 2. After delay, verify water position
                                self.root.after(0, lambda: self.status_var.set("Verifying water position..."))
                                screenshot_after_delay = pyautogui.screenshot(region=self.region)
                                screenshot_cv = cv2.cvtColor(np.array(screenshot_after_delay), cv2.COLOR_RGB2BGR)
                                water_templates = ['water.png', 'water2.png', 'water3.png']

                                # 3. Check for water
                                if detect_any_template(screenshot_cv, water_templates, confidence=0.5):
                                    # 4. Water is present, continue the loop
                                    self.root.after(0, lambda: self.status_var.set("Water found. Resuming fishing..."))
                                    consecutive_bobber_failures = 0 # Reset for the retry
                                    break # Exit inner loop to go back to casting phase
                                else:
                                    # 5. Water not found, this is a fatal error
                                    self.root.after(0, lambda: self.status_var.set("Position Lost! No water detected."))
                                    self.root.after(0, self.stop_macro)
                                    break # Exit the main while loop
                            break # Exit inner loop to go back to casting phase
                        else:
                            consecutive_bobber_failures = 0 # Reset counter on success

                    # No explicit sleep here to keep it fast, as requested.
                    # The screenshot and image processing provide some natural delay.

            except Exception as e:
                print(f"Error in macro: {e}")
                time.sleep(1) # Sleep on error to prevent rapid error logging

        # Clean up when stopped
        self.root.after(0, self.stop_macro)

def main():
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = FishingMacro(root)
        
        # Set window position (top-right corner)
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = root.winfo_screenwidth() - width - 20
        y = 20
        root.geometry(f'+{x}+{y}')
        
        # Start the application
        root.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
