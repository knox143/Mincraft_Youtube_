"""
VoiceStudio & Neural AI Voiceover Module for Minecraft YouTube Shorts
Supports:
1. Local VoiceStudio Desktop App (https://github.com/debpalash/VoiceStudio) via local REST API
2. Free, high-speed Edge-TTS Neural Voice Engine (Zero API key, ultra-natural YouTuber voices)
3. Scene-based AI commentary script generator (Hinglish / English Gaming / Funny Roast)
4. Intelligent audio mixing & ducking (original voice removal or game SFX preservation)
"""
import os
import asyncio
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
import config
from modules.ai_engine import call_gemini_api


VOICE_PRESETS = {
    "en_gamer_hype": {
        "name": "Christopher (US Gamer Hype)",
        "edge_voice": "en-US-ChristopherNeural",
        "rate": "+10%",
        "pitch": "+2Hz"
    },
    "en_energetic": {
        "name": "Guy (US Energetic Narrator)",
        "edge_voice": "en-US-GuyNeural",
        "rate": "+8%",
        "pitch": "+0Hz"
    },
    "hi_gamer_pro": {
        "name": "Madhur (Hindi Pro Gamer)",
        "edge_voice": "hi-IN-MadhurNeural",
        "rate": "+12%",
        "pitch": "+1Hz"
    },
    "hi_female_gamer": {
        "name": "Swara (Hindi Energetic)",
        "edge_voice": "hi-IN-SwaraNeural",
        "rate": "+10%",
        "pitch": "+0Hz"
    },
    "en_deep_epic": {
        "name": "Brian (Deep Dramatic / Phonk)",
        "edge_voice": "en-US-BrianMultilingualNeural",
        "rate": "+0%",
        "pitch": "-4Hz"
    }
}


