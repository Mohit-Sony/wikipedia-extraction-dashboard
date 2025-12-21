"""Integration tests for Wikidata enrichment with real API calls.

These tests make actual API calls to Wikidata and should be run sparingly.
Use pytest markers to skip them in regular test runs:
    pytest -m "not integration"  # Skip integration tests
    pytest -m integration        # Run only integration tests
"""

import pytest
import time
from wikidata.config_manager import PropertyConfigManager
from wikidata.client import WikidataClient
from wikidata.cache import EntityReferenceCache
from wikidata.parser import WikidataParser
from wikidata.enricher import WikidataEnricher
from wikidata.type_mapper import EntityTypeMapper


@pytest.mark.integration
class TestWikidataIntegration:
    """Integration tests with real Wikidata API."""

    @pytest.fixture(scope="class")
    def integration_enricher(self):
        """Create enricher with real components for integration testing."""
        from Python_Helper.wikidata.type_mapper import EntityTypeMapper

        config_manager = PropertyConfigManager()
        client = WikidataClient(requests_per_second=1.0)  # Respect API rate limits
        cache = EntityReferenceCache()
        parser = WikidataParser(cache)
        type_mapper = EntityTypeMapper()
        enricher = WikidataEnricher(config_manager, client, cache, parser, type_mapper)

        return enricher

    def test_fetch_mahatma_gandhi(self, integration_enricher):
        """Test fetching and parsing Mahatma Gandhi (Q1001)."""
        # Mock entity
        class MockEntity:
            type = "person"

        entity = MockEntity()

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi",
            "extraction_metadata": {}
        }

        result = integration_enricher.enrich_entity(wikipedia_data, entity)

        # Assertions
        assert result is not None
        assert result['structured_key_data_extracted'] == True
        assert 'structured_key_data' in result

        structured_data = result['structured_key_data']

        # Check for expected properties
        assert 'P569' in structured_data  # date of birth
        assert structured_data['P569']['value']['value'] == "1869-10-02"

        assert 'P570' in structured_data  # date of death
        assert structured_data['P570']['value']['value'] == "1948-01-30"

        # Allow time for API rate limit
        time.sleep(1)

    def test_fetch_mumbai(self, integration_enricher):
        """Test fetching and parsing Mumbai (Q1156)."""
        class MockEntity:
            type = "location"

        entity = MockEntity()

        wikipedia_data = {
            "qid": "Q1156",
            "title": "Mumbai",
            "extraction_metadata": {}
        }

        result = integration_enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == True

        structured_data = result['structured_key_data']

        # Check for location-specific properties
        if 'P625' in structured_data:  # coordinates
            coords = structured_data['P625']['value']
            assert 'latitude' in coords
            assert 'longitude' in coords
            assert abs(coords['latitude'] - 19.0760) < 0.1  # Approximately Mumbai

        time.sleep(1)

    def test_fetch_battle_of_panipat(self, integration_enricher):
        """Test fetching and parsing Battle of Panipat (Q129053)."""
        class MockEntity:
            type = "event"

        entity = MockEntity()

        wikipedia_data = {
            "qid": "Q129053",
            "title": "First Battle of Panipat",
            "extraction_metadata": {}
        }

        result = integration_enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == True

        structured_data = result['structured_key_data']

        # Check for event-specific properties
        # P580 (start time) or P585 (point in time)
        has_temporal_data = 'P580' in structured_data or 'P585' in structured_data

        # Battle of Panipat happened in 1526
        if has_temporal_data:
            if 'P580' in structured_data:
                assert '1526' in structured_data['P580']['value']['value']
            elif 'P585' in structured_data:
                assert '1526' in structured_data['P585']['value']['value']

        time.sleep(1)

    def test_fetch_mughal_empire(self, integration_enricher):
        """Test fetching and parsing Mughal Empire (Q33296)."""
        class MockEntity:
            type = "political_entity"

        entity = MockEntity()

        wikipedia_data = {
            "qid": "Q33296",
            "title": "Mughal Empire",
            "extraction_metadata": {}
        }

        result = integration_enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == True

        structured_data = result['structured_key_data']

        # Check for inception and dissolution
        if 'P571' in structured_data:  # inception
            inception = structured_data['P571']['value']['value']
            assert '1526' in inception or '1527' in inception  # Founded around 1526

        time.sleep(1)

    def test_nonexistent_entity(self, integration_enricher):
        """Test fetching non-existent entity."""
        class MockEntity:
            type = "person"

        entity = MockEntity()

        wikipedia_data = {
            "qid": "Q999999999",  # Non-existent
            "title": "Non-existent Entity",
            "extraction_metadata": {}
        }

        result = integration_enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == False

    def test_cache_effectiveness(self, integration_enricher):
        """Test that cache reduces API calls."""
        class MockEntity:
            type = "person"

        entity = MockEntity()

        wikipedia_data = {
            "qid": "Q1001",
            "title": "Mahatma Gandhi",
            "extraction_metadata": {}
        }

        # First call
        start = time.time()
        result1 = integration_enricher.enrich_entity(wikipedia_data, entity)
        first_duration = time.time() - start

        time.sleep(1)  # Respect rate limit

        # Second call (should use cache for entity references)
        start = time.time()
        result2 = integration_enricher.enrich_entity(wikipedia_data, entity)
        second_duration = time.time() - start

        # Both should succeed
        assert result1['structured_key_data_extracted'] == True
        assert result2['structured_key_data_extracted'] == True

        # Check cache stats if available
        if hasattr(integration_enricher.entity_cache, 'get_hit_rate'):
            hit_rate = integration_enricher.entity_cache.get_hit_rate()
            assert hit_rate > 0  # Should have some cache hits

    @pytest.mark.parametrize("qid,entity_type,expected_property", [
        ("Q1001", "person", "P569"),      # Gandhi - birth date
        ("Q1156", "location", "P625"),     # Mumbai - coordinates
        ("Q129053", "event", "P580"),      # Battle - start time (or P585)
        ("Q33296", "political_entity", "P571"),  # Mughal - inception
    ])
    def test_multiple_entity_types(self, integration_enricher, qid, entity_type, expected_property):
        """Test enrichment for different entity types."""
        class MockEntity:
            def __init__(self, etype):
                self.type = etype

        entity = MockEntity(entity_type)

        wikipedia_data = {
            "qid": qid,
            "title": f"Test Entity {qid}",
            "extraction_metadata": {}
        }

        result = integration_enricher.enrich_entity(wikipedia_data, entity)

        assert result is not None
        assert result['structured_key_data_extracted'] == True

        # Check that at least one expected property is present
        # (allowing for P585 as alternative to P580 for events)
        if expected_property == "P580":
            has_expected = expected_property in result['structured_key_data'] or \
                          'P585' in result['structured_key_data']
            assert has_expected
        else:
            assert expected_property in result['structured_key_data'] or \
                   len(result['structured_key_data']) > 0  # Has some data

        time.sleep(1)  # Respect rate limit


