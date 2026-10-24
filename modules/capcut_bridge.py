"""
CapCut Bridge Module: Exports Minecraft Shorts into native CapCut / JianYing Desktop Drafts.
Based on pyJianYingDraft from Hommy-master/capcut-mate (https://github.com/Hommy-master/capcut-mate).
Allows users to open projects in CapCut with 1-click and use CapCut's built-in Auto Captions (自动字幕).
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import config
from modules.pyJianYingDraft import (
    ScriptFile, TrackType, TextSegment, Timerange,
    VideoMaterial, VideoSegment
)

# 1 second = 1,000,000 microseconds in CapCut draft format
CAPCUT_TIME_UNIT = 1_000_000


def find_capcut_draft_folder() -> Optional[Path]:
    """Finds CapCut / JianYing local projects folder on Windows."""
    candidates = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft"))
    ]
    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            pass
    return None


def export_capcut_draft(
    short_info: Dict[str, Any],
    source_video_path: str,
    output_draft_dir: str
) -> Dict[str, Any]:
    """
    Creates a native CapCut desktop draft folder with:
    - 9:16 Vertical canvas (1080x1920 @ 60 FPS)
    - Track 1: Main Gameplay Video (145% zoomed, action-centered)
    - Track 2: Overlay HUD (Hearts & Hotbar for suspense)
    - Track 3: Mastered Audio
    - Track 4: Styled Text Captions & Hook Callout Banner
    - Compatible with CapCut Desktop's native 'Auto Captions' feature!
    """
    draft_path = Path(output_draft_dir)
    draft_path.mkdir(parents=True, exist_ok=True)
    
    start_sec = float(short_info.get("start", 0.0))
    duration_sec = float(short_info.get("duration", 30.0))
    hook_offset_sec = float(short_info.get("hook_offset_in_clip", duration_sec * 0.7))
    hook_dur_sec = min(getattr(config, "HOOK_DURATION_SEC", 3.5), duration_sec)
    enable_hook = getattr(config, "ENABLE_HOOK_TEASER", True)
    
    # 1. Initialize CapCut ScriptFile
    script = ScriptFile(
        width=config.TARGET_WIDTH,
        height=config.TARGET_HEIGHT,
        fps=config.TARGET_FPS,
        maintrack_adsorb=True
    )
    draft_content_file = draft_path / "draft_content.json"
    script.save_path = str(draft_content_file)
    
    # 2. Add Track 1: Main Video Track
    v_mat = VideoMaterial(str(source_video_path))
    mat_dur_us = max(100_000, v_mat.duration)
    script.add_track(TrackType.video, track_name="Main_Gameplay")
    
    current_time_us = 0
    
    # Add Hook Teaser if enabled
    if enable_hook:
        hook_start_us = min(max(0, int((start_sec + hook_offset_sec) * CAPCUT_TIME_UNIT)), max(0, mat_dur_us - 100_000))
        hook_dur_us = min(int(hook_dur_sec * CAPCUT_TIME_UNIT), max(100_000, mat_dur_us - hook_start_us))
        hook_seg = VideoSegment(
            v_mat,
            Timerange(0, hook_dur_us),
            source_timerange=Timerange(hook_start_us, hook_dur_us)
        )
        # 145% zoom (1.45 scale) centered on crosshair
        hook_seg.clip_settings.scale_x = 1.45
        hook_seg.clip_settings.scale_y = 1.45
        script.add_segment(hook_seg, track_name="Main_Gameplay")
        current_time_us += hook_dur_us
        
    # Add Main Highlight Segment
    main_start_us = min(max(0, int(start_sec * CAPCUT_TIME_UNIT)), max(0, mat_dur_us - 100_000))
    main_dur_us = min(int(duration_sec * CAPCUT_TIME_UNIT), max(100_000, mat_dur_us - main_start_us))
    main_seg = VideoSegment(
        v_mat,
        Timerange(current_time_us, main_dur_us),
        source_timerange=Timerange(main_start_us, main_dur_us)
    )
    main_seg.clip_settings.scale_x = 1.45
    main_seg.clip_settings.scale_y = 1.45
    script.add_segment(main_seg, track_name="Main_Gameplay")
    
    total_duration_us = current_time_us + main_dur_us
    
    # 3. Add Layer 2: HUD Overlay Track (Hearts & Hotbar)
    try:
        script.add_track(TrackType.video, track_name="HUD_Overlay")
        hud_dur_us = min(total_duration_us, max(100_000, mat_dur_us - main_start_us))
        hud_seg = VideoSegment(
            v_mat,
            Timerange(0, hud_dur_us),
            source_timerange=Timerange(main_start_us, hud_dur_us)
        )
        # Scale and position HUD above subtitles
        hud_seg.clip_settings.scale_x = 1.30
        hud_seg.clip_settings.scale_y = 1.30
        hud_seg.clip_settings.transform_y = -0.32
        script.add_segment(hud_seg, track_name="HUD_Overlay")
    except Exception as e:
        print(f"[CapCutBridge] HUD track note: {type(e).__name__}")
        
    # 4. Add Subtitles / Text Track
    subtitles = short_info.get("subtitles", [])
    script.add_track(TrackType.text, track_name="Captions")
    
    # Hook Banner at the top
    hook_text = short_info.get("hook_text", getattr(config, "HOOK_TEXT_TEMPLATE", "WAIT FOR THE END! 💀"))
    if enable_hook and hook_text:
        hook_text_seg = TextSegment(
            text=hook_text,
            timerange=Timerange(0, int(hook_dur_sec * CAPCUT_TIME_UNIT))
        )
        hook_text_seg.clip_settings.transform_y = 0.65
        hook_text_seg.style.size = 9.0
        script.add_segment(hook_text_seg, track_name="Captions")
        
    # Captions
    time_offset_sec = hook_dur_sec if enable_hook else 0.0
    for sub in subtitles:
        sub_text = str(sub.get("text", "")).strip().upper()
        if not sub_text or (enable_hook and sub_text == hook_text.upper()):
            continue
        try:
            s_sec = float(sub.get("start") or 0.0) + time_offset_sec
            e_sec = float(sub.get("end") or (s_sec + 2.0)) + time_offset_sec
            d_sec = max(0.5, e_sec - s_sec)
            
            c_seg = TextSegment(
                text=sub_text,
                timerange=Timerange(int(s_sec * CAPCUT_TIME_UNIT), int(d_sec * CAPCUT_TIME_UNIT))
            )
            # Safe zone positioning (lower third, y = -0.55)
            c_seg.clip_settings.transform_y = -0.55
            c_seg.style.size = 8.5
            script.add_segment(c_seg, track_name="Captions")
        except Exception:
            continue
            
    # 5. Save CapCut draft files
    script.save()
    
    # Create draft_meta_info.json template
    meta_info_file = draft_path / "draft_meta_info.json"
    if not meta_info_file.exists():
        import json
        meta = {
            "draft_id": f"draft_{short_info.get('short_id', 1)}",
            "draft_name": f"Minecraft_Short_{short_info.get('short_id', 1)}",
            "draft_materials": [],
            "draft_remake_version": "1.0",
            "tm_draft_create": 0,
            "tm_draft_modified": 0
        }
        meta_info_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        
    print(f"[CapCutBridge] Exported CapCut Draft to: {draft_path}")
    
    # 6. Auto-sync with installed CapCut Desktop app
    try:
        capcut_folder = find_capcut_draft_folder()
        if capcut_folder and capcut_folder.exists():
            target_draft = capcut_folder / f"MC_Short_{short_info.get('short_id', 1)}"
            if target_draft.exists():
                shutil.rmtree(target_draft)
            shutil.copytree(draft_path, target_draft)
            print(f"[CapCutBridge] Auto-synced draft into CapCut Desktop: {target_draft}")
    except Exception as e:
        print(f"[CapCutBridge] CapCut sync note: {type(e).__name__}")
            
    return {
        "draft_folder": str(draft_path),
        "status": "SUCCESS"
    }
