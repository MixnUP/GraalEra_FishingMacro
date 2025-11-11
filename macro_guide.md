# Macro System Design Guide

## Overview
This document defines the design and behavior of a **minimal fishing macro system** that automates casting and reeling actions using computer vision.

The macro observes a defined region of the screen, detects when `capture.png` appears, and performs mouse clicks at a specified location for both **cast** and **reel** actions. The process loops indefinitely.

---

## System Phases

### 1. Setup Phase
**Purpose:** Let the user define the vision region and click point.

**Behavior:**
- Display a transparent overlay rectangle.
- The overlay region can be **dragged and resized** by the user to define the vision area.
- A **click marker** (small visible circle) can be placed by **clicking once** inside the region.
- A small always-on-top UI window appears with two buttons:
  - `Start`
  - `Stop`

**UI Rules:**
- No additional controls or text fields.
- Minimal, clean, and centered layout.
- Overlay border visible (semi-transparent or outlined).

---

### 2. Running Phase
**Purpose:** Automatically handle casting and reeling using vision detection.

**Flow:**
> Cast → Wait for `capture.png` → Reel → Cast → Repeat indefinitely

**Behavior Details:**
- On `Start` click:
  - Perform one mouse click at the defined click point (initial **cast**).
  - Begin scanning within the selected region continuously.
- If `capture.png` is detected within the region:
  - Perform one mouse click (**reel**).
  - Immediately perform another mouse click (**cast**).
  - Continue looping.

**Detection:**
- Use `opencv-python` (`cv2`) for image recognition.
- Match templates (`capture.png`) against the current screenshot of the defined region.
- Tolerance or confidence threshold ≈ 0.8–0.9.

**Performance Notes:**
- Keep frame rate moderate (1–3 checks/sec).
- Avoid excessive CPU use by sleeping briefly per loop iteration.
- Run detection in a separate thread to prevent UI freeze.

---

### 3. Stop Phase
**Purpose:** Halt macro operation.

**Behavior:**
- Clicking `Stop` immediately ends the detection loop.
- Optionally, restore the overlay for region/click adjustment.

---

## Implementation Notes

### Required Libraries
- `tkinter` – base GUI and overlay system
- `pyautogui` – mouse click and screenshot utilities
- `opencv-python` – image matching for vision detection
- `threading` – background loop execution
- `time` – loop timing and brief sleeps

### Threading Model
- **Main Thread:** Handles UI + overlay events.
- **Worker Thread:** Runs continuous vision detection and auto-click loop.

### Overlay Interaction
- Implement using a border-only `tkinter.Toplevel` window with transparency.
- Support click-to-set marker and edge resizing via event bindings.
- Store the region (x, y, width, height) and click coordinates globally.

### Click Behavior
- Both **cast** and **reel** actions use the same click point.
- Triggered by vision event only (no fixed delays).

### Loop Pseudocode
```python
while running:
    region_img = capture(region)
    if detect(capture.png in region_img):
        click(click_point)  # reel
        click(click_point)  # cast
    time.sleep(0.3)
```

---

## Safety & Stability
- Ensure `Stop` safely terminates threads.
- Add try/except around vision and automation routines.
- Use small sleeps (e.g., 0.2–0.3s) to prevent 100% CPU usage.

---

## Summary
This macro runs in three main phases:

> **Setup:** Adjust region + set click point → press Start  
> **Running:** Detect `capture.png` → click (reel) → click (cast) → repeat  
> **Stop:** Terminate loop cleanly

Keep UI minimal and logic reactive — no fixed delays, no unnecessary options.
