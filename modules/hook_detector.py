"""
Hook Detector Module: Identifies shocking climax / punchline moments
and prepares 2.5-3.0 second retention teasers for the beginning of the Short.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple
import config


def extract_hook_segment(
    video_path: str,
    clip_start: float,
    clip_duration: float,
    hook_offset: float,
    output_hook_path: str,
    hook_duration: float = config.HOOK_DURATION_SEC
) -> bool:
    """
    Extracts the 2.5-3.0s climax moment from within the highlight to serve
    as the introductory retention teaser hook.
    """
    # Calculate absolute start time of the hook in the original video
    # If hook_offset is provided within the clip, hook_start = clip_start + hook_offset
    # Ensure hook stays within clip bounds
    if hook_offset <= 0 or hook_offset >= clip_duration - hook_duration:
        # Default to ~75% into the clip where the climax usually peaks
        target_offset = max(0.0, clip_duration * 0.75 - hook_duration)
    else:
        target_offset = hook_offset
        
    abs_hook_start = clip_start + target_offset
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(abs_hook_start),
        "-t", str(hook_duration),
        "-i", str(video_path),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-avoid_negative_ts", "make_zero",
        str(output_hook_path)
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"[HookDetector] Error extracting hook teaser: {e}")
        return False


def get_hook_text_for_category(highlight_type: str = "") -> str:
    """Returns high-retention hook overlay text."""
    low = highlight_type.lower()
    if "clutch" in low or "water" in low:
        return "TOP 1% MINECRAFT CLUTCH! 🌊"
    elif "fail" in low or "death" in low:
        return "BRO REALLY THOUGHT HE WAS SAFE 💀"
    elif "diamond" in low or "netherite" in low:
        return "THE RAREST MINECRAFT DROP?! 💎"
    elif "creeper" in low or "jumpscare" in low:
        return "HEART ATTACK IN 3... 2... 1... 💥"
    elif "hardcore" in low:
        return "I ALMOST LOST 100 DAYS! 😱"
    return "WAIT FOR THE END! 💀"
