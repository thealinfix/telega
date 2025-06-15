"""
Scheduling models
"""
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

from .post import Post


@dataclass
class ScheduledPost:
    """Scheduled post data"""
    time: str  # ISO format datetime
    record: Post
    
    def get_datetime(self) -> datetime:
        """Get scheduled datetime"""
        return datetime.fromisoformat(self.time.replace('Z', '+00:00'))
    
    def is_ready(self) -> bool:
        """Check if post is ready to be published"""
        return datetime.utcnow() >= self.get_datetime()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "time": self.time,
            "record": self.record.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledPost':
        """Create from dictionary"""
        return cls(
            time=data["time"],
            record=Post.from_dict(data["record"])
        )