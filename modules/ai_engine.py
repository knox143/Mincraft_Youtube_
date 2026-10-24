"""
AI Engine Module: Uses Google Gemini API (or heuristic fallback) for highlight detection,
hook pinpointing, virality & ranking probability estimation, and metadata generation.
"""
import json
import os
import requests
from typing import Dict, Any, List
import config


def _clean_json_text(text: str) -> str:
    """Strips markdown code fences and cleans JSON response text."""
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def call_gemini_api(prompt: str, system_instruction: str = "", api_key: str = "") -> Dict[str, Any]:
    """Calls Gemini REST API with JSON response schema and fallback models."""
    key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not key:
        return {"error": "NO_API_KEY"}
        
    models_to_try = [getattr(config, "GEMINI_MODEL", "gemini-1.5-flash"), "gemini-1.5-flash", "gemini-2.0-flash"]
    # Remove duplicates preserving order
    models_to_try = list(dict.fromkeys(models_to_try))
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json"
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                    clean = _clean_json_text(content_text)
                    return json.loads(clean)
            else:
                print(f"[AIEngine] Gemini ({model_name}) HTTP {response.status_code}, trying fallback...")
        except Exception as e:
            print(f"[AIEngine] Gemini ({model_name}) error: {e}")
            
    return {"error": "NO_RESPONSE"}


def transcribe_clip_audio(audio_path: str, api_key: str = "") -> List[Dict[str, Any]]:
    """
    Transcribes spoken words from the audio track using:
    1. Local faster-whisper / whisper (100% offline, free)
    2. Groq Cloud Whisper API (free, fast, whisper-large-v3-turbo)
    3. Google Gemini Audio API (gemini-1.5-flash / gemini-2.0-flash)
    Returns word-by-word / phrase subtitle segments matching speech.
    """
    if not os.path.exists(audio_path):
        return []

    # 1. Local faster-whisper (Offline, Free)
    try:
        from faster_whisper import WhisperModel
        print("[AIEngine] Transcribing with local faster-whisper...")
        model = WhisperModel("tiny", device="cuda" if config.USE_NVENC else "cpu", compute_type="float16")
        segments, _ = model.transcribe(audio_path, word_timestamps=True)
        results = []
        for segment in segments:
            for word in segment.words:
                w_txt = word.word.strip()
                if w_txt:
                    results.append({
                        "start": round(float(word.start), 2),
                        "end": round(float(word.end), 2),
                        "text": w_txt
                    })
        if results:
            print(f"[AIEngine] faster-whisper transcribed {len(results)} words.")
            return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[AIEngine] Local faster-whisper note: {e}")

    # 2. Groq Cloud Whisper API (Free tier from https://console.groq.com)
    groq_key = getattr(config, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            print("[AIEngine] Transcribing via Groq Whisper Large V3 API...")
            headers = {"Authorization": f"Bearer {groq_key}"}
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
                data = {
                    "model": "whisper-large-v3-turbo",
                    "response_format": "verbose_json"
                }
                res = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=30)
                if res.status_code == 200:
                    json_data = res.json()
                    segments = json_data.get("segments", [])
                    groq_results = []
                    for seg in segments:
                        txt = str(seg.get("text", "")).strip()
                        if txt:
                            groq_results.append({
                                "start": round(float(seg.get("start", 0.0)), 2),
                                "end": round(float(seg.get("end", 1.5)), 2),
                                "text": txt
                            })
                    if groq_results:
                        print(f"[AIEngine] Groq Whisper transcribed {len(groq_results)} subtitle segments!")
                        return groq_results
        except Exception as e:
            print(f"[AIEngine] Groq Whisper API note: {e}")

    # 3. Google Gemini Multimodal Audio API
    key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if key:
        import base64
        models = [getattr(config, "GEMINI_MODEL", "gemini-1.5-flash"), "gemini-1.5-flash", "gemini-2.0-flash"]
        models = list(dict.fromkeys(models))
        
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            if len(audio_bytes) < 15 * 1024 * 1024:
                b64_data = base64.b64encode(audio_bytes).decode("utf-8")
                prompt = (
                    "Listen to this Minecraft gameplay audio track carefully. "
                    "Transcribe the EXACT speech, screams, reactions, and commentary spoken in the audio. "
                    "Return ONLY a JSON list of timed subtitle segments: "
                    '[{"start": 0.0, "end": 1.2, "text": "word phrase"}, {"start": 1.2, "end": 2.5, "text": "next phrase"}]'
                )
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "parts": [
                            {"inlineData": {"mimeType": "audio/mp3", "data": b64_data}},
                            {"text": prompt}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json"
                    }
                }
                for mod in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
                    res = requests.post(url, headers=headers, json=payload, timeout=45)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "[]")
                            clean = _clean_json_text(content_text)
                            parsed = json.loads(clean)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                print(f"[AIEngine] Gemini ({mod}) transcribed {len(parsed)} real speech subtitle segments!")
                                return parsed
        except Exception as e:
            print(f"[AIEngine] Gemini Audio API transcription note: {e}")

    return []


