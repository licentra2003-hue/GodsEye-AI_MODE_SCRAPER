"""
Profile Manager for Burn & Rotate Strategy
Manages browser profiles to avoid detection
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ProfileManager:
    """Manages browser profiles with burn & rotate strategy"""
    
    def __init__(self, base_path: str = "/app/profiles"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Profile manager initialized with base path: {self.base_path}")
    
    def get_profile_path(self, job_id: Optional[str] = None) -> str:
        """Generate a unique profile path for a job"""
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        profile_path = self.base_path / job_id
        profile_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created profile path: {profile_path}")
        return str(profile_path)
    
    def cleanup_profile(self, profile_path: str) -> bool:
        """Delete a profile directory completely"""
        try:
            path = Path(profile_path)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                logger.info(f"Successfully cleaned up profile: {profile_path}")
                return True
            else:
                logger.warning(f"Profile path does not exist: {profile_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to cleanup profile {profile_path}: {e}")
            return False
    
    def profile_exists(self, profile_path: str) -> bool:
        """Check if a profile directory exists"""
        return Path(profile_path).exists()
    
    def get_profile_size(self, profile_path: str) -> int:
        """Get the size of a profile directory in bytes"""
        try:
            path = Path(profile_path)
            if not path.exists():
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            return total_size
        except Exception as e:
            logger.error(f"Failed to get profile size for {profile_path}: {e}")
            return 0
    
    def list_profiles(self) -> list:
        """List all existing profile directories"""
        try:
            profiles = []
            for item in self.base_path.iterdir():
                if item.is_dir():
                    profiles.append({
                        'path': str(item),
                        'name': item.name,
                        'size': self.get_profile_size(str(item))
                    })
            return profiles
        except Exception as e:
            logger.error(f"Failed to list profiles: {e}")
            return []
    
    def cleanup_all_profiles(self) -> int:
        """Clean up all profiles - useful for maintenance"""
        try:
            count = 0
            for item in self.base_path.iterdir():
                if item.is_dir():
                    if self.cleanup_profile(str(item)):
                        count += 1
            logger.info(f"Cleaned up {count} profiles")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup all profiles: {e}")
            return 0
