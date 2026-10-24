# ⛏️ Minecraft YouTube Shorts AI Automation Pipeline

An autonomous end-to-end pipeline designed to convert long Minecraft gameplay videos into high-retention, algorithm-optimized **9:16 vertical YouTube Shorts** (`1080x1920`).

---

## 🌟 Core Features (Features Ki Poori Jankari)

1. **AI Highlight Detection (~30s Short Duration Target)**:
   - Scans long video audio energy, action velocity, and silence gaps.
   - Evaluates Minecraft-specific moments: clutches, jumpscares, funny fails, diamond/netherite findings, boss fights, and high-tension PvP.
   - Optimized for new channels: targets **~30-second clips** (Hook 3.5s + Story ~26.5s) to guarantee maximum 100%+ Average Percentage Viewed (APV) retention.

2. **3.5s Hook Detection & Teaser Prepending**:
   - The first 3.5 seconds decide whether a viewer stays or swipes away.
   - The pipeline extracts the full 3.5-second climax/punchline moment and prepends it at `0:00 - 0:03.5` with an animated top callout banner (*"WAIT FOR THE END! 💀"*).

3. **Pro High-Editing & YouTube Reused Content Immunity (Anti-Copy Protection)**:
   - **Multi-layer Cinematic Layout**: Blurred background with cinematic lens vignette (`vignette=PI/4`) + glowing emerald/gold accent frame borders.
   - **Digital Anti-Fingerprint Hash**: Invisible micro-dithering noise alters every pixel's digital hash, preventing automated Content ID "reused content" flags.
   - **Pro Audio Mastering**: Broadcast loudness normalization (`loudnorm` -14 LUFS) + bass subwoofer boost + treble voice clarity + 1.02x tempo micro-shift to reshape the acoustic waveform.
   - **Rapid-fire 2-3 Word Hormozi Captions**: Large bold fonts, active word bounce, neon yellow glow, and context-aware emoji injection (💀, 🌊, 💥, 💎, 🔥) in the vertical safe zone.

4. **Minecraft Color Grading & Sharpening**:
   - Saturation boost (+25%) for vivid block and armor colors.
   - Contrast enhancement (+14%) for deep shadows and rich textures.
   - Unsharp filter for pixel-perfect clarity on mobile AMOLED/Retina screens.

5. **Virality & Ranking Probability Engine (Rank / Viral Prediction)**:
   - Calculates a **0–100% Viral Score**:
     - *Hook Impact* (0–25 pts)
     - *Pacing & Dead Air Reduction* (0–25 pts)
     - *Production Polish* (0–25 pts)
     - *SEO Search & Recommendation Volume* (0–25 pts)
   - **Adaptive Auto-Editing**: If pacing drops, it automatically trims silences (`silenceremove`) and speeds up transitions by 5% to push the retention score into the **High Virality Tier (80%+)**.

6. **Shorts Estimation (Kitne Shorts Generate Ho Sakte Hai)**:
   - Before rendering, the pipeline scans the entire video and outputs:
     - Total number of viable shorts that can be extracted.
     - Exact timestamps and duration for each candidate.
     - Predicted viral chance (%) and ranking tier for every short.

7. **Auto Titles, SEO Tags & Description**:
   - Generates 3 high-CTR title variations (with emojis & hashtags).
   - Generates 15+ ranked YouTube tags formatted for 1-click copy-paste into YouTube Studio.
   - Generates complete description with timestamps and viral hashtags.

8. **GPU Hardware Acceleration**:
   - Uses NVIDIA NVENC (`h264_nvenc`) for ultra-fast rendering on your GTX 1650.

9. **OpenCut (CapCut Alternative) Integration**:
   - Integrated with **[OpenCut](https://github.com/OpenCut-app/OpenCut)** (`opencut.app`), the premier open-source CapCut alternative.
   - For every Short detected or rendered, the pipeline generates a native **`opencut_project.json`** multi-track timeline project (1080x1920 @ 60 FPS) with video tracks, hook teasers, subtitle layers, color grading, and bookmarks.
   - Double-click **`run_opencut.bat`** or click **"✂️ OpenCut Project"** in the Web UI to open or download the project for manual CapCut-style fine-tuning (stickers, meme sound effects, zooms, transitions)!

---

## 📁 Folder Structure

```
D:\Youtube\Minecraft\
├── config.py                 # Core settings (API keys, grading, styles, safe zones)
├── pipeline.py               # Main CLI runner & orchestrator
├── web_app.py                # Modern Web Dashboard (Flask + HTML5/CSS3)
├── run_web_ui.bat            # 1-Click launcher for Web UI
├── run_pipeline.bat          # 1-Click launcher for CLI
├── run_opencut.bat           # 1-Click launcher for OpenCut Video Editor Studio
├── modules/
│   ├── analyzer.py           # FFprobe video & audio energy analyzer
│   ├── ai_engine.py          # Gemini AI & smart heuristic model
│   ├── hook_detector.py      # Climax extraction & teaser prepender
│   ├── subtitle_gen.py       # Hormozi/MrBeast ASS captions generator
│   ├── virality_scorer.py    # Virality probability & ranking evaluator
│   ├── metadata_gen.py       # Titles, tags & description builder
│   ├── video_editor.py       # FFmpeg 9:16 layout, color grading & burn-in engine
│   └── opencut_bridge.py     # OpenCut project timeline exporter
├── opencut/                  # OpenCut source repository (OpenCut-app/OpenCut)
├── input/                    # Place your long Minecraft videos here (.mp4, .mkv)
└── output/                   # Generated shorts with metadata packages & opencut_project.json
```

---

## 🚀 How to Run (Kaise Use Kare)

### Method 1: Web Dashboard (Recommended & Easy)
1. Double-click **`run_web_ui.bat`** (or run `python web_app.py`).
2. Your browser will open **`http://127.0.0.1:5000`**.
3. Place your long video in `D:\Youtube\Minecraft\input\` or enter its full path.
4. Click **🔍 Scan & Estimate Shorts**:
   - It will show how many shorts can be extracted and their viral chances!
5. Click **⚡ Render All Detected Shorts** or **🔥 Render Top 3 Viral Only**.
6. Preview finished shorts in the web player and copy Titles/Tags with 1 click!

### Method 2: Command Line (CLI)
- **Only Estimate Shorts & Virality (No rendering):**
  ```powershell
  python pipeline.py --video "D:\Youtube\Minecraft\input\gameplay.mp4" --estimate
  ```
- **Render Top 3 Highest Viral Potential Shorts:**
  ```powershell
  python pipeline.py --video "D:\Youtube\Minecraft\input\gameplay.mp4" --top 3
  ```
- **Render All Detected Shorts:**
  ```powershell
  python pipeline.py --video "D:\Youtube\Minecraft\input\gameplay.mp4"
  ```
