"""
Wikidata Integration Module

Provides easy integration of Wikidata enrichment into existing Wikipedia extraction pipeline.
This module acts as a facade/wrapper to initialize all Wikidata components.

Implements Phase 3, Step 8: Integration into Existing Pipeline.

Usage:
    from wikidata_integration import WikidataIntegration

    # Initialize
    wikidata = WikidataIntegration(enable=True)

    # Enrich Wikipedia data
    enriched_data = wikidata.enrich(wikipedia_data, entity)

    # Get statistics
    stats = wikidata.get_statistics()
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

# Import Wikidata components
from wikidata.config_manager import PropertyConfigManager
from wikidata.client import WikidataClient
from wikidata.cache import EntityReferenceCache
from wikidata.parser import WikidataParser
from wikidata.type_mapper import EntityTypeMapper
from wikidata.enricher import WikidataEnricher

logger = logging.getLogger(__name__)


@dataclass
class WikidataIntegrationConfig:
    """Configuration for Wikidata integration"""
    enable_enrichment: bool = True
    config_dir: str = "config/properties"
    cache_file: str = "pipeline_state/entity_cache.pkl"
    max_retries: int = 3
    timeout: int = 10
    rate_limit: float = 1.0  # requests per second
    type_override_file: Optional[str] = None
    # Phase 4 Step 11: Performance optimization parameters
    cache_ttl: int = 3600  # TTL cache duration in seconds (1 hour)
    cache_maxsize: int = 1000  # Maximum number of entries in TTL cache


class WikidataIntegration:
    """
    Facade for Wikidata enrichment integration.

    Provides a simplified interface to initialize and use all Wikidata components.
    """

    def __init__(
        self,
        config: Optional[WikidataIntegrationConfig] = None,
        base_path: Optional[Path] = None
    ):
        """
        Initialize Wikidata integration.

        Args:
            config: WikidataIntegrationConfig instance
            base_path: Base path for relative paths (defaults to current working directory)
        """
        self.config = config or WikidataIntegrationConfig()
        self.base_path = base_path or Path.cwd()
        self.enabled = self.config.enable_enrichment

        # Initialize components if enabled
        self.enricher = None
        if self.enabled:
            self._initialize_components()
        else:
            logger.info("Wikidata enrichment is disabled")

    def _initialize_components(self):
        """
        Initialize all Wikidata components.
        """
        try:
            logger.info("Initializing Wikidata enrichment components...")

            # 1. Property Configuration Manager
            config_dir = self.base_path / self.config.config_dir
            self.property_config_manager = PropertyConfigManager(
                config_dir=str(config_dir)
            )
            logger.info(f"PropertyConfigManager initialized with config dir: {config_dir}")

            # 2. Wikidata API Client (with Phase 4 Step 11 optimizations)
            self.wikidata_client = WikidataClient(
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
                requests_per_second=self.config.rate_limit,
                cache_ttl=self.config.cache_ttl,
                cache_maxsize=self.config.cache_maxsize
            )
            logger.info(
                f"WikidataClient initialized with TTL cache "
                f"(ttl={self.config.cache_ttl}s, maxsize={self.config.cache_maxsize})"
            )

            # 3. Entity Reference Cache
            cache_file = self.base_path / self.config.cache_file
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.entity_cache = EntityReferenceCache(
                cache_file=str(cache_file)
            )
            logger.info(f"EntityReferenceCache initialized with cache file: {cache_file}")

            # 4. Wikidata Parser (with client for fetching entity references)
            self.parser = WikidataParser(
                entity_cache=self.entity_cache,
                wikidata_client=self.wikidata_client
            )
            logger.info("WikidataParser initialized with client for entity reference resolution")

            # 5. Entity Type Mapper
            override_file = None
            if self.config.type_override_file:
                override_file = str(self.base_path / self.config.type_override_file)
            self.type_mapper = EntityTypeMapper(
                override_file=override_file
            )
            logger.info("EntityTypeMapper initialized")

            # 6. Wikidata Enricher (Orchestrator)
            self.enricher = WikidataEnricher(
                config_manager=self.property_config_manager,
                wikidata_client=self.wikidata_client,
                entity_cache=self.entity_cache,
                parser=self.parser,
                type_mapper=self.type_mapper
            )
            logger.info("WikidataEnricher initialized")

            logger.info("Wikidata enrichment components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Wikidata components: {e}", exc_info=True)
            self.enabled = False
            self.enricher = None

    def enrich(
        self,
        wikipedia_data: Dict,
        entity: Any = None
    ) -> Dict:
        """
        Enrich Wikipedia data with Wikidata structured data.

        Args:
            wikipedia_data: Dictionary containing Wikipedia extraction results
            entity: WikiEntity object with metadata (optional)

        Returns:
            Dictionary with added structured_key_data field and extraction flag

        Example:
            >>> wikidata = WikidataIntegration()
            >>> enriched = wikidata.enrich(wikipedia_data, entity)
            >>> enriched['structured_key_data_extracted']
            True
        """
        if not self.enabled or not self.enricher:
            logger.debug("Wikidata enrichment is disabled, skipping...")
            wikipedia_data['structured_key_data_extracted'] = False
            return wikipedia_data

        try:
            return self.enricher.enrich_entity(wikipedia_data, entity)
        except Exception as e:
            logger.error(f"Error during enrichment: {e}", exc_info=True)
            wikipedia_data['structured_key_data_extracted'] = False
            return wikipedia_data

    def get_statistics(self) -> Dict:
        """
        Get enrichment statistics.

        Returns:
            Dictionary with performance stats
        """
        if not self.enabled or not self.enricher:
            return {
                'enabled': False,
                'message': 'Wikidata enrichment is disabled'
            }

        stats = self.enricher.get_statistics()
        stats['enabled'] = True
        return stats

    def log_statistics(self):
        """
        Log enrichment statistics.
        """
        if self.enabled and self.enricher:
            self.enricher.log_statistics()
        else:
            logger.info("Wikidata enrichment is disabled")

    def reset_statistics(self):
        """
        Reset enrichment statistics.
        """
        if self.enabled and self.enricher:
            self.enricher.reset_statistics()

    def save_cache(self):
        """
        Manually save entity cache to disk.
        """
        if self.enabled and self.entity_cache:
            try:
                self.entity_cache._save_to_disk()
                logger.info("Entity cache saved to disk")
            except Exception as e:
                logger.error(f"Error saving entity cache: {e}")

    def get_cache_statistics(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.entity_cache:
            return {
                'enabled': False,
                'message': 'Wikidata enrichment is disabled'
            }

        return self.entity_cache.get_statistics()


def create_wikidata_integration(
    enable: bool = True,
    config_dir: str = "config/properties",
    cache_file: str = "pipeline_state/entity_cache.pkl",
    base_path: Optional[str] = None
) -> WikidataIntegration:
    """
    Factory function to create WikidataIntegration instance.

    Args:
        enable: Whether to enable Wikidata enrichment
        config_dir: Directory containing property YAML files
        cache_file: Path to entity cache file
        base_path: Base path for relative paths

    Returns:
        WikidataIntegration instance

    Example:
        >>> wikidata = create_wikidata_integration(enable=True)
        >>> enriched_data = wikidata.enrich(wikipedia_data, entity)
    """
    config = WikidataIntegrationConfig(
        enable_enrichment=enable,
        config_dir=config_dir,
        cache_file=cache_file
    )

    base = Path(base_path) if base_path else None

    return WikidataIntegration(config=config, base_path=base)


# Example usage helper
def enrich_wikipedia_data(
    wikipedia_data: Dict,
    entity: Any = None,
    wikidata_integration: Optional[WikidataIntegration] = None
) -> Dict:
    """
    Standalone function to enrich Wikipedia data.

    Args:
        wikipedia_data: Dictionary containing Wikipedia extraction results
        entity: WikiEntity object with metadata (optional)
        wikidata_integration: Existing WikidataIntegration instance (optional)

    Returns:
        Enriched Wikipedia data

    Example:
        >>> enriched = enrich_wikipedia_data(wikipedia_data, entity)
    """
    if wikidata_integration is None:
        wikidata_integration = create_wikidata_integration()

    return wikidata_integration.enrich(wikipedia_data, entity)