def analyze_video_highlights_with_ai(video_info: Dict[str, Any], candidates: List[Dict[str, Any]], api_key: str = "") -> List[Dict[str, Any]]:
    """
    Sends video candidate segments to Gemini to evaluate highlights,
    pinpoint the best 3-second hook for each, calculate virality probability,
    and generate viral titles/tags.
    """
    key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    if not key:
        # Fallback to smart heuristic scoring when offline or no API key set
        return generate_heuristic_highlights(candidates, video_info)
        
    system_prompt = (
        "You are an expert YouTube Shorts Algorithm Strategist & Minecraft Content Editor. "
        "Your goal is to turn long Minecraft gameplay into ultra-viral 9:16 YouTube Shorts. "
        "Target video length is ~30 seconds (optimal for new channels to maximize 100%+ APV retention). "
        "Hook duration is 3.5 seconds (first 3.5s retention teaser)."
    )
    
    prompt = f"""
    Video Filename: {video_info.get('filename')}
    Total Duration: {video_info.get('duration')} seconds
    Candidate Segments found: {json.dumps(candidates)}

    Task:
    For each candidate segment:
    1. Assess highlight quality (clutch play, funny fail, jumpscare, diamond discovery, intense fight, trap).
    2. Pinpoint the exact HOOK moment (a 3.5-second punchline, shocking event, or climax within or near the clip to tease in the first 3.5 seconds).
    3. Calculate 'viral_score' (0 to 100):
       - Retention likelihood (aiming for 100%+ APV on a tight ~30s clip)
       - First 3.5-sec hook impact
       - Minecraft community hype factor
    4. Categorize 'virality_tier': 'High' (score >= 80), 'Medium' (65-79), or 'Low' (<65).
    5. Generate 3 Click-worthy viral Titles (with emojis and #shorts).
    6. Generate 15 SEO Tags for YouTube search & recommendation algorithm ranking.
    7. Provide 4-6 short punchy caption sentences for subtitles.

    Return JSON list of objects matching schema:
    [
      {{
        "short_id": 1,
        "start": 0.0,
        "end": 26.5,
        "duration": 26.5,
        "highlight_title": "Epic Water Bucket Clutch",
        "hook_text": "WAIT FOR THE END! 💀",
        "hook_offset_in_clip": 20.0,
        "viral_score": 92,
        "virality_tier": "High",
        "viral_reasoning": "Tight 30s duration avoids drop-off. 3.5s teaser hook drives 90%+ retention.",
        "titles": [
          "Bro Really Thought He Was Dead... 💀 #minecraft #shorts",
          "The Clutchest Water Bucket in Minecraft History! 🌊 #shorts",
          "NEVER Give Up In Hardcore Minecraft! 🔥 #shorts"
        ],
        "tags": ["minecraft", "minecraft shorts", "minecraft clutch", "funny minecraft", "gaming", "minecraft meme", "shorts", "viral shorts"],
        "subtitles": [
          {{"start": 0.0, "end": 3.5, "text": "I was literally one heart away..."}},
          {{"start": 3.5, "end": 7.0, "text": "And then this happened!"}}
        ]
      }}
    ]
    """
    
    result = call_gemini_api(prompt, system_prompt, api_key=key)
    
    if isinstance(result, list) and len(result) > 0:
        return result
    elif isinstance(result, dict) and "candidates" in result and isinstance(result["candidates"], list):
        return result["candidates"]
        
    # If API fails or rate-limited, fall back safely
    print("[AIEngine] Gemini response not parsed as list, using smart heuristics fallback.")
    return generate_heuristic_highlights(candidates, video_info)


