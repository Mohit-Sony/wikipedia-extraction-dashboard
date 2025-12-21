"""
Wikidata Enricher

Orchestrates the complete Wikidata enrichment process.
Coordinates PropertyConfigManager, WikidataClient, EntityReferenceCache, and WikidataParser.

Implements Phase 3, Step 7: Wikidata Enrichment Module.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WikidataEnricher:
    """
    Orchestrator for Wikidata enrichment process.

    Coordinates all Wikidata components to enrich Wikipedia data with
    structured information from Wikidata.
    """

    def __init__(
        self,
        config_manager,
        wikidata_client,
        entity_cache,
        parser,
        type_mapper
    ):
        """
        Initialize Wikidata enricher.

        Args:
            config_manager: PropertyConfigManager instance
            wikidata_client: WikidataClient instance
            entity_cache: EntityReferenceCache instance
            parser: WikidataParser instance
            type_mapper: EntityTypeMapper instance
        """
        self.config_manager = config_manager
        self.wikidata_client = wikidata_client
        self.entity_cache = entity_cache
        self.parser = parser
        self.type_mapper = type_mapper

        # Performance tracking
        self.stats = {
            'total_enriched': 0,
            'successful': 0,
            'failed': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'total_fetch_time': 0.0
        }

        logger.info("WikidataEnricher initialized")

    def enrich_entity(
        self,
        wikipedia_data: Dict,
        entity: Any,
        extract_all_properties: bool = True
    ) -> Dict:
        """
        Enrich Wikipedia data with Wikidata structured data.

        This method fetches entity data from Wikidata API, parses configured
        properties, and adds a structured_key_data field to the wikipedia_data
        dictionary. The process includes caching, error handling, and performance
        tracking.

        Args:
            wikipedia_data: Dictionary containing Wikipedia extraction results
            entity: WikiEntity object with metadata (qid, type, etc.)
            extract_all_properties: If True, extracts ALL properties from Wikidata.
                                   If False, uses type-based YAML configuration.
                                   Default: True (universal extraction)

        Returns:
            Dictionary with added structured_key_data field and extraction flag

        Raises:
            Exception: Logs but doesn't raise - graceful degradation

        Example:
            >>> enricher = WikidataEnricher(...)
            >>> wikipedia_data = {'qid': 'Q1001', 'title': 'Gandhi'}
            >>> result = enricher.enrich_entity(wikipedia_data, entity)
            >>> result['structured_key_data_extracted']
            True
        """
        start_time = time.time()
        self.stats['total_enriched'] += 1

        try:
            # Extract QID from Wikipedia data
            qid = wikipedia_data.get('qid')
            if not qid:
                logger.warning(f"No QID found for entity: {wikipedia_data.get('title', 'Unknown')}")
                wikipedia_data['structured_key_data_extracted'] = False
                self.stats['failed'] += 1
                return wikipedia_data

            logger.info(f"Enriching entity {qid} ({wikipedia_data.get('title', 'Unknown')})")

            # Fetch Wikidata JSON
            wikidata_json = self._fetch_wikidata(qid)
            if not wikidata_json:
                logger.warning(f"Failed to fetch Wikidata for {qid}")
                wikipedia_data['structured_key_data_extracted'] = False
                self.stats['failed'] += 1
                return wikipedia_data

            # Determine entity type
            # Extract P31 (instance of) from Wikidata
            wikidata_instance_qids = self._extract_instance_of(wikidata_json)

            # Get standard type using type mapper
            standard_type = self.type_mapper.get_standard_type(
                wikipedia_type=entity.type if hasattr(entity, 'type') else None,
                wikidata_instance_qids=wikidata_instance_qids,
                qid=qid
            )

            logger.info(f"Determined entity type for {qid}: {standard_type}")

            # Parse Wikidata JSON to structured format
            if extract_all_properties:
                # UNIVERSAL EXTRACTION MODE: Extract ALL properties
                logger.info(f"Using universal extraction mode for {qid}")
                structured_data = self.parser.parse_entity_universal(wikidata_json)
            else:
                # CONFIG-BASED EXTRACTION MODE: Extract only configured properties
                logger.info(f"Using config-based extraction mode for {qid}")
                property_config = self._get_property_config(standard_type)
                if not property_config:
                    logger.warning(f"No property configuration for type: {standard_type}")
                    wikipedia_data['structured_key_data_extracted'] = False
                    self.stats['failed'] += 1
                    return wikipedia_data

                structured_data = self.parser.parse_entity(
                    wikidata_json,
                    property_config
                )

            if not structured_data:
                logger.warning(f"No structured data extracted for {qid}")
                wikipedia_data['structured_key_data_extracted'] = False
                self.stats['failed'] += 1
                return wikipedia_data

            # Add structured data to Wikipedia data
            wikipedia_data['structured_key_data'] = structured_data
            wikipedia_data['structured_key_data_extracted'] = True

            # Update extraction metadata
            fetch_time = time.time() - start_time
            self.stats['total_fetch_time'] += fetch_time
            self.stats['successful'] += 1

            if 'extraction_metadata' not in wikipedia_data:
                wikipedia_data['extraction_metadata'] = {}

            wikipedia_data['extraction_metadata']['wikidata_fetch_time'] = round(fetch_time, 3)
            wikipedia_data['extraction_metadata']['wikidata_properties_extracted'] = len(structured_data)
            wikipedia_data['extraction_metadata']['entity_type_standardized'] = standard_type

            # Add relationship metadata
            relationship_metadata = self._calculate_relationship_metadata(structured_data)
            wikipedia_data['extraction_metadata']['relationship_metadata'] = relationship_metadata

            logger.info(
                f"Successfully enriched {qid} with {len(structured_data)} properties "
                f"in {fetch_time:.2f}s"
            )

            return wikipedia_data

        except Exception as e:
            logger.error(f"Error enriching entity {wikipedia_data.get('qid', 'Unknown')}: {e}", exc_info=True)
            wikipedia_data['structured_key_data_extracted'] = False
            self.stats['failed'] += 1
            return wikipedia_data

    def _fetch_wikidata(self, qid: str) -> Optional[Dict]:
        """
        Fetch Wikidata JSON from cache or API.

        Args:
            qid: Wikidata entity QID

        Returns:
            Wikidata JSON response or None
        """
        try:
            # Check cache first
            cached_data = self.entity_cache.get(qid)
            if cached_data:
                logger.debug(f"Cache hit for {qid}")
                self.stats['cache_hits'] += 1
                # Cached data is simplified, need full data from API
                # Only use cache for entity references, not main entity
                pass

            # Fetch from Wikidata API
            logger.debug(f"Fetching {qid} from Wikidata API")
            wikidata_json = self.wikidata_client.fetch_entity_data(qid)
            self.stats['api_calls'] += 1

            return wikidata_json

        except Exception as e:
            logger.error(f"Error fetching Wikidata for {qid}: {e}")
            return None

    def _extract_instance_of(self, wikidata_json: Dict) -> List[str]:
        """
        Extract P31 (instance of) QIDs from Wikidata JSON.

        Args:
            wikidata_json: Wikidata API response

        Returns:
            List of instance QIDs
        """
        try:
            entities = wikidata_json.get('entities', {})
            if not entities:
                return []

            # Get first entity (should be the one we requested)
            entity_data = list(entities.values())[0]
            claims = entity_data.get('claims', {})
            p31_claims = claims.get('P31', [])

            # Extract QIDs
            qids = []
            for claim in p31_claims:
                try:
                    # Only process 'value' type claims
                    mainsnak = claim.get('mainsnak', {})
                    if mainsnak.get('snaktype') != 'value':
                        continue

                    datavalue = mainsnak.get('datavalue', {})
                    value = datavalue.get('value', {})
                    qid = value.get('id')

                    if qid:
                        qids.append(qid)

                except (KeyError, TypeError, AttributeError):
                    continue

            logger.debug(f"Extracted P31 instance types: {qids}")
            return qids

        except Exception as e:
            logger.error(f"Failed to extract P31 instance types: {e}")
            return []

    def _get_property_config(self, entity_type: str) -> List[Dict]:
        """
        Get property configuration for entity type.

        Args:
            entity_type: Standard entity type (person, location, etc.)

        Returns:
            List of property configurations
        """
        try:
            config = self.config_manager.get_properties_for_type(entity_type)
            logger.debug(f"Loaded {len(config)} properties for type: {entity_type}")
            return config

        except Exception as e:
            logger.error(f"Error loading property config for {entity_type}: {e}")
            return []

    def _calculate_relationship_metadata(self, structured_data: Dict) -> Dict:
        """
        Calculate relationship metadata from structured data.

        Args:
            structured_data: Parsed structured_key_data

        Returns:
            Dictionary with relationship counts
        """
        metadata = {
            'family_connections': 0,
            'political_connections': 0,
            'geographic_connections': 0,
            'total_unique_entities_referenced': 0
        }

        try:
            unique_entities = set()

            # Family properties
            family_props = ['P22', 'P25', 'P26', 'P40']  # father, mother, spouse, children
            for prop in family_props:
                if prop in structured_data:
                    value = structured_data[prop].get('value')
                    if isinstance(value, dict) and 'qid' in value:
                        unique_entities.add(value['qid'])
                        metadata['family_connections'] += 1
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and 'qid' in item:
                                unique_entities.add(item['qid'])
                                metadata['family_connections'] += 1

            # Political properties
            political_props = ['P39', 'P106']  # position_held, occupation
            for prop in political_props:
                if prop in structured_data:
                    value = structured_data[prop].get('value')
                    if isinstance(value, list):
                        metadata['political_connections'] += len(value)

            # Geographic properties
            geo_props = ['P19', 'P20', 'P27', 'P131']  # birth place, death place, country, location
            for prop in geo_props:
                if prop in structured_data:
                    value = structured_data[prop].get('value')
                    if isinstance(value, dict) and 'qid' in value:
                        unique_entities.add(value['qid'])
                        metadata['geographic_connections'] += 1

            metadata['total_unique_entities_referenced'] = len(unique_entities)

        except Exception as e:
            logger.error(f"Error calculating relationship metadata: {e}")

        return metadata

    def get_statistics(self) -> Dict:
        """
        Get enrichment statistics.

        Returns:
            Dictionary with performance stats
        """
        stats = self.stats.copy()

        # Calculate derived metrics
        if stats['total_enriched'] > 0:
            stats['success_rate'] = round(
                stats['successful'] / stats['total_enriched'] * 100, 2
            )
            stats['avg_fetch_time'] = round(
                stats['total_fetch_time'] / stats['total_enriched'], 3
            )
        else:
            stats['success_rate'] = 0.0
            stats['avg_fetch_time'] = 0.0

        if stats['api_calls'] > 0:
            stats['cache_hit_rate'] = round(
                stats['cache_hits'] / (stats['cache_hits'] + stats['api_calls']) * 100, 2
            )
        else:
            stats['cache_hit_rate'] = 0.0

        return stats

    def log_statistics(self):
        """
        Log enrichment statistics.
        """
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("Wikidata Enrichment Statistics")
        logger.info("=" * 60)
        logger.info(f"Total entities processed: {stats['total_enriched']}")
        logger.info(f"Successful enrichments: {stats['successful']}")
        logger.info(f"Failed enrichments: {stats['failed']}")
        logger.info(f"Success rate: {stats['success_rate']}%")
        logger.info(f"API calls made: {stats['api_calls']}")
        logger.info(f"Cache hits: {stats['cache_hits']}")
        logger.info(f"Cache hit rate: {stats['cache_hit_rate']}%")
        logger.info(f"Average fetch time: {stats['avg_fetch_time']}s")
        logger.info(f"Total fetch time: {round(stats['total_fetch_time'], 2)}s")
        logger.info("=" * 60)

    def reset_statistics(self):
        """
        Reset enrichment statistics.
        """
        self.stats = {
            'total_enriched': 0,
            'successful': 0,
            'failed': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'total_fetch_time': 0.0
        }
        logger.info("Enrichment statistics reset")
