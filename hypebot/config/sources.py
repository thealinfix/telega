#!/usr/bin/env python3
"""
Конфигурация источников данных
"""

# Расширенный список источников
SOURCES = [
    {
        "key": "sneakernews", 
        "name": "SneakerNews", 
        "type": "json", 
        "api": "https://sneakernews.com/wp-json/wp/v2/posts?per_page=10&_embed",
        "category": "sneakers"
    },
    {
        "key": "hypebeast", 
        "name": "Hypebeast Footwear", 
        "type": "rss", 
        "api": "https://hypebeast.com/footwear/feed",
        "category": "sneakers"
    },
    {
        "key": "highsnobiety", 
        "name": "Highsnobiety Sneakers", 
        "type": "rss", 
        "api": "https://www.highsnobiety.com/tag/sneakers/feed/",
        "category": "sneakers"
    },
    {
        "key": "hypebeast_fashion", 
        "name": "Hypebeast Fashion", 
        "type": "rss", 
        "api": "https://hypebeast.com/fashion/feed",
        "category": "fashion"
    },
    {
        "key": "highsnobiety_fashion", 
        "name": "Highsnobiety Fashion", 
        "type": "rss", 
        "api": "https://www.highsnobiety.com/tag/fashion/feed/",
        "category": "fashion"
    }
]