"""
Entity Type Mapper

Maps Wikipedia entity types and Wikidata P31 (instance of) to standardized types.
Implements Phase 2, Step 6: Entity Type Mapping System.

Standard Types:
- person
- location
- event
- dynasty
- political_entity
- other
"""

import logging
from typing import List, Optional, Dict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# Wikipedia type → Our standard type mapping
WIKIPEDIA_TYPE_TO_STANDARD_TYPE = {
    # Person types
    "human": "person",
    "person": "person",
    "people": "person",
    "individual": "person",
    "ruler": "person",
    "king": "person",
    "queen": "person",
    "emperor": "person",
    "empress": "person",
    "sultan": "person",
    "maharaja": "person",
    "maharani": "person",
    "nawab": "person",
    "prince": "person",
    "princess": "person",
    "politician": "person",
    "leader": "person",
    "warrior": "person",
    "general": "person",
    "commander": "person",
    "scholar": "person",
    "poet": "person",
    "author": "person",
    "artist": "person",
    "philosopher": "person",
    "scientist": "person",
    "religious leader": "person",
    "saint": "person",

    # Location types
    "place": "location",
    "location": "location",
    "city": "location",
    "town": "location",
    "village": "location",
    "settlement": "location",
    "mega city": "location",
    "megacity": "location",
    "metropolis": "location",
    "municipality": "location",
    "district": "location",
    "region": "location",
    "province": "location",
    "state": "location",
    "territory": "location",
    "country": "location",
    "nation": "location",
    "fort": "location",
    "fortress": "location",
    "palace": "location",
    "temple": "location",
    "shrine": "location",
    "monument": "location",
    "river": "location",
    "mountain": "location",
    "geographic location": "location",
    "capital": "location",
    "island": "location",
    "lake": "location",

    # Event types
    "event": "event",
    "occurrence": "event",
    "battle": "event",
    "war": "event",
    "conflict": "event",
    "siege": "event",
    "campaign": "event",
    "revolution": "event",
    "rebellion": "event",
    "uprising": "event",
    "movement": "event",
    "independence movement": "event",
    "protest": "event",
    "massacre": "event",
    "treaty": "event",
    "agreement": "event",
    "conference": "event",
    "festival": "event",
    "celebration": "event",
    "ceremony": "event",

    # Dynasty types
    "dynasty": "dynasty",
    "royal house": "dynasty",
    "royal family": "dynasty",
    "ruling family": "dynasty",
    "lineage": "dynasty",
    "clan": "dynasty",

    # Political entity types
    "kingdom": "political_entity",
    "empire": "political_entity",
    "sultanate": "political_entity",
    "caliphate": "political_entity",
    "princely state": "political_entity",
    "republic": "political_entity",
    "confederation": "political_entity",
    "union": "political_entity",
    "dominion": "political_entity",
    "state (polity)": "political_entity",
    "historical country": "political_entity",
    "historical state": "political_entity",
    "administrative division": "political_entity",
    "sovereign state": "political_entity",
    "former country": "political_entity",

    # Other types
    "organization": "other",
    "institution": "other",
    "company": "other",
    "business": "other",
    "concept": "other",
    "ideology": "other",
    "religion": "other",
    "language": "other",
    "book": "other",
    "document": "other",
    "artifact": "other",
    "text": "other",
    "work": "other",
}


