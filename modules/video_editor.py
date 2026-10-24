"""
Video Editor Module: FFmpeg assembly engine for 9:16 layout, color grading,
hook prepending, burning styled ASS subtitles, and GPU-accelerated rendering.
"""
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional
import config
from modules.hook_detector import extract_hook_segment
from modules.subtitle_gen import generate_ass_subtitles
from modules.analyzer import extract_audio
from modules.ai_engine import transcribe_clip_audio


def escape_ffmpeg_filter_path(path_str: str) -> str:
    """Escapes backslashes and colons for FFmpeg filter paths on Windows."""
    # Convert to forward slashes then escape colon (e.g. D\:/...)
    p = str(path_str).replace("\\", "/")
    return p.replace(":", "\\:")


def build_filter_graph(
    layout_mode: str,
    ass_path: Optional[str] = None,
    color_grading: bool = True,
    adaptive_rules: Optional[Dict[str, Any]] = None
) -> str:
    """
    Constructs high-end transformative editing filtergraph:
    - 9:16 vertical canvas (1080x1920 @ 60fps)
    - 2-Layer HUD Trick ('hud_overlay'): 145% zoomed gameplay + enlarged Hearts/Hotbar HUD overlay
    - Blurred background meta style ('blur_background')
    - 9:16 Action Center Crop ('center_crop')
    - Keyframe Zooms: Dynamic 100% to 108% rhythmic punch-in zooms every 3s
    - Vibrant Minecraft color grading (+25% sat, +14% contrast, +8% brightness, +20% sharpness, vignette)
    - Anti-Content-ID micro-dithering (100% unique digital pixel hash)
    - Burning rapid-fire animated ASS subtitles in safe zone
    - Audio broadcast mastering (-14 LUFS) + sub-bass sculpting & anti-pop crossfades
    - Synchronized A/V speedup (setpts + atempo) only if specified by adaptive rules
    """
    rules = adaptive_rules or {}
    speedup = float(rules.get("speedup_factor", 1.0))
    trim_silence = bool(rules.get("trim_silence", False))
    
    # 1. Color Grading filter string
    grading_filter = ""
    if color_grading:
        grading_filter = (
            f"eq=contrast={config.COLOR_CONTRAST}:"
            f"brightness={config.COLOR_BRIGHTNESS}:"
            f"saturation={config.COLOR_SATURATION},"
            f"unsharp=5:5:{getattr(config, 'COLOR_SHARPEN', 1.20)}:5:5:0.0"
        )

    vignette_filter = f"vignette=angle={getattr(config, 'VIGNETTE_ANGLE', 'PI/5')}" if getattr(config, "ENABLE_VIGNETTE", True) else ""
    anti_fp = ",noise=alls=1:allf=t" if getattr(config, "ENABLE_ANTI_FINGERPRINT", True) else ""

    # 2. Video Layout Modes
    if layout_mode == "hud_overlay":
        # Viral 2-Layer HUD Trick:
        # Layer 1: 145% zoomed main gameplay covering vertical canvas
        gameplay_chain = (
            "[0:v]crop=w=ih*9/16/1.45:h=ih/1.45:x=(iw-ow)/2:y=(ih-oh)/2-25,"
            "scale=1080:1920:flags=lanczos"
        )
        if getattr(config, "ENABLE_KEYFRAME_ZOOM", True):
            # Dynamic 100% to 108% rhythmic punch-in zoom every 3s to keep viewer retention high
            gameplay_chain += ",zoompan=z='1+0.07*pow(sin(2*PI*in/180),2)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=60"
        if grading_filter:
            gameplay_chain += f",{grading_filter}"
        if vignette_filter:
            gameplay_chain += f",{vignette_filter}"
        gameplay_chain += "[main_gameplay];"

        # Layer 2: Extract bottom-center Minecraft HUD (Hearts, Armor, Hunger & Hotbar)
        hud_chain = (
            "[0:v]crop=w=min(iw\\,ih*0.72):h=ih*0.15:x=(iw-ow)/2:y=ih-oh-12,"
            "scale=1000:-2,"
            "pad=1000:ih+10:0:5:color=0x0d1117@0.65[hud_overlay];"
        )

        # Composite Layer 1 + Layer 2 (HUD placed right above subtitles at y=1240)
        overlay_chain = f"[main_gameplay][hud_overlay]overlay=x=(1080-overlay_w)/2:y=1240{anti_fp}[merged]"
        filter_str = gameplay_chain + hud_chain + overlay_chain
        last_node = "[merged]"

    elif layout_mode == "blur_background":
        # Background: Scale, heavy gaussian blur, dimmed, vignette lens
        bg_chain = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "gblur=sigma=32:steps=2,"
            "eq=brightness=-0.12:contrast=0.92,"
            "vignette=PI/4[bg];"
        )
        # Even-height scaling (1080:-2) to prevent yuv420p odd-dimension crash
        fg_chain = "[0:v]scale=1080:-2[fg_raw];"
        if grading_filter:
            fg_chain += f"[fg_raw]{grading_filter}[fg_graded];"
        else:
            fg_chain += "[fg_raw]copy[fg_graded];"
            
        # Add 3px emerald accent border top and bottom dynamically using pad filter
        fg_chain += "[fg_graded]pad=1080:ih+6:0:3:color=0x10b981@0.85[fg];"
            
        overlay_chain = f"[bg][fg]overlay=0:(1920-overlay_h)/2{anti_fp}[merged]"
        filter_str = bg_chain + fg_chain + overlay_chain
        last_node = "[merged]"

    else:
        # Direct Center Crop (Focused on Minecraft crosshair & action)
        crop_chain = (
            "[0:v]crop=ih*9/16:ih:(iw-ow)/2:0,"
            "scale=1080:1920"
        )
        if getattr(config, "ENABLE_KEYFRAME_ZOOM", True):
            crop_chain += ",zoompan=z='1+0.07*pow(sin(2*PI*in/180),2)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=60"
        if grading_filter:
            crop_chain += f",{grading_filter}"
        if vignette_filter:
            crop_chain += f",{vignette_filter}"
        crop_chain += f"{anti_fp}[cropped]"
        filter_str = crop_chain
        last_node = "[cropped]"

    # Apply matched video speedup if specified by adaptive rules
    if speedup != 1.0:
        filter_str += f";{last_node}setpts=PTS/{speedup}[v_sped]"
        last_node = "[v_sped]"

    # 3. Subtitles
    if ass_path and os.path.exists(ass_path):
        escaped_ass = escape_ffmpeg_filter_path(ass_path)
        filter_str += f";{last_node}ass='{escaped_ass}'[outv]"
    else:
        filter_str += f";{last_node}copy[outv]"

    # 4. Anti-Copyright Audio Mastering (Broadcast -14 LUFS, Punchy Bass, Clear Treble & EQ Sculpting)
    audio_parts = [
        "equalizer=f=60:t=q:w=1.2:g=1.2",
        "equalizer=f=3200:t=q:w=1.0:g=2.0",
        "bass=g=2.2:f=110",
        "treble=g=2.0:f=3500",
        "loudnorm=I=-14:LRA=7:TP=-1.5",
        "afade=t=in:ss=0:d=0.08"
    ]
    if trim_silence:
        audio_parts.append("silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-32dB")
    if speedup != 1.0:
        # Only apply atempo when video speed is also altered, ensuring 100% frame-perfect sync!
        audio_parts.append(f"atempo={speedup}")
        
    audio_chain = ",".join(audio_parts)
    filter_str += f";[0:a]{audio_chain}[outa]"

    return filter_str


