"""
Video Editor Module: FFmpeg assembly engine for 9:16 layout, color grading,
hook prepending, burning styled ASS subtitles, and GPU-accelerated rendering.
"""
import sys
import subprocess
import os

# Safe UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import config
from modules.hook_detector import extract_hook_segment
from modules.subtitle_gen import generate_ass_subtitles
from modules.analyzer import extract_audio
from modules.ai_engine import transcribe_clip_audio
from modules.scene_effects import detect_troll_moment
from modules.voice_studio import generate_scene_commentary_script, synthesize_voiceover


def escape_ffmpeg_filter_path(path_str: str) -> str:
    """Escapes backslashes and colons for FFmpeg filter paths on Windows."""
    # Convert to forward slashes then escape colon (e.g. D\:/...)
    p = str(path_str).replace("\\", "/")
    return p.replace(":", "\\:")


def build_filter_graph(
    layout_mode: str,
    ass_path: Optional[str] = None,
    color_grading: bool = True,
    adaptive_rules: Optional[Dict[str, Any]] = None,
    troll_info: Optional[Dict[str, Any]] = None,
    meme_input_idx: Optional[int] = None,
    audio_indices: Optional[Dict[str, int]] = None,
    voice_mode: str = "original"
) -> str:
    """
    Constructs high-end transformative editing filtergraph:
    - 9:16 vertical canvas (1080x1920 @ 60fps)
    - 2-Layer HUD Trick ('hud_overlay'): 145% zoomed gameplay + enlarged Hearts/Hotbar HUD overlay
    - Blurred background meta style ('blur_background')
    - 9:16 Action Center Crop ('center_crop')
    - Trollface Meme Punch: Dynamic zoom overlay at detected troll/clutch moment
    - Burning rapid-fire animated ASS subtitles in safe zone
    - Multi-Track Audio Mixing: Game audio + VoiceStudio AI voiceover + Phonk/Suspense BGM + Vine Boom/Bruh SFX
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

    # 3. Dynamic Trollface Meme Overlay Effect
    if troll_info and meme_input_idx is not None:
        t_start = float(troll_info.get("actual_troll_time_sec", 15.0))
        t_dur = float(troll_info.get("troll_duration_sec", 2.2))
        t_end = t_start + t_dur
        scale_expr = f"scale=eval=frame:w='560+45*sin(14*(t-{t_start:.2f}))':h=-1"
        filter_str += f";[{meme_input_idx}:v]format=rgba,{scale_expr}[troll_scaled]"
        filter_str += f";{last_node}[troll_scaled]overlay=x='(1080-w)/2':y='(1920-h)*0.40':enable='between(t,{t_start:.2f},{t_end:.2f})'[with_troll]"
        last_node = "[with_troll]"

    # Apply matched video speedup if specified by adaptive rules
    if speedup != 1.0:
        filter_str += f";{last_node}setpts=PTS/{speedup}[v_sped]"
        last_node = "[v_sped]"

    # 4. Subtitles
    if ass_path and os.path.exists(ass_path):
        escaped_ass = escape_ffmpeg_filter_path(ass_path)
        filter_str += f";{last_node}ass='{escaped_ass}'[outv]"
    else:
        filter_str += f";{last_node}copy[outv]"

    # 5. Multi-Track Audio Mixing (Game SFX + AI Voiceover + Phonk/Suspense BGM + Vine Boom SFX)
    mix_sources = []
    
    # Track 1: Original Minecraft Gameplay Audio
    if voice_mode == "replace":
        # Mute original video voice completely
        filter_str += ";[0:a]volume=0.0[game_a]"
    elif voice_mode == "mix_ducked":
        # Duck original gameplay audio under the new AI commentary voice
        filter_str += ";[0:a]volume=0.35,highpass=f=80,equalizer=f=60:t=q:w=1.2:g=1.2[game_a]"
    else:
        # Keep original audio at broadcast standards
        filter_str += ";[0:a]equalizer=f=60:t=q:w=1.2:g=1.2,equalizer=f=3200:t=q:w=1.0:g=2.0,bass=g=2.2:f=110,treble=g=2.0:f=3500,loudnorm=I=-14:LRA=7:TP=-1.5,afade=t=in:ss=0:d=0.08[game_a]"
    mix_sources.append("[game_a]")

    if audio_indices:
        # Track 2: Background Music (BGM - Phonk Drift / Suspense)
        if "bgm" in audio_indices:
            b_idx = audio_indices["bgm"]
            bgm_vol = getattr(config, "SCENE_BGM_VOLUME", 0.18)
            filter_str += f";[{b_idx}:a]aloop=loop=-1:size=2e+09,volume={bgm_vol},bass=g=2.5:f=90[bgm_a]"
            mix_sources.append("[bgm_a]")

        # Track 3: Sound Effect (Vine Boom / Bruh / Creeper Hiss at troll moment)
        if "sfx" in audio_indices and troll_info:
            s_idx = audio_indices["sfx"]
            delay_ms = int(max(0.0, troll_info.get("actual_sfx_offset_sec", 0.0)) * 1000)
            filter_str += f";[{s_idx}:a]adelay={delay_ms}|{delay_ms},volume=1.35[sfx_a]"
            mix_sources.append("[sfx_a]")

        # Track 4: VoiceStudio AI Voiceover / Dubbing
        if "vo" in audio_indices:
            v_idx = audio_indices["vo"]
            filter_str += f";[{v_idx}:a]volume=1.35,loudnorm=I=-14:TP=-1.5[vo_a]"
            mix_sources.append("[vo_a]")

    if len(mix_sources) > 1:
        filter_str += f";{''.join(mix_sources)}amix=inputs={len(mix_sources)}:duration=first:dropout_transition=2,volume=1.2[outa]"
    else:
        filter_str += ";[game_a]copy[outa]"

    return filter_str

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

    # Step D: Filtergraph & Scene FX (Trollface Overlay + Phonk/Suspense BGM + SFX + AI Voiceover)
    adaptive_rules = short_info.get("adaptive_rules", {})
    
    enable_troll = short_info.get("enable_troll_effect", getattr(config, "ENABLE_TROLLFACE_EFFECT", True))
    enable_sfx = short_info.get("enable_sfx", getattr(config, "ENABLE_SCENE_SFX", True))
    enable_bgm = short_info.get("enable_bgm", getattr(config, "ENABLE_SCENE_BGM", True))
    enable_vo = short_info.get("enable_voiceover", getattr(config, "ENABLE_AI_VOICEOVER", False))
    vo_mode = short_info.get("voiceover_mode", getattr(config, "VOICEOVER_MODE", "mix_ducked"))
    vo_preset = short_info.get("voiceover_preset", getattr(config, "VOICEOVER_PRESET", "hi_gamer_pro"))

    troll_info = detect_troll_moment(short_info, duration)
    hook_shift = config.HOOK_DURATION_SEC if enable_hook else 0.0
    troll_info["actual_troll_time_sec"] = troll_info["troll_time_sec"] + hook_shift
    troll_info["actual_sfx_offset_sec"] = troll_info["sfx_offset_sec"] + hook_shift

    cfg_style = getattr(config, "TROLLFACE_STYLE", "auto")
    if cfg_style == "phonk":
        troll_info["meme_image_path"] = str(config.BASE_DIR / "assets" / "memes" / "trollface_phonk.png")
    elif cfg_style == "classic":
        troll_info["meme_image_path"] = str(config.BASE_DIR / "assets" / "memes" / "trollface.png")

    extra_ffmpeg_inputs = []
    current_input_idx = 1
    meme_idx = None
    audio_indices = {}

    # 1. Trollface Meme input
    if enable_troll and os.path.exists(troll_info["meme_image_path"]):
        extra_ffmpeg_inputs.extend(["-i", str(troll_info["meme_image_path"])])
        meme_idx = current_input_idx
        current_input_idx += 1
        print(f"[VideoEditor] 🎭 Trollface meme effect armed at {troll_info['actual_troll_time_sec']}s!")

    # 2. BGM input
    if enable_bgm and os.path.exists(troll_info["bgm_audio_path"]):
        extra_ffmpeg_inputs.extend(["-i", str(troll_info["bgm_audio_path"])])
        audio_indices["bgm"] = current_input_idx
        current_input_idx += 1
        print(f"[VideoEditor] 🎵 BGM armed: {Path(troll_info['bgm_audio_path']).name}")

    # 3. SFX input
    if enable_sfx and os.path.exists(troll_info["sfx_audio_path"]):
        extra_ffmpeg_inputs.extend(["-i", str(troll_info["sfx_audio_path"])])
        audio_indices["sfx"] = current_input_idx
        current_input_idx += 1
        print(f"[VideoEditor] 💥 Scene SFX armed: {Path(troll_info['sfx_audio_path']).name} at {troll_info['actual_sfx_offset_sec']}s")

    # 4. VoiceStudio AI Voiceover
    if enable_vo:
        vo_script = short_info.get("voiceover_script") or ""
        if not vo_script:
            vo_script = generate_scene_commentary_script(short_info, api_key=api_key)
        if vo_script:
            vo_file = str(temp_dir / "ai_voiceover.mp3")
            synthesize_voiceover(vo_script, voice_key=vo_preset, output_audio_path=vo_file)
            if os.path.exists(vo_file):
                extra_ffmpeg_inputs.extend(["-i", str(vo_file)])
                audio_indices["vo"] = current_input_idx
                current_input_idx += 1
                print(f"[VideoEditor] 🎙️ VoiceStudio AI Voiceover armed: '{vo_script}'")

    filter_graph = build_filter_graph(
        layout_mode=layout_mode,
        ass_path=ass_path,
        color_grading=enable_grading,
        adaptive_rules=adaptive_rules,
        troll_info=troll_info if enable_troll else None,
        meme_input_idx=meme_idx,
        audio_indices=audio_indices,
        voice_mode=vo_mode if enable_vo else "original"
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
            *extra_ffmpeg_inputs,
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
            if not getattr(config, "KEEP_TEMP_FILES", False):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return True
        else:
            print(f"[VideoEditor] NVENC failed or busy, falling back to CPU x264: {res.stderr[:200]}")

    # CPU x264 fallback
    cpu_render_cmd = [
        "ffmpeg", "-y",
        "-i", str(current_source),
        *extra_ffmpeg_inputs,
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
    success = (cpu_res.returncode == 0)
    
    # Auto-clean temporary render files to prevent disk bloating
    if not getattr(config, "KEEP_TEMP_FILES", False):
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    return success
