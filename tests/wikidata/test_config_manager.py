"""Unit tests for PropertyConfigManager."""

import pytest
from pathlib import Path
from wikidata.config_manager import PropertyConfigManager


class TestPropertyConfigManager:
    """Test suite for PropertyConfigManager."""

    def test_load_person_config(self):
        """Test loading person configuration."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('person')

        assert config is not None
        assert isinstance(config, list)
        assert len(config) > 0

        # Check for expected properties
        property_ids = [p['property_id'] for p in config]
        assert 'P569' in property_ids  # date of birth
        assert 'P570' in property_ids  # date of death
        assert 'P22' in property_ids   # father
        assert 'P25' in property_ids   # mother

    def test_load_location_config(self):
        """Test loading location configuration."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('location')

        assert config is not None
        assert isinstance(config, list)

        property_ids = [p['property_id'] for p in config]
        assert 'P625' in property_ids  # coordinate location
        assert 'P1082' in property_ids # population

    def test_load_event_config(self):
        """Test loading event configuration."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('event')

        assert config is not None
        property_ids = [p['property_id'] for p in config]
        assert 'P580' in property_ids  # start time
        assert 'P582' in property_ids  # end time

    def test_load_dynasty_config(self):
        """Test loading dynasty configuration."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('dynasty')

        assert config is not None
        property_ids = [p['property_id'] for p in config]
        assert 'P571' in property_ids  # inception
        assert 'P576' in property_ids  # dissolved/abolished

    def test_load_political_entity_config(self):
        """Test loading political_entity configuration."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('political_entity')

        assert config is not None
        property_ids = [p['property_id'] for p in config]
        assert 'P35' in property_ids   # head of state
        assert 'P36' in property_ids   # capital

    def test_load_other_config(self):
        """Test loading 'other' configuration."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('other')

        assert config is not None
        # Other should have minimal generic properties
        assert isinstance(config, list)

    def test_invalid_entity_type(self):
        """Test handling of invalid entity type."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('invalid_type')

        # Should return empty list or raise error
        assert config is not None
        assert isinstance(config, list)

    def test_property_structure(self):
        """Test that property configurations have required fields."""
        manager = PropertyConfigManager()
        config = manager.get_properties_for_type('person')

        for prop in config:
            assert 'property_id' in prop
            assert 'label' in prop
            assert 'value_type' in prop
            assert prop['property_id'].startswith('P')

    def test_cache_hit(self):
        """Test that configurations are cached."""
        manager = PropertyConfigManager()

        # First call loads from file
        config1 = manager.get_properties_for_type('person')

        # Second call should use cache (same object)
        config2 = manager.get_properties_for_type('person')

        assert config1 == config2

    def test_all_entity_types_loadable(self):
        """Test that all standard entity types can be loaded."""
        manager = PropertyConfigManager()
        entity_types = ['person', 'location', 'event', 'dynasty', 'political_entity', 'other']

        for entity_type in entity_types:
            config = manager.get_properties_for_type(entity_type)
            assert config is not None, f"Failed to load config for {entity_type}"
            assert isinstance(config, list), f"Config for {entity_type} is not a list"
