"""
Scene Effects & Trollface Meme Engine for Minecraft YouTube Shorts
Handles:
1. Intelligent detection of Troll / Clutch / Surprise moments in gameplay
2. Dynamic Trollface Meme Overlays (Classic Grin & Dark Phonk with zoom punch)
3. Scene-based Sound Effects (Vine boom, Bruh, Creeper Hiss, Heartbeat)
4. Rhythmic BGM pairing (Suspense buildup to Phonk beat drop)
5. FFmpeg visual FX injection (Zoom shockwave, Red danger flash, Screen shake)
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import config


ASSETS_DIR = config.BASE_DIR / "assets"
MEMES_DIR = ASSETS_DIR / "memes"
SFX_DIR = ASSETS_DIR / "sfx"
BGM_DIR = ASSETS_DIR / "bgm"


def detect_troll_moment(
    short_info: Dict[str, Any],
    duration: float = 30.0
) -> Dict[str, Any]:
    """
    Analyzes the short video segment and locates the optimal Trollface / Climax timestamp.
    In Minecraft clips, the surprise or fail moment typically occurs around 65%-80% through the clip,
    or at the detected hook offset.
    """
    # Check if AI or energy peaks flagged a specific climax offset
    hook_offset = float(short_info.get("hook_offset_in_clip", duration * 0.72))
    troll_time = min(max(2.0, hook_offset), duration - 2.5)
    
    title = short_info.get("highlight_title", "").lower()
    text = short_info.get("hook_text", "").lower()
    
    # Classify Scene Type & select meme/sfx pairing
    is_creeper = "creeper" in title or "creeper" in text
    is_phonk_clutch = "clutch" in title or "mlg" in title or "god" in title or "hardcore" in title
    is_fail = "fail" in title or "died" in title or "rip" in title or "wait" in text
    
    if is_phonk_clutch:
        meme_file = MEMES_DIR / "trollface_phonk.png"
        sfx_file = SFX_DIR / "vine_boom.mp3"
        bgm_file = BGM_DIR / "phonk_beat.mp3"
        effect_style = "phonk_zoom"
    elif is_creeper:
        meme_file = MEMES_DIR / "trollface.png"
        sfx_file = SFX_DIR / "creeper_hiss.mp3"
        bgm_file = BGM_DIR / "suspense_buildup.mp3"
        effect_style = "red_flash"
    elif is_fail:
        meme_file = MEMES_DIR / "trollface.png"
        sfx_file = SFX_DIR / "bruh.mp3"
        bgm_file = BGM_DIR / "suspense_buildup.mp3"
        effect_style = "zoom_punch"
    else:
        # Default high-retention trollface
        meme_file = MEMES_DIR / "trollface.png"
        sfx_file = SFX_DIR / "vine_boom.mp3"
        bgm_file = BGM_DIR / "phonk_beat.mp3"
        effect_style = "zoom_punch"
        
    return {
        "enabled": True,
        "troll_time_sec": round(troll_time, 2),
        "troll_duration_sec": 2.2,
        "meme_image_path": str(meme_file),
        "sfx_audio_path": str(sfx_file),
        "bgm_audio_path": str(bgm_file),
        "effect_style": effect_style,
        "sfx_offset_sec": round(troll_time, 2)
    }


def build_trollface_filter(
    meme_image_path: str,
    troll_time_sec: float,
    troll_dur_sec: float,
    input_tag: str = "[fg]",
    output_tag: str = "[with_troll]",
    effect_style: str = "zoom_punch",
    meme_input_idx: int = 1
) -> Tuple[str, str]:
    """
    Generates FFmpeg filter_complex syntax to overlay the Trollface meme
    with animated punch-in zoom and transparency.
    """
    if not os.path.exists(meme_image_path):
        return "", input_tag
        
    t_start = troll_time_sec
    t_end = troll_time_sec + troll_dur_sec
    
    # 1. Scale & Animate Meme: starts at 480px, rapidly punches in with subtle pulse
    # e.g. scale=eval=frame:w='520+35*sin(12*(t-{t_start}))':h=-1
    scale_expr = f"scale=eval=frame:w='560+40*sin(14*(t-{t_start}))':h=-1"
    
    filter_lines = []
    meme_scaled = f"[troll_scaled]"
    filter_lines.append(f"[{meme_input_idx}:v]format=rgba,{scale_expr}{meme_scaled};")
    
    # 2. Overlay at center of screen during the troll timerange
    enable_cond = f"between(t,{t_start:.2f},{t_end:.2f})"
    overlay_x = "(W-w)/2"
    # Position slightly above center crosshair (y=42% of 1920)
    overlay_y = "(H-h)*0.42"
    
    filter_lines.append(
        f"{input_tag}{meme_scaled}overlay=x='{overlay_x}':y='{overlay_y}':enable='{enable_cond}'{output_tag}"
    )
    
    return "".join(filter_lines), output_tag
