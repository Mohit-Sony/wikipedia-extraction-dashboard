"""Unit tests for EntityTypeMapper."""

import pytest
from wikidata.type_mapper import EntityTypeMapper, normalize_wikipedia_type, normalize_wikidata_instance_type


class TestNormalizeWikipediaType:
    """Test suite for normalize_wikipedia_type function."""

    def test_person_types(self):
        """Test person type mappings."""
        assert normalize_wikipedia_type("human") == "person"
        assert normalize_wikipedia_type("person") == "person"
        assert normalize_wikipedia_type("king") == "person"
        assert normalize_wikipedia_type("emperor") == "person"
        assert normalize_wikipedia_type("politician") == "person"
        assert normalize_wikipedia_type("scholar") == "person"

    def test_location_types(self):
        """Test location type mappings."""
        assert normalize_wikipedia_type("city") == "location"
        assert normalize_wikipedia_type("mega city") == "location"
        assert normalize_wikipedia_type("village") == "location"
        assert normalize_wikipedia_type("fort") == "location"
        assert normalize_wikipedia_type("temple") == "location"
        assert normalize_wikipedia_type("river") == "location"

    def test_event_types(self):
        """Test event type mappings."""
        assert normalize_wikipedia_type("event") == "event"
        assert normalize_wikipedia_type("battle") == "event"
        assert normalize_wikipedia_type("war") == "event"
        assert normalize_wikipedia_type("siege") == "event"
        assert normalize_wikipedia_type("revolution") == "event"

    def test_dynasty_types(self):
        """Test dynasty type mappings."""
        assert normalize_wikipedia_type("dynasty") == "dynasty"
        assert normalize_wikipedia_type("royal house") == "dynasty"
        assert normalize_wikipedia_type("royal family") == "dynasty"

    def test_political_entity_types(self):
        """Test political entity type mappings."""
        assert normalize_wikipedia_type("kingdom") == "political_entity"
        assert normalize_wikipedia_type("empire") == "political_entity"
        assert normalize_wikipedia_type("sultanate") == "political_entity"
        assert normalize_wikipedia_type("republic") == "political_entity"

    def test_other_types(self):
        """Test fallback to 'other' category."""
        assert normalize_wikipedia_type("organization") == "other"
        assert normalize_wikipedia_type("concept") == "other"
        assert normalize_wikipedia_type("book") == "other"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert normalize_wikipedia_type("HUMAN") == "person"
        assert normalize_wikipedia_type("City") == "location"
        assert normalize_wikipedia_type("BaTtLe") == "event"

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert normalize_wikipedia_type("  human  ") == "person"
        assert normalize_wikipedia_type("mega city") == "location"

    def test_unknown_type(self):
        """Test unknown type defaults to 'other'."""
        assert normalize_wikipedia_type("unknown_type_xyz") == "other"
        assert normalize_wikipedia_type("") == "other"


class TestNormalizeWikidataInstanceType:
    """Test suite for normalize_wikidata_instance_type function."""

    def test_person_qids(self):
        """Test person QID mappings."""
        assert normalize_wikidata_instance_type(["Q5"]) == "person"  # human
        assert normalize_wikidata_instance_type(["Q116"]) == "person"  # monarch
        assert normalize_wikidata_instance_type(["Q82955"]) == "person"  # politician

    def test_location_qids(self):
        """Test location QID mappings."""
        assert normalize_wikidata_instance_type(["Q515"]) == "location"  # city
        assert normalize_wikidata_instance_type(["Q486972"]) == "location"  # settlement
        assert normalize_wikidata_instance_type(["Q6256"]) == "location"  # country

    def test_event_qids(self):
        """Test event QID mappings."""
        assert normalize_wikidata_instance_type(["Q178561"]) == "event"  # battle
        assert normalize_wikidata_instance_type(["Q198"]) == "event"  # war
        assert normalize_wikidata_instance_type(["Q10931"]) == "event"  # revolution

    def test_dynasty_qids(self):
        """Test dynasty QID mappings."""
        assert normalize_wikidata_instance_type(["Q164950"]) == "dynasty"  # dynasty
        assert normalize_wikidata_instance_type(["Q171541"]) == "dynasty"  # royal house

    def test_political_entity_qids(self):
        """Test political entity QID mappings."""
        assert normalize_wikidata_instance_type(["Q417175"]) == "political_entity"  # kingdom
        assert normalize_wikidata_instance_type(["Q112099"]) == "political_entity"  # empire
        assert normalize_wikidata_instance_type(["Q842658"]) == "political_entity"  # sultanate

    def test_multiple_qids_first_match(self):
        """Test that first matching QID is used."""
        qids = ["Q999999", "Q5", "Q515"]  # unknown, human, city
        result = normalize_wikidata_instance_type(qids)
        assert result == "person"  # Q5 (human) should match first

    def test_unknown_qid(self):
        """Test unknown QID defaults to 'other'."""
        assert normalize_wikidata_instance_type(["Q999999999"]) == "other"

    def test_empty_list(self):
        """Test empty QID list defaults to 'other'."""
        assert normalize_wikidata_instance_type([]) == "other"