# Wikidata P31 (instance of) QID → Our standard type
WIKIDATA_INSTANCE_TO_STANDARD_TYPE = {
    # Person types
    "Q5": "person",  # human
    "Q45371": "person",  # monarch
    "Q116": "person",  # monarch (duplicate)
    "Q82955": "person",  # politician
    "Q1097498": "person",  # military leader
    "Q189290": "person",  # military officer
    "Q36180": "person",  # writer
    "Q483501": "person",  # artist
    "Q1930187": "person",  # journalist
    "Q169470": "person",  # physicist
    "Q201788": "person",  # historian
    "Q15995642": "person",  # religious leader

    # Location types
    "Q486972": "location",  # human settlement
    "Q515": "location",  # city
    "Q532": "location",  # village
    "Q3957": "location",  # town
    "Q1549591": "location",  # big city
    "Q208511": "location",  # megacity
    "Q448801": "location",  # metropolis
    "Q1266818": "location",  # municipality
    "Q15253706": "location",  # district
    "Q82794": "location",  # geographic region
    "Q7275": "location",  # state
    "Q6256": "location",  # country
    "Q23442": "location",  # island
    "Q23397": "location",  # lake
    "Q4022": "location",  # river
    "Q8502": "location",  # mountain
    "Q1785071": "location",  # fort
    "Q16560": "location",  # palace
    "Q44539": "location",  # temple
    "Q5119": "location",  # capital
    "Q2221906": "location",  # geographic location

    # Event types
    "Q1190554": "event",  # occurrence
    "Q178561": "event",  # battle
    "Q198": "event",  # war
    "Q180684": "event",  # conflict
    "Q188055": "event",  # siege
    "Q2001676": "event",  # military campaign
    "Q10931": "event",  # revolution
    "Q124734": "event",  # rebellion
    "Q1150958": "event",  # social movement
    "Q3736439": "event",  # treaty
    "Q1656682": "event",  # event (generic)
    "Q1190554": "event",  # occurrence
    "Q81672": "event",  # massacre

    # Dynasty types
    "Q164950": "dynasty",  # dynasty
    "Q171541": "dynasty",  # royal house
    "Q8436": "dynasty",  # family (when used for royal families)

    # Political entity types
    "Q417175": "political_entity",  # kingdom
    "Q3024240": "political_entity",  # historical country
    "Q1250464": "political_entity",  # historical state
    "Q112099": "political_entity",  # empire
    "Q842658": "political_entity",  # sultanate
    "Q12560": "political_entity",  # caliphate
    "Q185006": "political_entity",  # princely state
    "Q7270": "political_entity",  # republic
    "Q160114": "political_entity",  # confederation
    "Q4439689": "political_entity",  # sovereign state
    "Q3024240": "political_entity",  # former country
    "Q1048835": "political_entity",  # political territorial entity
}


def normalize_wikipedia_type(wikipedia_type: str) -> str:
    """
    Normalize Wikipedia type to one of our standard types:
    person, location, event, dynasty, political_entity, other

    Args:
        wikipedia_type: Type from Wikipedia extraction (e.g., "human", "mega city")

    Returns:
        Normalized type (person/location/event/dynasty/political_entity/other)

    Examples:
        >>> normalize_wikipedia_type("human")
        'person'
        >>> normalize_wikipedia_type("mega city")
        'location'
        >>> normalize_wikipedia_type("sultanate")
        'political_entity'
        >>> normalize_wikipedia_type("unknown")
        'other'
    """
    if not wikipedia_type:
        return "other"

    # Convert to lowercase and strip whitespace
    normalized_input = wikipedia_type.lower().strip()

    # Direct lookup in mapping
    if normalized_input in WIKIPEDIA_TYPE_TO_STANDARD_TYPE:
        return WIKIPEDIA_TYPE_TO_STANDARD_TYPE[normalized_input]

    # Fuzzy matching for partial matches
    for wiki_type, standard_type in WIKIPEDIA_TYPE_TO_STANDARD_TYPE.items():
        if wiki_type in normalized_input or normalized_input in wiki_type:
            logger.info(f"Fuzzy matched '{wikipedia_type}' to '{standard_type}' via '{wiki_type}'")
            return standard_type

    # Default fallback
    logger.warning(f"Unknown Wikipedia type '{wikipedia_type}', defaulting to 'other'")
    return "other"


def normalize_wikidata_instance_type(instance_qids: List[str]) -> str:
    """
    Normalize Wikidata P31 (instance of) to our standard type.

    Args:
        instance_qids: List of QIDs from P31 property

    Returns:
        Normalized type (person/location/event/dynasty/political_entity/other)

    Examples:
        >>> normalize_wikidata_instance_type(["Q5"])
        'person'
        >>> normalize_wikidata_instance_type(["Q515", "Q1549591"])
        'location'
        >>> normalize_wikidata_instance_type(["Q178561"])
        'event'
    """
    if not instance_qids:
        return "other"

    # Check each instance QID
    for qid in instance_qids:
        if qid in WIKIDATA_INSTANCE_TO_STANDARD_TYPE:
            return WIKIDATA_INSTANCE_TO_STANDARD_TYPE[qid]

    # No match found
    logger.warning(f"Unknown Wikidata instance types {instance_qids}, defaulting to 'other'")
    return "other"


