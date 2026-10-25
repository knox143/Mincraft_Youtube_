"""
Storage Cleaner Module for Minecraft YouTube Shorts Pipeline
Handles automatic memory and disk management:
- Automatically deletes all shorts of old long videos when a new long video is processed
- Cleans intermediate temporary render files (saving ~170MB per rendered short)
- Frees gigabytes of disk space and keeps the output library organized
"""
import os
import shutil
import stat
from pathlib import Path
from typing import Dict, Any, List, Optional
import config


def _handle_remove_readonly(func, path, exc):
    """Clears read-only attributes on Windows files so shutil.rmtree succeeds."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _get_target_dirs(primary_dir: Path, fallback_name: str) -> List[Path]:
    """Returns unique list of paths to check (both config path and base dir)."""
    dirs = [primary_dir, config.BASE_DIR / fallback_name]
    res = []
    for d in dirs:
        if d not in res and d.exists():
            res.append(d)
    return res


def get_dir_size_bytes(directory: Path) -> int:
    """Recursively calculates total byte size of files in a directory."""
    if not directory.exists():
        return 0
    total = 0
    try:
        for f in directory.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def get_storage_stats() -> Dict[str, Any]:
    """
    Returns current disk space usage and folder statistics for output and temp directories.
    """
    out_dirs = _get_target_dirs(config.OUTPUT_DIR, "output")
    temp_dirs = _get_target_dirs(config.TEMP_DIR, "temp")
    
    output_bytes = sum(get_dir_size_bytes(d) for d in out_dirs)
    temp_bytes = sum(get_dir_size_bytes(d) for d in temp_dirs)
    
    # Group shorts by source video
    video_groups: Dict[str, int] = {}
    total_short_folders = 0
    
    for d in out_dirs:
        for item in d.iterdir():
            if item.is_dir() and item.name != ".git":
                total_short_folders += 1
                # Extract source stem (format: "{video_stem}_Short_{id}")
                if "_Short_" in item.name:
                    stem = item.name.split("_Short_")[0]
                    video_groups[stem] = video_groups.get(stem, 0) + 1
                else:
                    video_groups[item.name] = video_groups.get(item.name, 0) + 1

    return {
        "output_size_mb": round(output_bytes / (1024 * 1024), 2),
        "temp_size_mb": round(temp_bytes / (1024 * 1024), 2),
        "total_size_mb": round((output_bytes + temp_bytes) / (1024 * 1024), 2),
        "total_short_folders": total_short_folders,
        "video_groups": video_groups
    }


def cleanup_temp_cache() -> float:
    """
    Removes intermediate rendering temp folders and files in config.TEMP_DIR.
    Returns freed megabytes.
    """
    freed_bytes = 0
    temp_dirs = _get_target_dirs(config.TEMP_DIR, "temp")
    
    for d in temp_dirs:
        for item in d.iterdir():
            if item.name == ".gitkeep":
                continue
            try:
                if item.is_dir():
                    size = get_dir_size_bytes(item)
                    shutil.rmtree(item, onerror=_handle_remove_readonly)
                    freed_bytes += size
                elif item.is_file():
                    size = item.stat().st_size
                    item.unlink(missing_ok=True)
                    freed_bytes += size
            except Exception as e:
                print(f"[StorageCleaner] Temp cleanup note for {item.name}: {e}")
                
    return round(freed_bytes / (1024 * 1024), 2)


def cleanup_old_shorts(
    current_source_video: Optional[str] = None,
    delete_current_too: bool = False,
    clean_temp: bool = True
) -> Dict[str, Any]:
    """
    Automatically deletes all shorts of previous long videos from output directories
    and cleans up any lingering intermediate files in temp directories.
    
    :param current_source_video: Path or filename of the new long video being processed.
           If provided, shorts belonging to OTHER/OLD videos are deleted, while the
           current video's shorts are kept intact (unless delete_current_too=True).
    :param delete_current_too: If True, deletes all shorts including the current video's.
    :param clean_temp: If True, also clears intermediate render cache in temp directories.
    :return: Summary dict with count of deleted folders and freed disk space in MB.
    """
    current_stem = Path(current_source_video).stem if current_source_video else None
    deleted_folders: List[str] = []
    freed_bytes = 0
    
    out_dirs = _get_target_dirs(config.OUTPUT_DIR, "output")
    
    print("\n=======================================================")
    print("[StorageCleaner] CHECKING FOR OLD VIDEO SHORTS")
    print("=======================================================")
    if current_stem:
        print(f"[StorageCleaner] Active Long Video: '{current_stem}'")
        if delete_current_too:
            print(f"[StorageCleaner] Action: Deleting ALL previous shorts including '{current_stem}' for a fresh start.")
        else:
            print(f"[StorageCleaner] Action: Preserving '{current_stem}' shorts; deleting all other old videos' shorts.")
    else:
        print("[StorageCleaner] Action: Cleaning ALL previous shorts from output library...")

    # 1. Clean old shorts from output directories
    for d in out_dirs:
        for item in d.iterdir():
            if not item.is_dir() or item.name == ".git":
                continue
                
            # Check if this folder belongs to the current video
            # Standard naming convention: f"{video_stem}_Short_{id}"
            is_current_video = False
            if current_stem:
                if item.name.startswith(f"{current_stem}_Short_") or item.name == current_stem:
                    is_current_video = True
                    
            # Decide whether to delete
            should_delete = False
            if delete_current_too:
                should_delete = True
            elif current_stem and not is_current_video:
                should_delete = True
            elif not current_stem:
                should_delete = True
                
            if should_delete:
                folder_size = get_dir_size_bytes(item)
                freed_bytes += folder_size
                deleted_folders.append(item.name)
                try:
                    shutil.rmtree(item, onerror=_handle_remove_readonly)
                    print(f"[StorageCleaner] Deleted old short folder: {item.name} (Freed {folder_size / (1024 * 1024):.1f} MB)")
                except Exception as e:
                    print(f"[StorageCleaner] Error removing {item.name}: {e}")

    # 2. Clean temporary render cache if requested
    temp_freed_mb = 0.0
    if clean_temp:
        temp_freed_mb = cleanup_temp_cache()
        freed_bytes += int(temp_freed_mb * 1024 * 1024)

    total_freed_mb = round(freed_bytes / (1024 * 1024), 2)
    
    if deleted_folders or temp_freed_mb > 0:
        print(f"[StorageCleaner] Cleaned: Removed {len(deleted_folders)} old folder(s) | Total freed: {total_freed_mb} MB")
    else:
        print("[StorageCleaner] Storage is already clean. No old video shorts found.")
    print("=======================================================\n")
    
    return {
        "success": True,
        "current_stem": current_stem,
        "deleted_count": len(deleted_folders),
        "deleted_folders": deleted_folders,
        "freed_mb": total_freed_mb,
        "temp_freed_mb": temp_freed_mb
    }
