"""
Analyzer Module: Scans long video, detects audio energy, silences, and highlights
"""
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Any
import config


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Retrieves duration, resolution, and fps of video via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        duration = float(data.get("format", {}).get("duration", 0.0))
        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        
        width = int(video_stream.get("width", 1920)) if video_stream else 1920
        height = int(video_stream.get("height", 1080)) if video_stream else 1080
        
        # Calculate FPS
        r_frame_rate = video_stream.get("r_frame_rate", "60/1") if video_stream else "60/1"
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 60.0
        else:
            fps = float(r_frame_rate)
            
        return {
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "filename": Path(video_path).name,
            "path": str(video_path)
        }
    except Exception as e:
        print(f"[Analyzer] Error reading video info: {e}")
        return {
            "duration": 0.0,
            "width": 1920,
            "height": 1080,
            "fps": 60.0,
            "filename": Path(video_path).name,
            "path": str(video_path)
        }


def extract_audio(video_path: str, output_audio_path: str) -> bool:
    """Extracts audio to MP3 for transcription and AI analysis."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "128k",
        "-ar", "44100",
        str(output_audio_path)
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"[Analyzer] Error extracting audio: {e}")
        return False


def detect_silences(video_path: str, noise_db: float = -32.0, min_duration: float = 0.8) -> List[Dict[str, float]]:
    """Detects silences in the audio track using FFmpeg silencedetect."""
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-af", f"silencedetect=n={noise_db}dB:d={min_duration}",
        "-f", "null",
        "-"
    ]
    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        output = result.stderr
        
        silences = []
        silence_start = None
        
        for line in output.splitlines():
            if "silence_start:" in line:
                match = re.search(r"silence_start:\s*([0-9.]+)", line)
                if match:
                    silence_start = float(match.group(1))
            elif "silence_end:" in line and silence_start is not None:
                match = re.search(r"silence_end:\s*([0-9.]+)", line)
                if match:
                    silence_end = float(match.group(1))
                    silences.append({
                        "start": silence_start,
                        "end": silence_end,
                        "duration": silence_end - silence_start
                    })
                    silence_start = None
        return silences
    except Exception as e:
        print(f"[Analyzer] Error detecting silences: {e}")
        return []


def scan_energy_peaks(video_path: str, duration: float, segment_len: float = 45.0) -> List[Dict[str, Any]]:
    """
    Scans video timeline for high audio excitement / volume peaks.
    Generates candidate highlight segments of 30-55s each.
    """
    if duration <= 0:
        return []
    
    silences = detect_silences(video_path)
    
    # Calculate intervals with active speech & sound
    # Divide timeline into potential candidate blocks
    candidates = []
    
    # Target short duration around 30 seconds total (optimized for new channels & max retention)
    hook_len = config.HOOK_DURATION_SEC if config.ENABLE_HOOK_TEASER else 0.0
    target_len = max(20.0, getattr(config, "TARGET_SHORT_DURATION", 30.0) - hook_len)
    min_len = getattr(config, "MIN_SHORT_DURATION", 22.0) - hook_len
    max_len = getattr(config, "MAX_SHORT_DURATION", 33.0) - hook_len
    step = 22.0
    
    current_time = 0.0
    index = 1
    
    while current_time + 15.0 < duration:
        start_time = current_time
        candidate_end = min(start_time + target_len, duration)
        
        # Adjust end_time so we don't cut in the middle of active speech if a silence is nearby
        nearby_silence = next((s for s in silences if abs(s["start"] - candidate_end) < 2.5), None)
        if nearby_silence and (start_time + min_len) <= nearby_silence["start"] <= (start_time + max_len):
            end_time = nearby_silence["start"]
        else:
            end_time = candidate_end
        
        seg_duration = end_time - start_time
        if seg_duration >= min_len:
            candidates.append({
                "short_id": index,
                "start": round(start_time, 2),
                "end": round(end_time, 2),
                "duration": round(seg_duration, 2),
                "silence_count": sum(1 for s in silences if s["start"] >= start_time and s["end"] <= end_time)
            })
            index += 1
            
        current_time += step
        if current_time >= duration - 12.0:
            break
            
    return candidates
