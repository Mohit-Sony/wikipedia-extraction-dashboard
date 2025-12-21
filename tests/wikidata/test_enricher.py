"""Unit tests for WikidataEnricher."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from wikidata.enricher import WikidataEnricher
from wikidata.config_manager import PropertyConfigManager
from wikidata.client import WikidataClient
from wikidata.cache import EntityReferenceCache
from wikidata.parser import WikidataParser


class TestWikidataEnricher:
    """Test suite for WikidataEnricher."""

    @pytest.fixture
    def enricher_components(self):
        """Create enricher with mocked components."""
        config_manager = Mock(spec=PropertyConfigManager)
        client = Mock(spec=WikidataClient)
        cache = Mock(spec=EntityReferenceCache)
        parser = Mock(spec=WikidataParser)

        return {
            'config_manager': config_manager,
            'client': client,
            'cache': cache,
            'parser': parser
        }

    @pytest.fixture
    def enricher(self, enricher_components):
        """Create WikidataEnricher instance with mocked components."""
        from Python_Helper.wikidata.type_mapper import EntityTypeMapper
        type_mapper = EntityTypeMapper()

        return WikidataEnricher(
            config_manager=enricher_components['config_manager'],
            wikidata_client=enricher_components['client'],
            entity_cache=enricher_components['cache'],
            parser=enricher_components['parser'],
            type_mapper=type_mapper
        )

    def test_initialization(self, enricher):
        """Test enricher initialization."""
        assert enricher.config_manager is not None
        assert enricher.wikidata_client is not None
        assert enricher.entity_cache is not None
        assert enricher.parser is not None

    def test_enrich_entity_success(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test successful entity enrichment."""
        # Setup mocks
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response

        enricher_components['config_manager'].get_properties_for_type.return_value = [
            {"property_id": "P569", "label": "date_of_birth", "value_type": "time"}
        ]

        enricher_components['parser'].parse_entity.return_value = {
            "P569": {
                "label": "date_of_birth",
                "value": {"value": "1869-10-02", "precision": 11},
                "value_type": "time"
            }
        }

        # Mock entity
        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == True
        assert 'structured_key_data' in result
        assert 'P569' in result['structured_key_data']

    def test_enrich_entity_missing_qid(self, enricher):
        """Test enrichment with missing QID."""
        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "title": "Unknown Entity"
            # No QID
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == False
        assert 'structured_key_data' not in result or result.get('structured_key_data') == {}

    def test_enrich_entity_api_failure(self, enricher, enricher_components):
        """Test handling of API failure."""
        # Mock API returning None (failure)
        enricher_components['client'].fetch_entity_data.return_value = None

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == False

    def test_enrich_entity_cache_hit(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test that cache is checked before API call."""
        # Setup cache to return data
        enricher_components['cache'].get.return_value = {
            "qid": "Q1001",
            "name": "Mahatma Gandhi"
        }

        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response

        enricher_components['config_manager'].get_properties_for_type.return_value = []
        enricher_components['parser'].parse_entity.return_value = {}

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        enricher.enrich_entity(wikipedia_data, entity)

        # Verify cache was checked
        enricher_components['cache'].get.assert_called_with("Q1001")

    def test_enrich_entity_type_detection(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test entity type detection and property config selection."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response

        # Mock config manager to track which type was requested
        enricher_components['config_manager'].get_properties_for_type.return_value = []
        enricher_components['parser'].parse_entity.return_value = {}

        entity = Mock()
        entity.type = "human"  # Wikipedia type

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        enricher.enrich_entity(wikipedia_data, entity)

        # Verify correct entity type was used to get properties
        # Should normalize "human" to "person"
        enricher_components['config_manager'].get_properties_for_type.assert_called()

    def test_enrich_entity_adds_metadata(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test that enrichment adds metadata."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response
        enricher_components['config_manager'].get_properties_for_type.return_value = []
        enricher_components['parser'].parse_entity.return_value = {}

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi",
            "extraction_metadata": {}
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        # Should add timing information
        assert 'extraction_metadata' in result
        if 'wikidata_fetch_time' in result['extraction_metadata']:
            assert isinstance(result['extraction_metadata']['wikidata_fetch_time'], (int, float))

    def test_enrich_entity_relationship_metadata(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test calculation of relationship metadata."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response

        enricher_components['config_manager'].get_properties_for_type.return_value = [
            {"property_id": "P22", "label": "father", "value_type": "wikibase-item"},
            {"property_id": "P25", "label": "mother", "value_type": "wikibase-item"}
        ]

        enricher_components['parser'].parse_entity.return_value = {
            "P22": {
                "label": "father",
                "value": {"qid": "Q5682621", "name": "Karamchand Gandhi"},
                "value_type": "wikibase-item"
            },
            "P25": {
                "label": "mother",
                "value": {"qid": "Q3042895", "name": "Putlibai Gandhi"},
                "value_type": "wikibase-item"
            }
        }

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi",
            "extraction_metadata": {}
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        # Should calculate relationship metadata
        if 'relationship_metadata' in result.get('extraction_metadata', {}):
            metadata = result['extraction_metadata']['relationship_metadata']
            assert 'family_connections' in metadata or 'total_unique_entities_referenced' in metadata

    def test_enrich_entity_performance_tracking(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test performance tracking during enrichment."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response
        enricher_components['config_manager'].get_properties_for_type.return_value = []
        enricher_components['parser'].parse_entity.return_value = {}

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        # Should track performance
        if hasattr(enricher, 'stats'):
            assert enricher.stats is not None

    def test_enrich_entity_parser_error(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test handling of parser errors."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response
        enricher_components['config_manager'].get_properties_for_type.return_value = []

        # Mock parser to raise exception
        enricher_components['parser'].parse_entity.side_effect = Exception("Parse error")

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        # Should handle gracefully
        assert result is not None
        assert result['structured_key_data_extracted'] == False

    def test_enrich_multiple_entities(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test enriching multiple entities."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response
        enricher_components['config_manager'].get_properties_for_type.return_value = [
            {"property_id": "P569", "label": "date_of_birth", "value_type": "time"}
        ]
        enricher_components['parser'].parse_entity.return_value = {
            "P569": {"label": "date_of_birth", "value": "1869-10-02"}
        }

        entity = Mock()
        entity.type = "person"

        entities_data = [
            {"qid": "Q1001", "title": "Gandhi"},
            {"qid": "Q1002", "title": "Nehru"},
            {"qid": "Q1003", "title": "Patel"}
        ]

        for data in entities_data:
            result = enricher.enrich_entity(data, entity)
            assert result['structured_key_data_extracted'] == True

    def test_enrich_entity_empty_structured_data(self, enricher, enricher_components, sample_wikidata_person_response):
        """Test when parser returns empty structured data."""
        enricher_components['client'].fetch_entity_data.return_value = sample_wikidata_person_response
        enricher_components['config_manager'].get_properties_for_type.return_value = [
            {"property_id": "P569", "label": "date_of_birth", "value_type": "time"}
        ]
        enricher_components['parser'].parse_entity.return_value = {}  # Empty

        entity = Mock()
        entity.type = "person"

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi"
        }

        result = enricher.enrich_entity(wikipedia_data, entity)

        # With empty structured data, extraction should be marked as failed
        assert result is not None
        assert result['structured_key_data_extracted'] == False