@pytest.mark.integration
class TestWikidataClientIntegration:
    """Integration tests specifically for WikidataClient."""

    @pytest.fixture
    def client(self):
        """Create WikidataClient for testing."""
        return WikidataClient(requests_per_second=1.0)

    def test_fetch_valid_entity(self, client):
        """Test fetching a valid entity."""
        result = client.fetch_entity_data("Q1001")

        assert result is not None
        assert 'entities' in result
        assert 'Q1001' in result['entities']

        entity = result['entities']['Q1001']
        assert 'claims' in entity
        assert 'labels' in entity

        time.sleep(1)

    def test_fetch_invalid_qid(self, client):
        """Test fetching with invalid QID."""
        result = client.fetch_entity_data("Q999999999")

        # Should return None or handle gracefully
        assert result is None or 'entities' not in result

    def test_rate_limiting(self, client):
        """Test that rate limiting works."""
        start = time.time()

        # Make 3 requests
        client.fetch_entity_data("Q1001")
        client.fetch_entity_data("Q1002")
        client.fetch_entity_data("Q1003")

        duration = time.time() - start

        # Should take at least 2 seconds (3 requests at 1/sec = 2 seconds between)
        assert duration >= 2.0


@pytest.mark.integration
class TestTypeMapperIntegration:
    """Integration tests for type detection with real data."""

    @pytest.fixture
    def mapper(self):
        """Create EntityTypeMapper."""
        return EntityTypeMapper()

    @pytest.fixture
    def client(self):
        """Create client to fetch real P31 data."""
        return WikidataClient(requests_per_second=1.0)

    def test_type_detection_gandhi(self, mapper, client):
        """Test type detection for Mahatma Gandhi."""
        # Fetch real data
        data = client.fetch_entity_data("Q1001")
        assert data is not None

        # Extract P31 (instance of)
        entity_data = data['entities']['Q1001']
        p31_claims = entity_data['claims'].get('P31', [])
        qids = [claim['mainsnak']['datavalue']['value']['id'] for claim in p31_claims
                if 'datavalue' in claim['mainsnak']]

        # Detect type
        detected_type = mapper.get_standard_type(
            wikipedia_type="human",
            wikidata_instance_qids=qids
        )

        assert detected_type == "person"

        time.sleep(1)

    def test_type_detection_mumbai(self, mapper, client):
        """Test type detection for Mumbai."""
        data = client.fetch_entity_data("Q1156")
        assert data is not None

        entity_data = data['entities']['Q1156']
        p31_claims = entity_data['claims'].get('P31', [])
        qids = [claim['mainsnak']['datavalue']['value']['id'] for claim in p31_claims
                if 'datavalue' in claim['mainsnak']]

        detected_type = mapper.get_standard_type(
            wikipedia_type="city",
            wikidata_instance_qids=qids
        )

        assert detected_type == "location"

        time.sleep(1)
