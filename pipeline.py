"""
Minecraft YouTube Shorts AI Pipeline
Main Pipeline Orchestrator (CLI & Backend Service)
"""
import sys
import os
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

import config
from modules.analyzer import get_video_info, scan_energy_peaks
from modules.ai_engine import analyze_video_highlights_with_ai
from modules.virality_scorer import calculate_viral_score, get_adaptive_editing_rules
from modules.metadata_gen import format_metadata_package
from modules.video_editor import render_short_video
from modules.opencut_bridge import generate_opencut_project


class MinecraftShortsPipeline:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

    def estimate_shorts(self, video_path: str) -> Dict[str, Any]:
        """
        Scans long video, detects how many shorts can be extracted,
        and scores each candidate for virality probability.
        """
        path = Path(video_path)
        if not path.exists():
            return {"error": f"Video file not found: {video_path}"}
            
        print(f"\n=======================================================")
        print(f"🎬 SCANNING VIDEO: {path.name}")
        print(f"=======================================================")
        
        info = get_video_info(str(path))
        duration = info.get("duration", 0.0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        print(f"⏱️ Duration: {minutes}m {seconds}s ({duration:.1f}s) | Resolution: {info.get('width')}x{info.get('height')}")
        
        # Scan for highlights
        candidates = scan_energy_peaks(str(path), duration)
        print(f"🔍 Found {len(candidates)} candidate highlight segments.")
        
        # AI / Heuristic Analysis
        analyzed_shorts = analyze_video_highlights_with_ai(info, candidates, api_key=self.api_key)
        
        # Calculate Virality & Ranking scores
        results = []
        for s in analyzed_shorts:
            dur = s.get("duration", 45.0)
            v_score_data = calculate_viral_score(
                duration=dur,
                silence_count=s.get("silence_count", 1),
                has_hook_teaser=config.ENABLE_HOOK_TEASER,
                has_animated_subtitles=config.ENABLE_SUBTITLES,
                has_color_grading=config.ENABLE_COLOR_GRADING
            )
            # Merge score
            s["viral_score"] = v_score_data["viral_score"]
            s["virality_tier"] = v_score_data["virality_tier"]
            s["badge"] = v_score_data["badge"]
            s["rank_prediction"] = v_score_data["rank_prediction"]
            s["adaptive_rules"] = get_adaptive_editing_rules(s["viral_score"])
            results.append(s)
            
        # Sort by viral score descending
        results.sort(key=lambda x: x["viral_score"], reverse=True)
        
        manifest = {
            "source_video": str(path),
            "video_info": info,
            "total_shorts_possible": len(results),
            "high_virality_count": sum(1 for r in results if r["virality_tier"] == "High"),
            "medium_virality_count": sum(1 for r in results if r["virality_tier"] == "Medium"),
            "shorts": results
        }
        
        return manifest

    def render_pipeline(
        self,
        manifest: Dict[str, Any],
        selected_ids: List[int] = None,
        layout_mode: str = config.DEFAULT_LAYOUT_MODE
    ) -> List[Dict[str, Any]]:
        """Renders the selected or all candidate shorts."""
        source_video = manifest["source_video"]
        video_stem = Path(source_video).stem
        shorts_list = manifest.get("shorts", [])
        
        if selected_ids:
            targets = [s for s in shorts_list if s["short_id"] in selected_ids]
        else:
            targets = shorts_list
            
        print(f"\n🚀 Rendering {len(targets)} Shorts for '{video_stem}'...")
        completed_shorts = []
        
        for idx, short_data in enumerate(targets, 1):
            short_id = short_data["short_id"]
            out_folder = config.OUTPUT_DIR / f"{video_stem}_Short_{short_id}"
            out_video_path = out_folder / f"short_{short_id}.mp4"
            
            print(f"\n-------------------------------------------------------")
            print(f"[{idx}/{len(targets)}] Rendering Short #{short_id}")
            print(f"Highlight: {short_data.get('highlight_title')}")
            print(f"Viral Score: {short_data.get('viral_score')}% ({short_data.get('badge')})")
            print(f"-------------------------------------------------------")
            
            # Format and save metadata (titles, tags, descriptions)
            metadata = format_metadata_package(short_data, str(out_folder))
            
            # Export OpenCut CapCut-compatible timeline project
            opencut_project_file = out_folder / "opencut_project.json"
            generate_opencut_project(short_data, source_video, str(opencut_project_file))
            
            # Render video
            success = render_short_video(
                source_video=source_video,
                short_info=short_data,
                output_path=str(out_video_path),
                layout_mode=layout_mode,
                enable_hook=config.ENABLE_HOOK_TEASER,
                enable_subtitles=config.ENABLE_SUBTITLES,
                enable_grading=config.ENABLE_COLOR_GRADING,
                use_nvenc=config.USE_NVENC
            )
            
            if success:
                print(f"✅ Finished: {out_video_path}")
                completed_shorts.append({
                    "short_id": short_id,
                    "video_path": str(out_video_path),
                    "metadata": metadata,
                    "status": "SUCCESS"
                })
            else:
                print(f"❌ Failed rendering Short #{short_id}")
                
        return completed_shorts


def main():
    parser = argparse.ArgumentParser(description="Minecraft YouTube Shorts AI Pipeline")
    parser.add_argument("--video", "-v", type=str, help="Path to input video (.mp4/.mkv)")
    parser.add_argument("--estimate", "-e", action="store_true", help="Only estimate possible shorts and viral potential")
    parser.add_argument("--top", "-t", type=int, default=0, help="Generate only top N highest viral score shorts")
    parser.add_argument("--layout", "-l", choices=["blur_background", "center_crop"], default=config.DEFAULT_LAYOUT_MODE)
    parser.add_argument("--key", "-k", type=str, default="", help="Gemini API Key")
    
    args = parser.parse_args()
    
    video_path = args.video
    if not video_path:
        # Check input directory for available videos
        mp4_files = list(config.INPUT_DIR.glob("*.mp4")) + list(config.INPUT_DIR.glob("*.mkv"))
        if mp4_files:
            video_path = str(mp4_files[0])
            print(f"[Auto-Detect] Using input video: {video_path}")
        else:
            print("Usage: python pipeline.py --video <path_to_video>")
            print(f"Or place your long Minecraft videos in: {config.INPUT_DIR}")
            sys.exit(1)
            
    pipeline = MinecraftShortsPipeline(api_key=args.key)
    manifest = pipeline.estimate_shorts(video_path)
    
    print("\n=======================================================")
    print("📊 SHORTS ESTIMATION & VIRAL RANKING REPORT")
    print("=======================================================")
    print(f"Total Shorts Generatable: {manifest['total_shorts_possible']}")
    print(f"🔥 High Viral Probability (>80%): {manifest['high_virality_count']}")
    print(f"🚀 Medium Viral Probability (65-79%): {manifest['medium_virality_count']}")
    print("-------------------------------------------------------")
    
    for s in manifest.get("shorts", []):
        print(f"• Short #{s['short_id']}: [{s['start']}s - {s['end']}s] ({s['duration']}s)")
        print(f"  Highlight: {s.get('highlight_title')}")
        print(f"  Hook Teaser: \"{s.get('hook_text')}\"")
        print(f"  Viral Chance: {s['viral_score']}% -> {s['badge']}")
        print(f"  Top Title: {s['titles'][0] if s.get('titles') else 'N/A'}")
        print()
        
    if args.estimate:
        print("[Estimate Mode] Finished estimation report. Exiting without rendering.")
        return
        
    # Render
    selected_ids = None
    if args.top > 0:
        sorted_shorts = manifest.get("shorts", [])
        selected_ids = [s["short_id"] for s in sorted_shorts[:args.top]]
        print(f"🎯 Selected Top {args.top} highest viral potential shorts: {selected_ids}")
        
    pipeline.render_pipeline(manifest, selected_ids=selected_ids, layout_mode=args.layout)
    print("\n🎉 Pipeline Execution Completed Successfully!")


if __name__ == "__main__":
    main()
