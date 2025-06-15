"""
Tag extraction service
"""
from typing import List

from ..config.constants import (
    BRAND_KEYWORDS, MODEL_KEYWORDS, RELEASE_TYPES, COLOR_KEYWORDS
)
from ..models.post import PostTags


class TagExtractor:
    """Extract tags from post content"""
    
    @staticmethod
    def extract_tags(title: str, context: str = "") -> PostTags:
        """Extract tags from title and context"""
        text = f"{title} {context}".lower()
        
        tags = PostTags()
        
        # Extract brands
        for brand, keywords in BRAND_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if brand not in tags.brands:
                        tags.brands.append(brand)
                    break
        
        # Extract models
        for model, keywords in MODEL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if model not in tags.models:
                        tags.models.append(model)
                    break
        
        # Extract release types
        for release_type, keywords in RELEASE_TYPES.items():
            for keyword in keywords:
                if keyword in text:
                    if release_type not in tags.types:
                        tags.types.append(release_type)
                    break
        
        # Extract colors
        tags.colors = TagExtractor._extract_colors(text)
        
        return tags
    
    @staticmethod
    def _extract_colors(text: str) -> List[str]:
        """Extract color tags from text"""
        found_colors = []
        
        # Map non-English colors to English
        color_map = {
            "черный": "black",
            "белый": "white",
            "красный": "red",
            "синий": "blue",
            "зеленый": "green",
            "желтый": "yellow",
            "фиолетовый": "purple",
            "розовый": "pink",
            "оранжевый": "orange",
            "серый": "gray"
        }
        
        english_colors = [
            "black", "white", "red", "blue", "green", "yellow", 
            "purple", "pink", "orange", "grey", "gray"
        ]
        
        for color in COLOR_KEYWORDS:
            if color in text:
                # Map to English if needed
                english_color = color_map.get(color, color)
                
                # Normalize gray/grey
                if english_color == "grey":
                    english_color = "gray"
                
                if english_color in english_colors and english_color not in found_colors:
                    found_colors.append(english_color)
        
        return found_colors
    
    @staticmethod
    def matches_filter(tags: PostTags, filter_type: str, filter_value: str) -> bool:
        """Check if tags match filter"""
        if filter_type == "brand":
            return filter_value in tags.brands
        elif filter_type == "model":
            return filter_value in tags.models
        elif filter_type == "type":
            return filter_value in tags.types
        elif filter_type == "color":
            return filter_value in tags.colors
        
        return False
    
    @staticmethod
    def get_all_unique_tags(posts: dict) -> dict:
        """Get all unique tags from posts"""
        all_brands = set()
        all_models = set()
        all_types = set()
        all_colors = set()
        
        for post in posts.values():
            if post.tags:
                all_brands.update(post.tags.brands)
                all_models.update(post.tags.models)
                all_types.update(post.tags.types)
                all_colors.update(post.tags.colors)
        
        return {
            "brands": sorted(list(all_brands)),
            "models": sorted(list(all_models)),
            "types": sorted(list(all_types)),
            "colors": sorted(list(all_colors))
        }