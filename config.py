import os
import sys

# Tesseract configuration
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# OCR Languages (change as needed)
OCR_LANG = 'rus+eng'

# Application settings
APP_NAME = 'Screen Text Capture'
ICON_SIZE = (64, 64)

# UI Settings
SELECTION_OVERLAY_ALPHA = 0.3
SELECTION_LINE_COLOR = 'red'
SELECTION_LINE_WIDTH = 2

# OCR Delay (in seconds) - time to wait after action before capturing OCR
OCR_DELAY = 3.5

# Random delay bounds (in seconds) - random delay before executing next action
RANDOM_DELAY_MIN = 3
RANDOM_DELAY_MAX = 8

# Click delay bounds (in seconds) - time between mouse/key press and release
CLICK_DELAY_MIN = 0.040  # 40 milliseconds
CLICK_DELAY_MAX = 0.060  # 60 milliseconds

# Mouse movement speed bounds (in seconds) - duration for mouse movements
MOUSE_SPEED_MIN = 0.15
MOUSE_SPEED_MAX = 0.25

# Settings file path
SETTINGS_FILE = 'polisher_settings.json'

# Statistics file path
STATISTICS_FILE = 'polisher_statistics.jsonl'

def configure_tesseract():
    """Configure tesseract path if on Windows"""
    if sys.platform == 'win32' and os.path.exists(TESSERACT_CMD):
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
