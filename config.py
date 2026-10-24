"""
Configuration settings for Minecraft YouTube Shorts AI Pipeline
"""
import os
import tempfile
from pathlib import Path

# Base Paths
BASE_DIR = Path(r"D:\Youtube\Minecraft")

def _get_safe_dir(preferred: Path, fallback_subdir: str) -> Path:
    """Checks if directory is writable; falls back to system temp if permissions are restricted."""
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".probe"
        probe.touch()
        probe.unlink()
        return preferred
    except Exception:
        fb = Path(tempfile.gettempdir()) / fallback_subdir
        fb.mkdir(parents=True, exist_ok=True)
        return fb

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = _get_safe_dir(BASE_DIR / "output", "minecraft_shorts_output")
TEMP_DIR = _get_safe_dir(BASE_DIR / "temp", "minecraft_shorts_temp")

# AI & API Configuration
# Put your Gemini API Key here or set GEMINI_API_KEY environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Default Gemini Model for Multimodal / Content Analysis
GEMINI_MODEL = "gemini-2.5-flash"

# Video Processing Settings
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 60
USE_NVENC = True  # Uses NVIDIA GPU (GTX 1650) for fast NVENC encoding

# Layout Mode:
# 'blur_background' = Center 16:9 gameplay with blurred enlarged background (Gaming meta style)
# 'center_crop'     = Direct 9:16 vertical crop focused on the Minecraft crosshair/action
DEFAULT_LAYOUT_MODE = "blur_background"

# Color Grading Preset (Optimized for Minecraft visual vibrance on mobile screens)
ENABLE_COLOR_GRADING = True
COLOR_SATURATION = 1.25   # +25% saturation for vibrant blocks & armor
COLOR_CONTRAST = 1.14     # +14% contrast for punchy shadows
COLOR_BRIGHTNESS = 0.02   # Slight lift
ENABLE_SHARPENING = True  # Crisp unsharp filter for pixel-perfect block edges

# Shorts Duration Settings (Optimized for new channels & maximum retention)
TARGET_SHORT_DURATION = 30.0   # Target short duration around 30 seconds
MIN_SHORT_DURATION = 22.0      # Minimum duration threshold
MAX_SHORT_DURATION = 33.0      # Maximum duration threshold (prevents drop-off)

# Hook Teaser Settings (First 3.5 seconds retention booster)
ENABLE_HOOK_TEASER = True
HOOK_DURATION_SEC = 3.5   # 3.5 seconds climax teaser (increased for better retention)
HOOK_TEXT_TEMPLATE = "WAIT FOR THE END! 💀"

# Subtitle (Captions) Settings - MrBeast / Hormozi Style
ENABLE_SUBTITLES = True
SUBTITLE_FONT = "Arial"
SUBTITLE_FONT_SIZE = 40                 # Large, punchy mobile-readable font size
SUBTITLE_PRIMARY_COLOR = "&H0000FFFF"   # Vibrant Yellow in BGR hex format
SUBTITLE_OUTLINE_COLOR = "&H00000000"   # Deep Black Outline
SUBTITLE_OUTLINE_WIDTH = 5.0
SUBTITLE_SHADOW_OFFSET = 3.0
SUBTITLE_MARGIN_V = 520  # Pixels from bottom (Placed clearly above YouTube Shorts title/channel safe zone)

# Virality & Ranking Scoring Criteria
VIRAL_SCORE_HIGH_THRESHOLD = 80     # Score >= 80: High probability of viral push
VIRAL_SCORE_MEDIUM_THRESHOLD = 65   # Score 65-79: Medium-High potential
AUTO_TRIM_SILENCE = True            # Automatically trim dead pauses > 0.7s to boost retention score

# Web Server Settings
WEB_HOST = "127.0.0.1"
WEB_PORT = 5000