def generate_heuristic_highlights(candidates: List[Dict[str, Any]], video_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generates realistic Minecraft highlight analysis and viral scores without external API."""
    enhanced = []
    
    # Minecraft high-CTR title templates
    title_presets = [
        [
            "He Thought He Was Safe In Minecraft... 💀 #shorts",
            "Top 1% Water Bucket Clutch Moment! 🌊 #minecraft #shorts",
            "This Minecraft Moment Had My Heart PUMPING! 😱 #shorts"
        ],
        [
            "I Found The Rarest Thing In Minecraft?! 💎 #shorts",
            "Mining At Y=-58 Was A Huge Mistake... 💀 #minecraft #shorts",
            "Bro Hit The Jackpot In The Deep Dark! 😱 #shorts"
        ],
        [
            "When Pro Players Panic In Minecraft 😂 #shorts",
            "Wait Till The End Of This Jump... 🏃‍♂️💨 #minecraft #shorts",
            "The Most Illegal Minecraft Glitch Ever! 🤯 #shorts"
        ],
        [
            "Hardcore Day 100 Almost Ended Here... 💀 #shorts",
            "Creeper Jumpscare Caught In 4K! 💥 #minecraft #shorts",
            "Never Trust A Villager In Minecraft 💀 #shorts"
        ]
    ]
    
    hook_texts = [
        "WAIT FOR THE END! 💀",
        "I ALMOST LOST EVERYTHING! 😱",
        "HOW DID I SURVIVE THIS?! 🌊",
        "YOU WON'T BELIEVE THIS... 🤯",
        "BRO REALLY TRIED IT 💀"
    ]
    
    for i, c in enumerate(candidates):
        # Calculate dynamic score based on duration and pacing
        dur = c.get("duration", 42.0)
        silence_count = c.get("silence_count", 2)
        
        # Pacing bonus: fewer long silences = higher score
        base_score = 78 + (i % 4) * 4
        if silence_count <= 2:
            base_score += 6
        if 24.0 <= dur <= 32.0:
            base_score += 5  # Sweet spot for new channel shorts retention (~30s total)
            
        viral_score = min(max(base_score, 62), 95)
        virality_tier = "High" if viral_score >= 80 else ("Medium" if viral_score >= 65 else "Low")
        
        template_idx = i % len(title_presets)
        titles = title_presets[template_idx]
        hook_text = hook_texts[i % len(hook_texts)]
        hook_dur = getattr(config, "HOOK_DURATION_SEC", 3.5)
        
        # Hook climax is usually placed around 75% through the clip
        hook_offset = round(dur * 0.72, 2)
        
        enhanced.append({
            "short_id": c.get("short_id", i + 1),
            "start": c.get("start", 0.0),
            "end": c.get("end", dur),
            "duration": dur,
            "highlight_title": f"Minecraft Highlight #{i + 1}",
            "hook_text": hook_text,
            "hook_offset_in_clip": hook_offset,
            "viral_score": viral_score,
            "virality_tier": virality_tier,
            "viral_reasoning": (
                f"Optimal retention length ({dur}s + {hook_dur}s hook ≈ 30s total). "
                f"Fast pacing with low dead air. Hook text '{hook_text}' (3.5s) drives 90%+ initial retention."
            ),
            "titles": titles,
            "tags": [
                "minecraft", "minecraft shorts", "minecraft clutch", "funny minecraft moments",
                "minecraft fail", "minecraft hardcore", "minecraft memes", "gaming", "shorts",
                "minecraft pvp", "viral shorts", "trending gaming", "minecraft bedrock", "minecraft java"
            ],
            "subtitles": [
                {"start": 0.0, "end": hook_dur, "text": hook_text},
                {"start": 0.0, "end": 4.5, "text": "Look at what happens right now..."},
                {"start": 5.0, "end": 11.0, "text": "I had literally zero chances to live!"},
                {"start": 11.5, "end": 18.0, "text": "Watch this insane play!"},
                {"start": 18.5, "end": 26.0, "text": "Never dig straight down!"}
            ]
        })
        
    # Sort descending by viral_score so top viral candidates appear first
    enhanced.sort(key=lambda x: x["viral_score"], reverse=True)
    return enhanced
