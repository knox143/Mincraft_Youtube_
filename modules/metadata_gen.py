"""
Metadata Generator Module: Creates high-CTR YouTube Titles,
Ranked SEO Tags, and Descriptions for Shorts.
"""
import json
from pathlib import Path
from typing import Dict, Any, List


def format_metadata_package(
    short_info: Dict[str, Any],
    output_dir: str
) -> Dict[str, Any]:
    """
    Produces complete metadata package:
    - 3 Click-worthy title options
    - 15+ high-volume tags
    - Formatted description
    - Saves metadata.json & metadata.txt to output_dir
    """
    titles = short_info.get("titles", [])
    if not titles:
        titles = [
            f"The Craziest Minecraft Moment Ever! 😱 #shorts",
            f"Bro Thought He Was Safe In Minecraft 💀 #shorts",
            f"Top 1% Minecraft Clutch You Won't Believe! 🔥 #shorts"
        ]
        
    tags = short_info.get("tags", [])
    if not tags:
        tags = [
            "minecraft", "minecraft shorts", "minecraft clutch", "funny minecraft",
            "minecraft fail", "minecraft hardcore", "minecraft memes", "gaming", "shorts",
            "viral shorts", "trending gaming", "minecraft pvp", "minecraft tips"
        ]
        
    primary_title = titles[0]
    tags_comma_separated = ", ".join(tags)
    
    description = (
        f"{primary_title}\n\n"
        f"Subscribe for more daily Minecraft shorts, clutches, and epic gameplay moments! 🔔\n\n"
        f"#shorts #minecraft #gaming #minecraftmemes #minecraftclutch #viral"
    )
    
    metadata = {
        "short_id": short_info.get("short_id", 1),
        "primary_title": primary_title,
        "title_options": titles,
        "tags_list": tags,
        "tags_comma_separated": tags_comma_separated,
        "description": description,
        "viral_score": short_info.get("viral_score", 85),
        "virality_tier": short_info.get("virality_tier", "High")
    }
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    json_file = out_path / "metadata.json"
    json_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Save TXT for easy 1-click copy
    txt_file = out_path / "metadata.txt"
    txt_content = f"""==================================================
YOUTUBE SHORTS METADATA PACKAGE - SHORT #{metadata['short_id']}
Viral Score: {metadata['viral_score']}% ({metadata['virality_tier']})
==================================================

[TITLE CHOICES (Pick One)]:
Option 1: {titles[0] if len(titles) > 0 else ''}
Option 2: {titles[1] if len(titles) > 1 else ''}
Option 3: {titles[2] if len(titles) > 2 else ''}

[DESCRIPTION]:
{description}

[YOUTUBE TAGS (Copy & Paste directly into YouTube Studio)]:
{tags_comma_separated}
==================================================
"""
    txt_file.write_text(txt_content, encoding="utf-8")
    
    return metadata