def render_short_video(
    source_video: str,
    short_info: Dict[str, Any],
    output_path: str,
    layout_mode: str = config.DEFAULT_LAYOUT_MODE,
    enable_hook: bool = config.ENABLE_HOOK_TEASER,
    enable_subtitles: bool = config.ENABLE_SUBTITLES,
    enable_grading: bool = config.ENABLE_COLOR_GRADING,
    use_nvenc: bool = config.USE_NVENC,
    api_key: str = ""
) -> bool:
    """
    Renders a single 9:16 YouTube Short:
    1. Extracts raw highlight segment.
    2. If hook is enabled, extracts 2.8s hook and prepends it.
    3. Builds and burns styled ASS subtitles in safe zone.
    4. Applies Minecraft color grading and sharpens.
    5. Encodes with GPU NVENC or CPU x264.
    """
    start = float(short_info.get("start", 0.0))
    duration = float(short_info.get("duration", 45.0))
    short_id = short_info.get("short_id", 1)
    
    temp_dir = config.TEMP_DIR / f"render_short_{short_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    raw_clip_path = str(temp_dir / "raw_clip.mp4")
    
    # Step A: Cut Highlight Segment
    print(f"[VideoEditor] Cutting highlight #{short_id}: {start}s -> {start + duration}s...")
    cut_cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", str(source_video),
        "-af", f"afade=t=in:ss=0:d=0.06,afade=t=out:st={max(0.1, duration - 0.06)}:d=0.06",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", getattr(config, "AUDIO_BITRATE", "256k"),
        "-ar", str(getattr(config, "AUDIO_SAMPLE_RATE", 48000)),
        "-avoid_negative_ts", "make_zero",
        raw_clip_path
    ]
    subprocess.run(cut_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    current_source = raw_clip_path

    # Step A2: Real Audio Transcription for Subtitles (Whisper or Gemini Audio API)
    if enable_subtitles and (not short_info.get("subtitles") or short_info.get("use_real_transcription", True)):
        temp_audio_path = str(temp_dir / "clip_audio.mp3")
        if extract_audio(raw_clip_path, temp_audio_path):
            key = api_key or short_info.get("api_key", "")
            real_subs = transcribe_clip_audio(temp_audio_path, api_key=key)
            if real_subs:
                short_info["subtitles"] = real_subs
    
    # Step B: Hook Teaser Prepending
    if enable_hook:
        hook_path = str(temp_dir / "hook_teaser.mp4")
        hook_offset = float(short_info.get("hook_offset_in_clip", duration * 0.7))
        print(f"[VideoEditor] Extracting hook climax teaser from offset {hook_offset}s...")
        
        hook_extracted = extract_hook_segment(
            source_video,
            clip_start=start,
            clip_duration=duration,
            hook_offset=hook_offset,
            output_hook_path=hook_path
        )
        
        if hook_extracted and os.path.exists(hook_path):
            # Concatenate hook + main clip
            concat_list = temp_dir / "concat_list.txt"
            concat_list.write_text(
                f"file '{Path(hook_path).as_posix()}'\nfile '{Path(raw_clip_path).as_posix()}'\n",
                encoding="utf-8"
            )
            stitched_path = str(temp_dir / "stitched_with_hook.mp4")
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                stitched_path
            ]
            try:
                subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                current_source = stitched_path
                print(f"[VideoEditor] Successfully prepended {config.HOOK_DURATION_SEC}s hook teaser!")
            except Exception as e:
                print(f"[VideoEditor] Hook stitch warning: {e}, continuing with raw clip.")

    # Step C: Generate Subtitles ASS File
    ass_path = None
    if enable_subtitles and "subtitles" in short_info and short_info["subtitles"]:
        ass_path = str(temp_dir / "subtitles.ass")
        hook_dur = config.HOOK_DURATION_SEC if enable_hook else 0.0
        subs_to_render = []
        hook_text = short_info.get("hook_text", config.HOOK_TEXT_TEMPLATE)
        
        if enable_hook:
            # 0.0 to hook_dur displays the Hook Callout Banner
            subs_to_render.append({
                "start": 0.0,
                "end": hook_dur,
                "text": hook_text,
                "style": "HookBanner"
            })
            # Shift story subtitles by hook_dur
            for sub in short_info["subtitles"]:
                s_txt = str(sub.get("text", "")).strip().upper()
                if s_txt == hook_text.strip().upper() and float(sub.get("start", 0)) < 4.0:
                    continue
                subs_to_render.append({
                    "start": float(sub.get("start", 0.0)) + hook_dur,
                    "end": float(sub.get("end", 2.0)) + hook_dur,
                    "text": sub.get("text", ""),
                    "style": "ProCaptions"
                })
        else:
            subs_to_render = short_info["subtitles"]
            
        generate_ass_subtitles(subs_to_render, ass_path)

    # Step D: Filtergraph (9:16 layout + Color Grading + Subtitle burn-in + Adaptive Rules)
    adaptive_rules = short_info.get("adaptive_rules", {})
    filter_graph = build_filter_graph(
        layout_mode=layout_mode,
        ass_path=ass_path,
        color_grading=enable_grading,
        adaptive_rules=adaptive_rules
    )
    
    # Step E: Encoder Selection (GPU NVENC vs CPU x264)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[VideoEditor] Rendering final 9:16 Short to {output_path}...")
    
    # Try GPU NVENC first if enabled
    if use_nvenc:
        render_cmd = [
            "ffmpeg", "-y",
            "-i", str(current_source),
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "[outa]?",
            "-c:v", "h264_nvenc",
            "-preset", "p6",
            "-cq", "18",
            "-b:v", getattr(config, "EXPORT_VIDEO_BITRATE", "22M"),
            "-maxrate", getattr(config, "EXPORT_MAX_BITRATE", "25M"),
            "-bufsize", "45M",
            "-rc", "vbr",
            "-colorspace", getattr(config, "EXPORT_COLORSPACE", "bt709"),
            "-color_primaries", getattr(config, "EXPORT_COLORSPACE", "bt709"),
            "-color_trc", getattr(config, "EXPORT_COLORSPACE", "bt709"),
            "-color_range", "tv",
            "-c:a", "aac",
            "-b:a", getattr(config, "AUDIO_BITRATE", "256k"),
            "-ar", str(getattr(config, "AUDIO_SAMPLE_RATE", 48000)),
            "-pix_fmt", "yuv420p",
            "-r", str(config.TARGET_FPS),
            "-map_metadata", "-1",
            "-metadata", "title=",
            "-metadata", "comment=Rendered with Minecraft Shorts Pro Engine",
            str(output_path)
        ]
        res = subprocess.run(render_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            print(f"[VideoEditor] GPU NVENC render finished successfully!")
            return True
        else:
            print(f"[VideoEditor] NVENC failed or busy, falling back to CPU x264: {res.stderr[:200]}")

    # CPU x264 fallback
    cpu_render_cmd = [
        "ffmpeg", "-y",
        "-i", str(current_source),
        "-filter_complex", filter_graph,
        "-map", "[outv]",
        "-map", "[outa]?",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-b:v", getattr(config, "EXPORT_VIDEO_BITRATE", "22M"),
        "-maxrate", getattr(config, "EXPORT_MAX_BITRATE", "25M"),
        "-bufsize", "45M",
        "-colorspace", getattr(config, "EXPORT_COLORSPACE", "bt709"),
        "-color_primaries", getattr(config, "EXPORT_COLORSPACE", "bt709"),
        "-color_trc", getattr(config, "EXPORT_COLORSPACE", "bt709"),
        "-color_range", "tv",
        "-c:a", "aac",
        "-b:a", getattr(config, "AUDIO_BITRATE", "256k"),
        "-ar", str(getattr(config, "AUDIO_SAMPLE_RATE", 48000)),
        "-pix_fmt", "yuv420p",
        "-r", str(config.TARGET_FPS),
        "-map_metadata", "-1",
        "-metadata", "title=",
        "-metadata", "comment=Rendered with Minecraft Shorts Pro Engine",
        str(output_path)
    ]
    cpu_res = subprocess.run(cpu_render_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cpu_res.returncode == 0