def generate_scene_commentary_script(
    short_info: Dict[str, Any],
    language: str = "hinglish",
    style: str = "energetic_gaming",
    api_key: str = ""
) -> str:
    """
    Generates a high-retention 15-25 word voiceover script tailored to the Minecraft scene.
    Optimized for high APV (Average Percentage Viewed) on YouTube Shorts.
    """
    title = short_info.get("highlight_title", "Insane Minecraft Moment")
    hook = short_info.get("hook_text", "WAIT FOR THE END!")
    duration = float(short_info.get("duration", 30.0))
    is_troll = short_info.get("is_troll_moment", True)

    prompt = f"""
Write an ULTRA HIGH RETENTION YouTube Shorts voiceover commentary for this Minecraft clip:
- Highlight Theme: {title}
- Hook: {hook}
- Clip Duration: {duration} seconds
- Scene Type: {"Troll/Clutch surprise moment" if is_troll else "Epic Action moment"}
- Language: {language} (e.g. natural energetic Hinglish gamer or English hype)
- Style: {style} (Excited YouTuber, dramatic buildup, funny troll reaction)

Rules:
1. Length: Exactly 2 to 3 punchy sentences (around 20-35 words total).
2. Start with an immediate curiosity hook ("Bhai ye dekho kya hua..." or "Bro thought he was completely safe...").
3. End with suspense or funny punchline right as the troll / clutch hits.
4. Return ONLY the plain spoken text without quotes or stage directions.
"""
    ai_resp = call_gemini_api(prompt, api_key=api_key)
    if isinstance(ai_resp, dict) and "text" in ai_resp and ai_resp["text"]:
        script = ai_resp["text"].strip()
    elif isinstance(ai_resp, dict) and "candidates" in ai_resp:
        try:
            script = ai_resp["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            script = ""
    else:
        script = ""

    # Fallback high-retention gaming templates if AI is offline
    if not script or len(script) < 10:
        if "hi" in language.lower():
            if is_troll:
                script = "Bhai ye banda soch raha tha ye bilkul safe hai... Par aage jo iske sath hua na, bhai ka reaction dekhne layaq tha! WAIT FOR THE END!"
            else:
                script = "Bhai ye Minecraft ka ab tak ka sabse insane clutch hone wala hai! Dhyan se dekhna... Aur ye BOOM!"
        else:
            if is_troll:
                script = "Bro thought he was completely invincible right here... But watch closely what snuck up behind him! WAIT FOR IT!"
            else:
                script = "This is officially one of the most insane clutch plays in Minecraft history! Watch the crosshair... BOOM!"

    return script.strip('"').strip("'")


async def _synthesize_edge_tts(text: str, voice: str, rate: str, pitch: str, output_path: str):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await comm.save(output_path)


def synthesize_voiceover(
    text: str,
    voice_key: str = "en_gamer_hype",
    output_audio_path: str = None,
    voicestudio_url: str = "http://127.0.0.1:8000"
) -> Optional[str]:
    """
    Synthesizes speech for the commentary script.
    Tries VoiceStudio local REST API first, then falls back to Edge-TTS.
    """
    if not text:
        return None

    if not output_audio_path:
        output_audio_path = str(config.TEMP_DIR / "ai_voiceover.mp3")

    Path(output_audio_path).parent.mkdir(parents=True, exist_ok=True)

    # 1. Check VoiceStudio Local API (https://github.com/debpalash/VoiceStudio)
    try:
        vs_endpoint = f"{voicestudio_url.rstrip('/')}/api/tts/generate"
        payload = {"text": text, "speed": 1.1, "format": "mp3"}
        resp = requests.post(vs_endpoint, json=payload, timeout=2.0)
        if resp.status_code == 200:
            with open(output_audio_path, "wb") as f:
                f.write(resp.content)
            print(f"[VoiceStudio] Voice synthesized via VoiceStudio Local API: {output_audio_path}")
            return output_audio_path
    except Exception:
        pass  # VoiceStudio not running locally, seamlessly fallback to Edge-TTS

    # 2. High-Quality Edge Neural TTS Engine (Free, built-in, fast)
    preset = VOICE_PRESETS.get(voice_key, VOICE_PRESETS["en_gamer_hype"])
    edge_voice = preset.get("edge_voice", "en-US-ChristopherNeural")
    rate = preset.get("rate", "+10%")
    pitch = preset.get("pitch", "+0Hz")

    try:
        print(f"[VoiceStudio] Synthesizing speech with {preset['name']}...")
        asyncio.run(_synthesize_edge_tts(text, edge_voice, rate, pitch, output_audio_path))
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print(f"[VoiceStudio] Speech generated successfully: {output_audio_path}")
            return output_audio_path
    except Exception as e:
        print(f"[VoiceStudio] Edge-TTS note: {e}")

    return None


def prepare_dubbed_audio(
    source_video_clip: str,
    voiceover_path: Optional[str],
    bgm_path: Optional[str],
    sfx_path: Optional[str],
    sfx_offset_sec: float,
    output_audio_path: str,
    voice_mode: str = "mix_ducked",
    video_duration: float = 30.0
) -> bool:
    """
    Mixes and masters audio streams according to scene requirements:
    - voice_mode:
        'replace': Mute original speech/audio, use new AI voiceover + BGM + SFX
        'mix_ducked': Duck original audio by -12dB when AI voiceover speaks, keep Minecraft game hits
        'original': Keep original audio untouched, add subtle BGM & SFX
    """
    inputs = ["-i", str(source_video_clip)]
    filter_parts = []
    current_stream_idx = 1
    
    # 0:a = Original video audio
    if voice_mode == "replace":
        # Mute original video entirely
        filter_parts.append("[0:a]volume=0.0[orig_a];")
    elif voice_mode == "mix_ducked":
        # Keep original game hits at -8dB with high-pass to remove mic rumble
        filter_parts.append("[0:a]volume=0.35,highpass=f=80[orig_a];")
    else:
        filter_parts.append("[0:a]volume=1.0[orig_a];")
        
    mix_sources = ["[orig_a]"]

    # Voiceover input
    has_vo = voiceover_path and os.path.exists(voiceover_path)
    if has_vo:
        inputs.extend(["-i", str(voiceover_path)])
        # AI Voiceover: Loud, punchy, compressed broadcast curve (at 0dB)
        vo_idx = current_stream_idx
        filter_parts.append(f"[{vo_idx}:a]volume=1.35,loudnorm=I=-14:TP=-1.5[vo_a];")
        mix_sources.append("[vo_a]")
        current_stream_idx += 1

    # Background Music (BGM)
    has_bgm = bgm_path and os.path.exists(bgm_path)
    if has_bgm:
        inputs.extend(["-i", str(bgm_path)])
        bgm_idx = current_stream_idx
        # BGM: Ducked in background (-22dB) with subtle bass punch
        filter_parts.append(f"[{bgm_idx}:a]aloop=loop=-1:size=2e+09,volume=0.18,bass=g=3:f=90[bgm_a];")
        mix_sources.append("[bgm_a]")
        current_stream_idx += 1

    # Sound Effect (SFX) at troll moment
    has_sfx = sfx_path and os.path.exists(sfx_path)
    if has_sfx and sfx_offset_sec >= 0:
        inputs.extend(["-i", str(sfx_path)])
        sfx_idx = current_stream_idx
        delay_ms = int(max(0.0, sfx_offset_sec) * 1000)
        # Delay SFX to trigger right at the troll moment
        filter_parts.append(f"[{sfx_idx}:a]adelay={delay_ms}|{delay_ms},volume=1.2[sfx_a];")
        mix_sources.append("[sfx_a]")
        current_stream_idx += 1

    # Mix all audio sources together
    num_inputs = len(mix_sources)
    filter_parts.append(f"{''.join(mix_sources)}amix=inputs={num_inputs}:duration=first:dropout_transition=2,volume=1.25[final_a]")
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", "".join(filter_parts),
        "-map", "[final_a]",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-t", str(video_duration),
        str(output_audio_path)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        print(f"[VoiceStudio] Mastered audio mix created: {output_audio_path}")
        return True
    else:
        print(f"[VoiceStudio] Audio mix note: {res.stderr[:200]}")
        return False
