"""Schemas package for knowledge service API v1."""

from .resource import *

__all__ = [
    "TopicBase", "TopicCreate", "TopicUpdate", "Topic",
    "ResourceBase", "ResourceCreate", "ResourceUpdate", "Resource",
    "BookmarkBase", "BookmarkCreate", "BookmarkUpdate", "Bookmark",
    "CitationBase", "CitationCreate", "Citation"
]