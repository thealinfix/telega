"""
Post data models
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any


@dataclass
class PostTags:
    """Tags extracted from post content"""
    brands: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary"""
        return {
            "brands": self.brands,
            "models": self.models,
            "types": self.types,
            "colors": self.colors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[str]]) -> 'PostTags':
        """Create from dictionary"""
        return cls(
            brands=data.get("brands", []),
            models=data.get("models", []),
            types=data.get("types", []),
            colors=data.get("colors", [])
        )


@dataclass
class Post:
    """Post data model"""
    id: str
    title: str
    link: str
    source: str
    category: str = "sneakers"
    timestamp: str = ""
    description: str = ""
    context: str = ""
    images: List[str] = field(default_factory=list)
    original_images: List[str] = field(default_factory=list)
    tags: Optional[PostTags] = None
    needs_parsing: bool = True
    
    def __post_init__(self):
        """Post initialization"""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.original_images and self.images:
            self.original_images = self.images.copy()
        if not self.tags:
            self.tags = PostTags()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "category": self.category,
            "timestamp": self.timestamp,
            "description": self.description,
            "context": self.context,
            "images": self.images,
            "original_images": self.original_images,
            "tags": self.tags.to_dict() if self.tags else {},
            "needs_parsing": self.needs_parsing
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create from dictionary"""
        tags_data = data.get("tags", {})
        tags = PostTags.from_dict(tags_data) if tags_data else PostTags()
        
        return cls(
            id=data["id"],
            title=data["title"],
            link=data["link"],
            source=data.get("source", "Unknown"),
            category=data.get("category", "sneakers"),
            timestamp=data.get("timestamp", ""),
            description=data.get("description", ""),
            context=data.get("context", ""),
            images=data.get("images", []),
            original_images=data.get("original_images", []),
            tags=tags,
            needs_parsing=data.get("needs_parsing", True)
        )
    
    def get_hashtags(self) -> str:
        """Get hashtags for the post"""
        from ..utils.formatters import get_hashtags_for_post
        return get_hashtags_for_post(self.title, self.category)
    
    def format_for_channel(self) -> str:
        """Format post for channel publication"""
        from ..utils.formatters import format_post_for_channel
        return format_post_for_channel(self)


@dataclass
class ThoughtPost:
    """Thought post data model"""
    text: str
    topic: str
    image_url: Optional[str] = None
    image_description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "text": self.text,
            "topic": self.topic,
            "image_url": self.image_url,
            "image_description": self.image_description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtPost':
        """Create from dictionary"""
        return cls(
            text=data["text"],
            topic=data["topic"],
            image_url=data.get("image_url"),
            image_description=data.get("image_description")
        )