class TestEntityTypeMapper:
    """Test suite for EntityTypeMapper class."""

    @pytest.fixture
    def mapper(self):
        """Create EntityTypeMapper instance."""
        return EntityTypeMapper()

    def test_initialization(self, mapper):
        """Test mapper initialization."""
        assert mapper.wikipedia_mapping is not None
        assert mapper.wikidata_mapping is not None
        assert "person" in mapper.valid_types
        assert "location" in mapper.valid_types

    def test_get_standard_type_wikidata_priority(self, mapper):
        """Test that Wikidata P31 takes priority over Wikipedia type."""
        result = mapper.get_standard_type(
            wikipedia_type="city",  # Would map to location
            wikidata_instance_qids=["Q5"]  # human
        )

        # Should use Wikidata (person) not Wikipedia (location)
        assert result == "person"

    def test_get_standard_type_wikipedia_fallback(self, mapper):
        """Test fallback to Wikipedia type when Wikidata is unknown."""
        result = mapper.get_standard_type(
            wikipedia_type="king",
            wikidata_instance_qids=["Q999999"]  # unknown QID
        )

        # Should use Wikipedia type
        assert result == "person"

    def test_get_standard_type_both_none(self, mapper):
        """Test when both sources are None."""
        result = mapper.get_standard_type(
            wikipedia_type=None,
            wikidata_instance_qids=None
        )

        assert result == "other"

    def test_get_standard_type_wikidata_only(self, mapper):
        """Test with only Wikidata data."""
        result = mapper.get_standard_type(
            wikipedia_type=None,
            wikidata_instance_qids=["Q515"]  # city
        )

        assert result == "location"

    def test_get_standard_type_wikipedia_only(self, mapper):
        """Test with only Wikipedia data."""
        result = mapper.get_standard_type(
            wikipedia_type="battle",
            wikidata_instance_qids=None
        )

        assert result == "event"

    def test_validate_type_valid(self, mapper):
        """Test type validation for valid types."""
        assert mapper.validate_type("person") == True
        assert mapper.validate_type("location") == True
        assert mapper.validate_type("event") == True
        assert mapper.validate_type("dynasty") == True
        assert mapper.validate_type("political_entity") == True
        assert mapper.validate_type("other") == True

    def test_validate_type_invalid(self, mapper):
        """Test type validation for invalid types."""
        assert mapper.validate_type("invalid") == False
        assert mapper.validate_type("") == False
        assert mapper.validate_type(None) == False

    def test_get_property_config_path(self, mapper):
        """Test getting property config file paths."""
        assert mapper.get_property_config_file("person") == "person.yaml"
        assert mapper.get_property_config_file("location") == "location.yaml"
        assert mapper.get_property_config_file("event") == "event.yaml"
        assert mapper.get_property_config_file("dynasty") == "dynasty.yaml"
        assert mapper.get_property_config_file("political_entity") == "political_entity.yaml"
        assert mapper.get_property_config_file("other") == "other.yaml"

    def test_manual_override_support(self, mapper):
        """Test manual override functionality if implemented."""
        # Check if override methods exist
        if hasattr(mapper, 'get_standard_type_with_override'):
            # The implementation exists but we need to add the override first
            mapper.overrides["Q83891"] = "dynasty"

            result = mapper.get_standard_type_with_override(
                qid="Q83891",
                wikipedia_type="empire",  # Would be political_entity
                wikidata_instance_qids=["Q112099"]  # empire
            )

            assert result == "dynasty"  # Override should win
        else:
            # Skip test if not implemented
            pytest.skip("Manual override not yet implemented")

    def test_real_world_examples(self, mapper):
        """Test with real-world entity type combinations."""
        # Mahatma Gandhi
        gandhi_type = mapper.get_standard_type(
            wikipedia_type="human",
            wikidata_instance_qids=["Q5"]
        )
        assert gandhi_type == "person"

        # Mumbai
        mumbai_type = mapper.get_standard_type(
            wikipedia_type="mega city",
            wikidata_instance_qids=["Q515", "Q1549591"]
        )
        assert mumbai_type == "location"

        # Battle of Panipat
        battle_type = mapper.get_standard_type(
            wikipedia_type="battle",
            wikidata_instance_qids=["Q178561"]
        )
        assert battle_type == "event"

        # Mughal Empire - could be dynasty or political_entity
        mughal_type = mapper.get_standard_type(
            wikipedia_type="empire",
            wikidata_instance_qids=["Q112099"]
        )
        assert mughal_type in ["dynasty", "political_entity"]
