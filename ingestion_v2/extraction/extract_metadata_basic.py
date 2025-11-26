"""
Basic metadata extraction from file info.

No heavy lifting - just file stats and basic info.
"""
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def extract_basic_metadata(file_path: Path) -> Dict:
    """
    Extract basic metadata from file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with basic metadata
    """
    try:
        stat = file_path.stat()
        
        metadata = {
            "file_name": file_path.name,
            "file_stem": file_path.stem,
            "file_extension": file_path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "file_path": str(file_path),
        }
        
        logger.debug(f"Extracted basic metadata for {file_path.name}")
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata for {file_path}: {e}")
        return {
            "file_name": file_path.name,
            "error": str(e),
        }


def extract_path_metadata(file_path: Path, base_path: Optional[Path] = None) -> Dict:
    """
    Extract metadata from file path structure.
    
    Args:
        file_path: Path to file
        base_path: Base path to make relative from
        
    Returns:
        Dictionary with path metadata
    """
    try:
        # Get parent folders
        if base_path and file_path.is_relative_to(base_path):
            relative_path = file_path.relative_to(base_path)
            parent_folders = list(relative_path.parent.parts)
        else:
            # Just get last 3 levels
            parent_folders = list(file_path.parent.parts[-3:])
        
        metadata = {
            "parent_folders": parent_folders,
            "folder_depth": len(parent_folders),
            "immediate_parent": parent_folders[-1] if parent_folders else "",
        }
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting path metadata: {e}")
        return {
            "parent_folders": [],
            "folder_depth": 0,
        }


def combine_metadata(file_path: Path, base_path: Optional[Path] = None) -> Dict:
    """
    Combine all basic metadata.
    
    Args:
        file_path: Path to file
        base_path: Base path for relative path extraction
        
    Returns:
        Combined metadata dictionary
    """
    basic = extract_basic_metadata(file_path)
    path_info = extract_path_metadata(file_path, base_path)
    
    return {**basic, **path_info}