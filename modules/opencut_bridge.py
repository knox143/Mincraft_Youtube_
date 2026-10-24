"""
OpenCut Bridge Module: Converts Minecraft Shorts highlight data, hooks,
subtitles, and color grading into OpenCut native Project Timeline format.
Repo reference: https://github.com/OpenCut-app/OpenCut
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
import config

# OpenCut uses high-precision integer tick timing: 120,000 ticks per second
TICKS_PER_SECOND = 120_000


def sec_to_ticks(seconds: float) -> int:
    """Converts seconds to OpenCut MediaTime integer ticks."""
    return int(round(float(seconds) * TICKS_PER_SECOND))


def generate_opencut_project(
    short_info: Dict[str, Any],
    source_video_path: str,
    output_project_path: str
) -> Dict[str, Any]:
    """
    Creates an OpenCut project JSON file with:
    - 9:16 Canvas (1080x1920) at 60 FPS
    - Main video track with hook teaser + highlight cut
    - Text overlay track with styled word-timed subtitles
    - Bookmarks marking Hook Teaser & Climax Moment
    - Blurred background layout configuration
    """
    project_id = f"opencut-mc-{short_info.get('short_id', 1)}-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    start_sec = float(short_info.get("start", 0.0))
    duration_sec = float(short_info.get("duration", 45.0))
    total_ticks = sec_to_ticks(duration_sec)
    
    # 1. Main Video Track Elements
    main_elements = []
    
    # If hook teaser is enabled, add 3.5s hook element first, then main clip
    hook_offset_sec = float(short_info.get("hook_offset_in_clip", duration_sec * 0.7))
    hook_dur_sec = min(getattr(config, "HOOK_DURATION_SEC", 3.5), duration_sec)
    hook_ticks = sec_to_ticks(hook_dur_sec)
    
    # Element 1: Hook Teaser
    main_elements.append({
        "id": f"elem-hook-{uuid.uuid4().hex[:6]}",
        "name": f"Hook Teaser ({short_info.get('hook_text', 'Hook')})",
        "type": "video",
        "mediaId": Path(source_video_path).name,
        "sourcePath": str(source_video_path),
        "startTime": 0,
        "duration": hook_ticks,
        "trimStart": sec_to_ticks(start_sec + hook_offset_sec),
        "trimEnd": sec_to_ticks(start_sec + hook_offset_sec + hook_dur_sec),
        "params": {
            "position": {"x": 0.5, "y": 0.5},
            "scale": {"x": 1.0, "y": 1.0},
            "rotation": 0,
            "opacity": 1.0
        }
    })
    
    # Element 2: Story Highlight Clip
    clip_ticks = sec_to_ticks(duration_sec)
    main_elements.append({
        "id": f"elem-clip-{uuid.uuid4().hex[:6]}",
        "name": short_info.get("highlight_title", "Minecraft Highlight"),
        "type": "video",
        "mediaId": Path(source_video_path).name,
        "sourcePath": str(source_video_path),
        "startTime": hook_ticks,
        "duration": clip_ticks,
        "trimStart": sec_to_ticks(start_sec),
        "trimEnd": sec_to_ticks(start_sec + duration_sec),
        "params": {
            "position": {"x": 0.5, "y": 0.5},
            "scale": {"x": 1.0, "y": 1.0},
            "rotation": 0,
            "opacity": 1.0
        }
    })
    
    # 2. Text / Subtitle Overlay Track
    text_elements = []
    subtitles = short_info.get("subtitles", [])
    
    # Add Hook Title Banner at 0-2.8s
    hook_text = short_info.get("hook_text", "WAIT FOR THE END! 💀")
    text_elements.append({
        "id": f"elem-text-hook-{uuid.uuid4().hex[:6]}",
        "name": "Hook Callout Banner",
        "type": "text",
        "text": hook_text,
        "startTime": 0,
        "duration": hook_ticks,
        "trimStart": 0,
        "trimEnd": hook_ticks,
        "params": {
            "position": {"x": 0.5, "y": 0.15},  # Top banner
            "fontSize": 48,
            "fontFamily": "Arial Black",
            "fillColor": "#FFFFFF",
            "strokeColor": "#000000",
            "strokeWidth": 4,
            "textAlign": "center"
        }
    })
    
    # Add synchronized subtitles
    for sub in subtitles:
        sub_start_ticks = hook_ticks + sec_to_ticks(sub.get("start", 0.0))
        sub_dur_ticks = sec_to_ticks(max(0.5, sub.get("end", 1.0) - sub.get("start", 0.0)))
        
        text_elements.append({
            "id": f"elem-sub-{uuid.uuid4().hex[:6]}",
            "name": f"Subtitle: {sub.get('text', '')[:15]}",
            "type": "text",
            "text": str(sub.get("text", "")).upper(),
            "startTime": sub_start_ticks,
            "duration": sub_dur_ticks,
            "trimStart": 0,
            "trimEnd": sub_dur_ticks,
            "params": {
                "position": {"x": 0.5, "y": 0.78},  # Shorts safe zone (lower-middle)
                "fontSize": 42,
                "fontFamily": "Arial Black",
                "fillColor": "#FFFF00",  # Hormozi Yellow
                "strokeColor": "#000000",
                "strokeWidth": 4,
                "textAlign": "center"
            }
        })
        
    # 3. Bookmarks / Timeline Markers
    bookmarks = [
        {
            "time": 0,
            "note": "🔥 Retention Hook Teaser (0-3s)",
            "color": "#ef4444"
        },
        {
            "time": hook_ticks,
            "note": "🎬 Story Arc Begins",
            "color": "#3b82f6"
        },
        {
            "time": hook_ticks + sec_to_ticks(hook_offset_sec),
            "note": "⚡ Climax / Peak Action Moment",
            "color": "#10b981"
        }
    ]
    
    # 4. Construct OpenCut Project Schema
    total_project_duration_ticks = hook_ticks + clip_ticks
    scene_id = f"scene-{uuid.uuid4().hex[:6]}"
    
    project = {
        "metadata": {
            "id": project_id,
            "name": short_info.get("highlight_title", "Minecraft Short"),
            "duration": total_project_duration_ticks,
            "durationSeconds": round(total_project_duration_ticks / TICKS_PER_SECOND, 2),
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "version": 1,
            "sourceRepository": "https://github.com/OpenCut-app/OpenCut"
        },
        "settings": {
            "fps": 60,
            "canvasSize": {
                "width": 1080,
                "height": 1920
            },
            "canvasSizeMode": "preset",
            "background": {
                "type": "blur",
                "blurIntensity": 5
            },
            "colorGrading": {
                "saturation": 1.25,
                "contrast": 1.14,
                "brightness": 0.02
            }
        },
        "scenes": [
            {
                "id": scene_id,
                "name": "Main Scene",
                "isMain": True,
                "bookmarks": bookmarks,
                "tracks": {
                    "main": {
                        "id": "track-video-main",
                        "name": "Main Gameplay Video",
                        "type": "video",
                        "muted": False,
                        "hidden": False,
                        "elements": main_elements
                    },
                    "overlay": [
                        {
                            "id": "track-text-captions",
                            "name": "Dynamic Subtitles & Hooks",
                            "type": "text",
                            "hidden": False,
                            "elements": text_elements
                        }
                    ],
                    "audio": []
                },
                "createdAt": now_iso,
                "updatedAt": now_iso
            }
        ],
        "currentSceneId": scene_id,
        "timelineViewState": {
            "zoomLevel": 1.0,
            "scrollLeft": 0,
            "playheadTime": 0
        }
    }
    
    # Save project file
    out_file = Path(output_project_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"[OpenCutBridge] Exported OpenCut Project to: {out_file}")
    return project
