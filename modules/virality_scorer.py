"""
Virality & Ranking Scorer Module:
Evaluates YouTube Shorts algorithm ranking probability based on Retention,
Hook strength, Pacing, and SEO search volume. Applies adaptive edits to boost scores.
"""
from typing import Dict, Any, Tuple
import config


def calculate_viral_score(
    duration: float,
    silence_count: int,
    has_hook_teaser: bool = True,
    has_animated_subtitles: bool = True,
    has_color_grading: bool = True,
    keyword_relevance_score: int = 20
) -> Dict[str, Any]:
    """
    Computes a comprehensive Virality & Ranking Probability (0 - 100%):
    - Hook Impact (0-25)
    - Pacing & Density (0-25)
    - Production Polish (0-25) [Subtitles, 9:16 layout, Color grading]
    - SEO & Topic Appeal (0-25)
    """
    # 1. Hook Impact (0 - 25)
    hook_score = 23 if has_hook_teaser else 12
    
    # 2. Pacing & Retention (0 - 25)
    # Sweet spot duration for new channels: 25s - 33s gives highest APV (>95-120%)
    pacing_score = 22
    if duration < 20.0:
        pacing_score -= 4
    elif duration > 36.0:
        pacing_score -= 6  # Penalty for too long (risk of drop-off on new channel)
    elif 25.0 <= duration <= 33.0:
        pacing_score += 3  # Optimal 30-second target bonus!
        
    if silence_count > 4:
        pacing_score -= 6
    elif silence_count <= 2:
        pacing_score += 3
    pacing_score = max(8, min(25, pacing_score))
    
    # 3. Production Polish (0 - 25)
    polish_score = 0
    if has_animated_subtitles:
        polish_score += 12
    if has_color_grading:
        polish_score += 8
    polish_score += 5  # 9:16 vertical conversion standard
    
    # 4. SEO & Keyword Appeal (0 - 25)
    seo_score = max(10, min(25, keyword_relevance_score))
    
    total_score = hook_score + pacing_score + polish_score + seo_score
    total_score = min(98, max(45, total_score))
    
    if total_score >= config.VIRAL_SCORE_HIGH_THRESHOLD:
        tier = "High"
        badge = "🔥 High Viral Probability"
        rank_prediction = "High chance of getting pushed to YouTube Shorts Feed (Est. 80-110% APV)"
    elif total_score >= config.VIRAL_SCORE_MEDIUM_THRESHOLD:
        tier = "Medium"
        badge = "🚀 Solid Performer"
        rank_prediction = "Good engagement, solid search rank potential for Minecraft keywords"
    else:
        tier = "Low"
        badge = "⚠️ Needs Optimization"
        rank_prediction = "Pacing may cause swipe-aways; recommended to apply adaptive trimming"
        
    return {
        "viral_score": total_score,
        "virality_tier": tier,
        "badge": badge,
        "rank_prediction": rank_prediction,
        "breakdown": {
            "hook_impact": hook_score,
            "pacing_retention": pacing_score,
            "production_polish": polish_score,
            "seo_appeal": seo_score
        }
    }


def get_adaptive_editing_rules(viral_score: int) -> Dict[str, Any]:
    """
    Decides adaptive edits based on virality score:
    If a clip has low/medium score, it triggers tighter cuts, faster pacing,
    and visual curiosity hooks to bring the score above 85.
    """
    if viral_score < 75:
        return {
            "trim_silence": True,
            "boost_grading": True,
            "insert_hook_banner": True,
            "speedup_factor": 1.05,  # Subtle 5% speed boost to increase WPM and retention
            "adaptation_applied": "Applied aggressive silence removal and +5% pacing speedup to boost retention."
        }
    else:
        return {
            "trim_silence": False,
            "boost_grading": False,
            "insert_hook_banner": True,
            "speedup_factor": 1.0,
            "adaptation_applied": "Optimal pacing detected; standard high-definition render applied."
        }