class EntityTypeMapper:
    """
    Centralized entity type mapping and normalization.
    Handles both Wikipedia types and Wikidata P31 instance types.
    """

    def __init__(self, override_file: Optional[str] = None):
        """
        Initialize entity type mapper.

        Args:
            override_file: Optional path to type override JSON file
        """
        self.wikipedia_mapping = WIKIPEDIA_TYPE_TO_STANDARD_TYPE
        self.wikidata_mapping = WIKIDATA_INSTANCE_TO_STANDARD_TYPE
        self.valid_types = {
            "person", "location", "event", "dynasty", "political_entity", "other"
        }

        # Load manual overrides if provided
        self.overrides = {}
        if override_file:
            self._load_overrides(override_file)

        logger.info(f"EntityTypeMapper initialized with {len(self.overrides)} manual overrides")

    def _load_overrides(self, override_file: str):
        """
        Load manual type overrides from JSON file.

        Format:
        {
            "Q1001": "person",
            "Q83891": "dynasty"
        }
        """
        try:
            override_path = Path(override_file)
            if override_path.exists():
                with open(override_path, 'r') as f:
                    self.overrides = json.load(f)
                logger.info(f"Loaded {len(self.overrides)} type overrides from {override_file}")
            else:
                logger.warning(f"Override file not found: {override_file}")
        except Exception as e:
            logger.error(f"Error loading type overrides: {e}")

    def get_standard_type(
        self,
        wikipedia_type: Optional[str] = None,
        wikidata_instance_qids: Optional[List[str]] = None,
        qid: Optional[str] = None
    ) -> str:
        """
        Determine standard entity type from available sources.

        Priority:
        1. Manual override (if QID provided and override exists)
        2. Wikidata P31 (instance of) - most authoritative
        3. Wikipedia type
        4. Default to 'other'

        Args:
            wikipedia_type: Type from Wikipedia extraction
            wikidata_instance_qids: List of P31 QIDs from Wikidata
            qid: Entity QID for override lookup

        Returns:
            Standard type: person/location/event/dynasty/political_entity/other

        Examples:
            >>> mapper = EntityTypeMapper()
            >>> mapper.get_standard_type(wikipedia_type="human")
            'person'
            >>> mapper.get_standard_type(wikidata_instance_qids=["Q5"])
            'person'
            >>> mapper.get_standard_type(wikipedia_type="city", wikidata_instance_qids=["Q515"])
            'location'
        """
        # Priority 1: Manual override
        if qid and qid in self.overrides:
            override_type = self.overrides[qid]
            logger.info(f"Using manual override for {qid}: {override_type}")
            return override_type

        # Priority 2: Wikidata P31 (instance of) - most authoritative
        if wikidata_instance_qids:
            wikidata_type = normalize_wikidata_instance_type(wikidata_instance_qids)
            if wikidata_type != "other":
                return wikidata_type

        # Priority 3: Wikipedia type
        if wikipedia_type:
            wiki_type = normalize_wikipedia_type(wikipedia_type)
            if wiki_type != "other":
                return wiki_type

        # Fallback: other
        return "other"

    def validate_type(self, entity_type: str) -> bool:
        """
        Check if type is one of our valid standard types.

        Args:
            entity_type: Type to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> mapper = EntityTypeMapper()
            >>> mapper.validate_type("person")
            True
            >>> mapper.validate_type("invalid")
            False
        """
        return entity_type in self.valid_types

    def get_property_config_file(self, entity_type: str) -> str:
        """
        Get property configuration file path for entity type.

        Args:
            entity_type: Standard entity type

        Returns:
            Path to YAML config file (relative to config/properties/)

        Example:
            >>> mapper = EntityTypeMapper()
            >>> mapper.get_property_config_file("person")
            'person.yaml'
        """
        type_to_file = {
            "person": "person.yaml",
            "location": "location.yaml",
            "event": "event.yaml",
            "dynasty": "dynasty.yaml",
            "political_entity": "political_entity.yaml",
            "other": "other.yaml"
        }

        return type_to_file.get(entity_type, "other.yaml")

    def add_override(self, qid: str, entity_type: str):
        """
        Add manual type override for specific entity.

        Args:
            qid: Entity QID
            entity_type: Standard type to assign

        Raises:
            ValueError: If entity_type is not valid
        """
        if not self.validate_type(entity_type):
            raise ValueError(f"Invalid entity type: {entity_type}")

        self.overrides[qid] = entity_type
        logger.info(f"Added override: {qid} -> {entity_type}")

    def save_overrides(self, override_file: str):
        """
        Save manual overrides to JSON file.

        Args:
            override_file: Path to save overrides
        """
        try:
            with open(override_file, 'w') as f:
                json.dump(self.overrides, f, indent=2)
            logger.info(f"Saved {len(self.overrides)} overrides to {override_file}")
        except Exception as e:
            logger.error(f"Error saving overrides: {e}")

    def get_statistics(self) -> Dict:
        """
        Get mapping statistics.

        Returns:
            Dictionary with mapping counts
        """
        return {
            'wikipedia_mappings': len(self.wikipedia_mapping),
            'wikidata_mappings': len(self.wikidata_mapping),
            'manual_overrides': len(self.overrides),
            'valid_types': list(self.valid_types)
        }
