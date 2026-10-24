"""
Minecraft YouTube Shorts Web Dashboard
Flask Backend: UI controls, scanning, live progress, video streaming, and metadata copying.
"""
import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
import config
from pipeline import MinecraftShortsPipeline
from modules.opencut_bridge import generate_opencut_project

app = Flask(__name__)
pipeline = MinecraftShortsPipeline()

CURRENT_MANIFEST = None


@app.route("/")
def index():
    # Scan input directory for available videos
    input_files = []
    if config.INPUT_DIR.exists():
        for ext in ("*.mp4", "*.mkv", "*.mov", "*.avi"):
            for f in config.INPUT_DIR.glob(ext):
                input_files.append({
                    "name": f.name,
                    "path": f.as_posix(),
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2)
                })
                
    # Scan output directory for existing rendered shorts
    rendered_shorts = []
    if config.OUTPUT_DIR.exists():
        for folder in config.OUTPUT_DIR.iterdir():
            if folder.is_dir():
                mp4s = list(folder.glob("*.mp4"))
                meta_json = folder / "metadata.json"
                if mp4s:
                    meta = {}
                    if meta_json.exists():
                        try:
                            meta = json.loads(meta_json.read_text(encoding="utf-8"))
                        except Exception:
                            pass
                    has_opencut = (folder / "opencut_project.json").exists()
                    rendered_shorts.append({
                        "folder": folder.name,
                        "video_filename": mp4s[0].name,
                        "video_url": f"/stream/{folder.name}/{mp4s[0].name}",
                        "metadata": meta,
                        "has_opencut": has_opencut,
                        "opencut_url": f"/api/opencut/project/{folder.name}"
                    })
                    
    return render_template(
        "index.html",
        input_files=input_files,
        rendered_shorts=rendered_shorts,
        config={
            "input_dir": str(config.INPUT_DIR),
            "output_dir": str(config.OUTPUT_DIR),
            "layout_mode": config.DEFAULT_LAYOUT_MODE,
            "enable_hook": config.ENABLE_HOOK_TEASER,
            "enable_grading": config.ENABLE_COLOR_GRADING,
            "enable_subtitles": config.ENABLE_SUBTITLES,
            "has_api_key": bool(config.GEMINI_API_KEY)
        }
    )


@app.route("/api/scan", methods=["POST"])
def api_scan():
    global CURRENT_MANIFEST
    data = request.json or {}
    video_path = data.get("video_path")
    api_key = data.get("api_key", "")
    
    if api_key:
        pipeline.api_key = api_key
        
    target_dur = data.get("target_duration")
    if target_dur:
        try:
            config.TARGET_SHORT_DURATION = float(target_dur)
        except Exception:
            pass

    hook_dur = data.get("hook_duration")
    if hook_dur:
        try:
            config.HOOK_DURATION_SEC = float(hook_dur)
        except Exception:
            pass
        
    if not video_path or not Path(video_path).exists():
        return jsonify({"success": False, "error": "Video file not found."}), 400
        
    try:
        manifest = pipeline.estimate_shorts(video_path)
        CURRENT_MANIFEST = manifest
        return jsonify({"success": True, "manifest": manifest})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/render", methods=["POST"])
def api_render():
    global CURRENT_MANIFEST
    data = request.json or {}
    selected_ids = data.get("selected_ids", [])
    layout_mode = data.get("layout_mode", config.DEFAULT_LAYOUT_MODE)
    
    if not CURRENT_MANIFEST:
        return jsonify({"success": False, "error": "No video scanned yet."}), 400
        
    try:
        results = pipeline.render_pipeline(
            manifest=CURRENT_MANIFEST,
            selected_ids=selected_ids if selected_ids else None,
            layout_mode=layout_mode
        )
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/stream/<folder>/<filename>")
def stream_video(folder, filename):
    folder_path = config.OUTPUT_DIR / folder
    return send_from_directory(folder_path, filename)


@app.route("/api/opencut/project/<folder>")
def get_opencut_project(folder):
    folder_path = config.OUTPUT_DIR / folder
    proj_path = folder_path / "opencut_project.json"
    if proj_path.exists():
        return send_from_directory(folder_path, "opencut_project.json", as_attachment=True)
    return jsonify({"error": "OpenCut project file not found"}), 404


@app.route("/api/opencut/export_candidate", methods=["POST"])
def export_candidate_opencut():
    global CURRENT_MANIFEST
    data = request.json or {}
    short_id = data.get("short_id")
    if not CURRENT_MANIFEST or "shorts" not in CURRENT_MANIFEST:
        return jsonify({"success": False, "error": "No scan manifest available"}), 400
        
    short = next((s for s in CURRENT_MANIFEST["shorts"] if s["short_id"] == short_id), None)
    if not short:
        return jsonify({"success": False, "error": f"Short #{short_id} not found"}), 404
        
    video_stem = Path(CURRENT_MANIFEST["source_video"]).stem
    out_folder = config.OUTPUT_DIR / f"{video_stem}_Short_{short_id}"
    out_file = out_folder / "opencut_project.json"
    
    proj = generate_opencut_project(short, CURRENT_MANIFEST["source_video"], str(out_file))
    return jsonify({
        "success": True,
        "project": proj,
        "download_url": f"/api/opencut/project/{video_stem}_Short_{short_id}"
    })


if __name__ == "__main__":
    print(f"\n=======================================================")
    print(f"🔥 MINECRAFT SHORTS PIPELINE WEB DASHBOARD LAUNCHED")
    print(f"🌐 Access Web Dashboard: http://{config.WEB_HOST}:{config.WEB_PORT}")
    print(f"=======================================================\n")
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False)
