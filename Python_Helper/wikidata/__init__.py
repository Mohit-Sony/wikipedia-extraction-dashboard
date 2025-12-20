"""
Wikidata Integration Module

This module provides functionality to enrich Wikipedia extraction data
with structured data from Wikidata's EntityData API.

Components:
    - PropertyConfigManager: Manages YAML property configurations
    - WikidataClient: API client for fetching Wikidata entity data
    - EntityReferenceCache: Caching layer for entity references
    - WikidataParser: Parses Wikidata JSON to structured format
    - WikidataEnricher: Orchestrates the enrichment process
"""

__version__ = "1.0.0"
__author__ = "Senior Python Developer Team"

from .config_manager import PropertyConfigManager
from .client import WikidataClient
from .cache import EntityReferenceCache
from .parser import WikidataParser
from .enricher import WikidataEnricher

__all__ = [
    "PropertyConfigManager",
    "WikidataClient",
    "EntityReferenceCache",
    "WikidataParser",
    "WikidataEnricher",
]
