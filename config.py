"""
Configuration settings for Minecraft YouTube Shorts AI Pipeline
"""
import os
import tempfile
from pathlib import Path

# Base Paths
BASE_DIR = Path(r"D:\Youtube\Minecraft")

# Auto-load .env file if present
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    try:
        with open(_env_file, "r", encoding="utf-8") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
    except Exception:
        pass

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
# Option 1: Gemini API Key (Loaded from .env or system environment)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Default Gemini Model for Multimodal / Content Analysis
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Option 2: Groq Whisper API Key (get free from https://console.groq.com)
# Ultra-fast speech-to-text with Whisper Large V3
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Video Processing Settings
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 60
USE_NVENC = True  # Uses NVIDIA GPU (GTX 1650) for fast NVENC encoding

# Layout Mode:
# 'hud_overlay'     = 2-Layer HUD Trick: 145% zoomed main gameplay + enlarged Hearts/Hotbar HUD overlay (Viral Meta)
# 'blur_background' = Center 16:9 gameplay with blurred enlarged background
# 'center_crop'     = Direct 9:16 vertical crop focused on the Minecraft crosshair/action
DEFAULT_LAYOUT_MODE = "hud_overlay"

# Color Grading Preset (Enhanced for Caves, Deep Dark, and Nether Vibrancy)
ENABLE_COLOR_GRADING = True
COLOR_SATURATION = 1.25   # +25% saturation for eye-catching grass, armor & lava
COLOR_CONTRAST = 1.14     # +14% contrast for deep block shadows
COLOR_BRIGHTNESS = 0.08   # +8% exposure lift to make dark caves & Deep Dark crystal clear
ENABLE_SHARPENING = True  # Crisp unsharp filter for pixel-perfect block edges
COLOR_SHARPEN = 1.20      # +20% sharpness for mobile screens
ENABLE_VIGNETTE = True    # Subtle cinematic border focusing eyes on center crosshair
VIGNETTE_ANGLE = "PI/5"

# Anti-Copyright & Digital Fingerprint Protection
ENABLE_ANTI_FINGERPRINT = True   # Temporal micro-dither, custom harmonic EQ & metadata wiping
ENABLE_KEYFRAME_ZOOM = True      # Dynamic 100% to 115% rhythmic punch-in zooms to boost APV retention

# Anti-Blur High-Bitrate Export Settings (Prevents pixelation during fast camera moves)
EXPORT_VIDEO_BITRATE = "22M"     # Target 22 Mbps (20-25 Mbps YouTube recommendation)
EXPORT_MAX_BITRATE = "25M"       # Peak 25 Mbps
EXPORT_COLORSPACE = "bt709"      # Rec. 709 standard sRGB
AUDIO_SAMPLE_RATE = 48000        # Broadcast standard 48 kHz
AUDIO_BITRATE = "256k"           # High-fidelity AAC audio

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

# Storage & Auto-Cleanup Settings
# Automatically delete old long videos' shorts when a new long video is processed
AUTO_CLEAN_OLD_SHORTS = True
# Automatically remove intermediate temporary render clips (saves ~170MB per rendered short)
KEEP_TEMP_FILES = False

# Web Server Settings
WEB_HOST = "127.0.0.1"
WEB_PORT = 5000
