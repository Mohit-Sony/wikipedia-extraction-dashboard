# Wikidata Integration Implementation Plan

**Project:** Wikipedia Extraction Pipeline Enhancement
**Version:** 2.0
**Date:** 2025-12-20
**Author:** Senior Python Developer Team
**Status:** Phase 1 Complete - In Progress

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context & Background](#context--background)
3. [Implementation Plan](#implementation-plan)
4. [Technical Specifications](#technical-specifications)
5. [Data Structure Design](#data-structure-design)
6. [Integration Architecture](#integration-architecture)
7. [Testing Strategy](#testing-strategy)
8. [Performance Targets](#performance-targets)
9. [Risk Mitigation](#risk-mitigation)
10. [Future Roadmap](#future-roadmap)

---

## Executive Summary

### Goal
Enhance the existing Wikipedia extraction pipeline by integrating Wikidata's EntityData API to extract structured linked data (birth/death dates, family relationships, geographic data, etc.) without replacing current Wikipedia extraction functionality.

### Approach
- **Enhancement Layer:** Add new `structured_key_data` field to existing entity JSON
- **Clean Separation:** No modification to existing Wikipedia data fields
- **Graceful Degradation:** Wikipedia extraction continues even if Wikidata fails
- **Performance Optimized:** Multi-level caching and batch processing
- **Future Ready:** Designed for relationship queries and knowledge graphs

### Key Benefits
1. **Structured Data:** Machine-readable dates, relationships, and metadata
2. **Data Quality:** Canonical identifiers and standardized values from Wikidata
3. **Relationship Tracking:** Foundation for family networks, dynasty succession, battle participants
4. **Enhanced Analytics:** Enable timeline generation, geographic analysis, network visualization
5. **Backward Compatible:** Zero impact on existing extraction pipeline

---

## Context & Background

### Current Pipeline Capabilities
- Extracts Wikipedia pages with content, infobox, links, tables, images
- Depth-based traversal (configurable max depth)
- Entity type classification (human, place, event, organization, concept)
- Deduplication and error handling
- Excel summaries per entity type
- Pause/resume functionality with state persistence

### Gap Identified
- Wikipedia infoboxes are unstructured and inconsistent
- Missing canonical dates and relationships in machine-readable format
- No standardized entity references (father, mother, spouse, etc.)
- Limited ability to query relationships across entities

### Solution
Integrate Wikidata EntityData API to extract structured properties mapped to standardized Wikidata property IDs (P569 for birth date, P22 for father, etc.).

---

## Implementation Progress Tracking

### Phase 1: Foundation Setup - ✅ COMPLETED (2025-12-20)
- ✅ Step 1: Property Configuration System - COMPLETE
  - Created config/properties directory structure
  - Created YAML files: person.yaml, event.yaml, location.yaml, dynasty.yaml, political_entity.yaml, other.yaml
  - Implemented PropertyConfigManager class with full functionality

- ✅ Step 2: Wikidata API Client - COMPLETE
  - Implemented WikidataClient with retry logic and exponential backoff
  - Added rate limiting (1 req/sec default)
  - Batch fetching support (up to 50 entities)
  - Comprehensive error handling

- ✅ Step 3: Entity Reference Cache - COMPLETE
  - Implemented EntityReferenceCache with thread-safe operations
  - Disk persistence with pickle
  - Cache statistics tracking (hit rate, etc.)
  - Auto-save mechanism

### Phase 2: Data Processing Layer - ⏳ PENDING
- ⏳ Step 4: Build Data Parser & Transformer - NOT STARTED
- ⏳ Step 5: Design Enhanced Data Structure - NOT STARTED
- ⏳ Step 6: Build Entity Type Mapping System - NOT STARTED

### Phase 3: Integration - ⏳ PENDING
- ⏳ Step 7: Create Wikidata Enrichment Module - NOT STARTED
- ⏳ Step 8: Integrate into Existing Pipeline - NOT STARTED
- ⏳ Step 9: Update Excel Export Logic - NOT STARTED

### Phase 4: Testing & Optimization - ⏳ PENDING
- ⏳ Step 10: Testing Strategy - NOT STARTED
- ⏳ Step 11: Performance Optimization - NOT STARTED
- ⏳ Step 12: Documentation & Configuration - NOT STARTED

### Phase 5: Future Extensibility - ⏳ PENDING
- ⏳ Step 13: Prepare for Relationship Queries - NOT STARTED
- ⏳ Step 14: Add Dynamic Property Discovery - NOT STARTED

---

## Implementation Plan

### **Phase 1: Foundation Setup** (Steps 1-3) - ✅ COMPLETED

#### **Step 1: Create Property Configuration System**

**Objective:** Define which Wikidata properties to extract for each entity type

**Tasks:**
1. Create directory structure:
   ```
   config/
   └── properties/
       ├── person.yaml
       ├── event.yaml
       ├── location.yaml
       ├── dynasty.yaml
       └── political_entity.yaml
   ```

2. Define YAML schema for property configuration:
   ```yaml
   entity_type: person
   properties:
     - property_id: P569
       label: date_of_birth
       value_type: time
       priority: high

     - property_id: P22
       label: father
       value_type: wikibase-item
       priority: high
       fetch_depth: 1  # Extract basic info for linked entity
   ```

3. Property mappings per entity type:

   **Person (person.yaml):**
   - P569: date_of_birth (time)
   - P570: date_of_death (time)
   - P19: place_of_birth (wikibase-item)
   - P20: place_of_death (wikibase-item)
   - P22: father (wikibase-item)
   - P25: mother (wikibase-item)
   - P26: spouse (wikibase-item, multi-value)
   - P40: children (wikibase-item, multi-value)
   - P39: position_held (wikibase-item, multi-value with qualifiers)
   - P106: occupation (wikibase-item, multi-value)

   **Event (event.yaml):**
   - P580: start_time (time)
   - P582: end_time (time)
   - P276: location (wikibase-item)
   - P710: participant (wikibase-item, multi-value)
   - P793: significant_event (wikibase-item, multi-value)
   - P1120: casualties (quantity)

   **Location (location.yaml):**
   - P625: coordinate_location (coordinate)
   - P31: instance_of (wikibase-item)
   - P131: located_in_administrative_territory (wikibase-item)
   - P1082: population (quantity)
   - P2046: area (quantity)
   - P17: country (wikibase-item)

   **Dynasty (dynasty.yaml):**
   - P571: inception (time)
   - P576: dissolved_abolished (time)
   - P112: founded_by (wikibase-item)
   - P527: has_part_members (wikibase-item, multi-value)
   - P1001: applies_to_jurisdiction (wikibase-item)

   **Political Entity (political_entity.yaml):**
   - P31: instance_of (wikibase-item)
   - P571: inception (time)
   - P576: dissolved_abolished (time)
   - P35: head_of_state (wikibase-item, multi-value)
   - P6: head_of_government (wikibase-item, multi-value)
   - P36: capital (wikibase-item)
   - P1001: applies_to_jurisdiction (wikibase-item)

4. Build `PropertyConfigManager` class:
   ```python
   class PropertyConfigManager:
       def __init__(self, config_dir: str = "config/properties"):
           self.config_dir = Path(config_dir)
           self.configs = {}
           self._load_all_configs()

       def _load_all_configs(self):
           """Load all YAML configuration files"""
           pass

       def get_properties_for_type(self, entity_type: str) -> List[Dict]:
           """Get property configuration for entity type"""
           pass

       def add_property_dynamically(self, entity_type: str, property_config: Dict):
           """Add new property during runtime"""
           pass
   ```

**Deliverables:**
- 5 YAML configuration files
- PropertyConfigManager class with tests
- Documentation for adding new properties

---

#### **Step 2: Build Wikidata API Client**

**Objective:** Reliable API client for fetching Wikidata EntityData

**Tasks:**
1. Create `WikidataClient` class with core methods:
   ```python
   class WikidataClient:
       BASE_URL = "https://www.wikidata.org/wiki/Special:EntityData"

       def __init__(self, timeout: int = 10, max_retries: int = 3):
           self.timeout = timeout
           self.max_retries = max_retries
           self.session = requests.Session()
           self.rate_limiter = RateLimiter(requests_per_second=1)

       def fetch_entity_data(self, qid: str) -> Optional[Dict]:
           """Fetch entity data from Wikidata with retry logic"""
           pass

       def _make_request(self, qid: str) -> requests.Response:
           """Make HTTP request with rate limiting"""
           pass

       def _retry_with_backoff(self, func, *args, **kwargs):
           """Retry with exponential backoff"""
           pass
   ```

2. Implement retry logic:
   - Max 3 attempts
   - Exponential backoff: 1s, 2s, 4s
   - Handle HTTP errors: 429 (rate limit), 500 (server error), timeout
   - Log each retry attempt

3. Add request throttling:
   - Default: 1 request per second
   - Configurable via parameter
   - Respect Wikidata User-Agent guidelines

4. Response validation:
   - Check for valid JSON
   - Verify entity exists in response
   - Handle redirected entities
   - Validate required fields

5. Error handling:
   - Network errors → retry
   - Invalid QID → return None
   - Missing entity → return None
   - API rate limit → exponential backoff

**Deliverables:**
- WikidataClient class with comprehensive error handling
- Unit tests with mock API responses
- Integration tests with real API (5 sample entities)
- Performance logging

---

#### **Step 3: Implement Entity Reference Cache**

**Objective:** Prevent duplicate API calls for cross-referenced entities

**Tasks:**
1. Create `EntityReferenceCache` class:
   ```python
   class EntityReferenceCache:
       def __init__(self, cache_file: Optional[str] = None):
           self.cache: Dict[str, Dict] = {}
           self.cache_file = cache_file
           self.lock = threading.Lock()
           self.stats = {"hits": 0, "misses": 0}

           if cache_file and Path(cache_file).exists():
               self._load_from_disk()

       def get(self, qid: str) -> Optional[Dict]:
           """Get entity from cache, return None if not found"""
           pass

       def put(self, qid: str, entity_data: Dict):
           """Add entity to cache"""
           pass

       def _load_from_disk(self):
           """Load cache from pickle file"""
           pass

       def _save_to_disk(self):
           """Save cache to pickle file"""
           pass

       def get_hit_rate(self) -> float:
           """Calculate cache hit rate"""
           pass
   ```

2. Cache schema:
   ```python
   {
       "Q12345": {
           "qid": "Q12345",
           "name": "Entity Name",
           "description": "Brief description (4-5 words)",
           "type": "human",  # instance_of value
           "key_data": {
               # Minimal structured data for reference
               "birth_date": "1869-10-02",
               "death_date": "1948-01-30"
           },
           "cached_at": "2025-12-20T10:30:00"
       }
   }
   ```

3. Thread-safe operations:
   - Use `threading.Lock()` for concurrent access
   - Atomic get/put operations
   - Safe disk persistence

4. Cache persistence:
   - Save to pickle file every N operations
   - Load on initialization
   - Backup mechanism for corruption recovery

5. Performance tracking:
   - Track cache hits/misses
   - Calculate hit rate
   - Log statistics periodically

**Deliverables:**
- EntityReferenceCache class
- Thread-safe implementation
- Persistence mechanism
- Performance monitoring
- Unit tests

---

### **Phase 2: Data Processing Layer** (Steps 4-6)

#### **Step 4: Build Data Parser & Transformer**

**Objective:** Parse Wikidata JSON and transform to structured format

**Tasks:**
1. Create `WikidataParser` class:
   ```python
   class WikidataParser:
       def __init__(self, entity_cache: EntityReferenceCache):
           self.entity_cache = entity_cache

       def parse_entity(
           self,
           wikidata_json: Dict,
           property_config: List[Dict]
       ) -> Dict:
           """Parse Wikidata JSON to structured_key_data format"""
           pass

       def _parse_claim(self, claim: Dict, value_type: str) -> Any:
           """Parse individual claim based on value type"""
           pass

       def _parse_time_value(self, time_data: Dict) -> Dict:
           """Parse time datatype with precision"""
           pass

       def _parse_wikibase_item(self, item_data: Dict) -> Dict:
           """Parse entity reference, fetch from cache or API"""
           pass

       def _parse_quantity(self, quantity_data: Dict) -> Dict:
           """Parse quantity with units"""
           pass

       def _parse_coordinate(self, coord_data: Dict) -> Dict:
           """Parse geographic coordinates"""
           pass
   ```

2. Value type handlers:

   **Time (dates):**
   ```python
   {
       "value": "1869-10-02",
       "precision": 11,  # day precision (11), month (10), year (9)
       "calendar": "gregorian"
   }
   ```

   **Wikibase-item (entity reference):**
   ```python
   {
       "qid": "Q1001",
       "name": "Karamchand Gandhi",
       "description": "father of Mahatma Gandhi",
       "type": "human"
   }
   ```

   **Array (multi-value):**
   ```python
   [
       {"qid": "Q456", "name": "Spouse 1", ...},
       {"qid": "Q789", "name": "Spouse 2", ...}
   ]
   ```

   **Quantity:**
   ```python
   {
       "amount": "350000",
       "unit": "Q11573",  # square kilometer
       "unit_label": "square kilometer"
   }
   ```

   **Coordinate:**
   ```python
   {
       "latitude": 28.6139,
       "longitude": 77.2090,
       "precision": 0.0001,
       "globe": "earth"
   }
   ```

3. Handle edge cases:
   - Missing properties → skip, don't error
   - Multi-value properties → return array
   - Deprecated statements → ignore (check rank)
   - Preferred rank → prioritize
   - Qualifiers → include for position_held (start/end time)

4. Entity reference resolution:
   - Check cache first
   - If not in cache, fetch basic info (label, description, instance_of)
   - Add to cache for future use
   - Only go 1 level deep (no recursive nesting)

**Deliverables:**
- WikidataParser class with all value type handlers
- Edge case handling
- Unit tests for each value type
- Integration tests with real Wikidata responses

---

#### **Step 5: Design Enhanced Data Structure**

**Objective:** Define output schema for structured_key_data

**Tasks:**
1. Define complete schema:
   ```json
   {
       "title": "Mahatma Gandhi",
       "qid": "Q1001",
       "type": "human",

       // Existing Wikipedia fields...
       "content": {...},
       "infobox": {...},
       "links": {...},

       // NEW: Wikidata structured data
       "structured_key_data": {
           "P569": {
               "label": "date_of_birth",
               "value": {
                   "value": "1869-10-02",
                   "precision": 11,
                   "calendar": "gregorian"
               },
               "value_type": "time"
           },
           "P22": {
               "label": "father",
               "value": {
                   "qid": "Q5682621",
                   "name": "Karamchand Gandhi",
                   "description": "father of Mahatma Gandhi",
                   "type": "human"
               },
               "value_type": "wikibase-item"
           },
           "P26": {
               "label": "spouse",
               "value": [
                   {
                       "qid": "Q229858",
                       "name": "Kasturba Gandhi",
                       "description": "wife of Mahatma Gandhi",
                       "type": "human"
                   }
               ],
               "value_type": "array"
           },
           "P39": {
               "label": "position_held",
               "value": [
                   {
                       "position": {
                           "qid": "Q191954",
                           "name": "President of the Indian National Congress",
                           "type": "position"
                       },
                       "start_time": "1924-01-01",
                       "end_time": "1924-12-31"
                   }
               ],
               "value_type": "array_with_qualifiers"
           }
       },

       // NEW: Flag indicating success
       "structured_key_data_extracted": true,

       // Existing metadata
       "extraction_metadata": {
           "timestamp": "2025-12-20T10:30:00",
           "wikidata_fetch_time": 1.23,
           "cache_hits": 2
       }
   }
   ```

2. Create helper functions:
   ```python
   def create_structured_data_entry(
       property_id: str,
       label: str,
       value: Any,
       value_type: str
   ) -> Dict:
       """Create standardized structured data entry"""
       pass

   def validate_structured_data(data: Dict) -> bool:
       """Validate structured_key_data format"""
       pass
   ```

3. Documentation:
   - Schema documentation with examples
   - Value type reference guide
   - Migration guide for existing data

**Deliverables:**
- Complete schema definition
- Helper functions
- Validation logic
- Documentation with examples

---

#### **Step 6: Build Entity Type Mapping System**

**Objective:** Map Wikipedia entity types to Wikidata instance types and normalize to standard types

**Tasks:**

1. **Create Wikipedia Type to Standard Type Mapping:**

   This mapping normalizes diverse Wikipedia type labels to our 5 standard types plus "other".

   ```python
   # config/type_mappings.py

   # Wikipedia type → Our standard type
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

       # Fallback to "other"
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
       # Convert to lowercase and strip whitespace
       normalized_input = wikipedia_type.lower().strip()

       # Direct lookup in mapping
       if normalized_input in WIKIPEDIA_TYPE_TO_STANDARD_TYPE:
           return WIKIPEDIA_TYPE_TO_STANDARD_TYPE[normalized_input]

       # Fuzzy matching for partial matches
       for wiki_type, standard_type in WIKIPEDIA_TYPE_TO_STANDARD_TYPE.items():
           if wiki_type in normalized_input or normalized_input in wiki_type:
               return standard_type

       # Default fallback
       logger.warning(f"Unknown Wikipedia type '{wikipedia_type}', defaulting to 'other'")
       return "other"
   ```

2. **Create Wikidata Instance Type to Standard Type Mapping:**

   This maps Wikidata P31 (instance of) QIDs to our standard types.

   ```python
   # Wikidata P31 QID → Our standard type
   WIKIDATA_INSTANCE_TO_STANDARD_TYPE = {
       # Person types
       "Q5": "person",  # human
       "Q45371": "person",  # monarch
       "Q116": "person",  # monarch (duplicate)
       "Q82955": "person",  # politician
       "Q1097498": "person",  # military leader
       "Q189290": "person",  # military officer

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
   }

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
       # Check each instance QID
       for qid in instance_qids:
           if qid in WIKIDATA_INSTANCE_TO_STANDARD_TYPE:
               return WIKIDATA_INSTANCE_TO_STANDARD_TYPE[qid]

       # No match found
       logger.warning(f"Unknown Wikidata instance types {instance_qids}, defaulting to 'other'")
       return "other"
   ```

3. **Unified Type Detection Logic:**

   ```python
   class EntityTypeMapper:
       """
       Centralized entity type mapping and normalization.
       Handles both Wikipedia types and Wikidata P31 instance types.
       """

       def __init__(self):
           self.wikipedia_mapping = WIKIPEDIA_TYPE_TO_STANDARD_TYPE
           self.wikidata_mapping = WIKIDATA_INSTANCE_TO_STANDARD_TYPE
           self.valid_types = {
               "person", "location", "event", "dynasty", "political_entity", "other"
           }

       def get_standard_type(
           self,
           wikipedia_type: Optional[str] = None,
           wikidata_instance_qids: Optional[List[str]] = None
       ) -> str:
           """
           Determine standard entity type from available sources.
           Priority: Wikidata P31 > Wikipedia type > Default to 'other'

           Args:
               wikipedia_type: Type from Wikipedia extraction
               wikidata_instance_qids: List of P31 QIDs from Wikidata

           Returns:
               Standard type: person/location/event/dynasty/political_entity/other
           """
           # Priority 1: Wikidata P31 (instance of) - most authoritative
           if wikidata_instance_qids:
               wikidata_type = normalize_wikidata_instance_type(wikidata_instance_qids)
               if wikidata_type != "other":
                   return wikidata_type

           # Priority 2: Wikipedia type
           if wikipedia_type:
               wiki_type = normalize_wikipedia_type(wikipedia_type)
               if wiki_type != "other":
                   return wiki_type

           # Fallback: other
           return "other"

       def validate_type(self, entity_type: str) -> bool:
           """Check if type is one of our valid standard types"""
           return entity_type in self.valid_types

       def get_property_config_path(self, entity_type: str) -> str:
           """Get property configuration file path for entity type"""
           if entity_type == "person":
               return "config/properties/person.yaml"
           elif entity_type == "location":
               return "config/properties/location.yaml"
           elif entity_type == "event":
               return "config/properties/event.yaml"
           elif entity_type == "dynasty":
               return "config/properties/dynasty.yaml"
           elif entity_type == "political_entity":
               return "config/properties/political_entity.yaml"
           else:
               # For "other", use a minimal generic config
               return "config/properties/other.yaml"
   ```

4. **Integration into WikidataEnricher:**

   ```python
   class WikidataEnricher:
       def __init__(self, ...):
           # ... existing initialization
           self.type_mapper = EntityTypeMapper()

       def enrich_entity(self, wikipedia_data: Dict, entity: WikiEntity) -> Dict:
           # ... fetch wikidata_json ...

           # Determine entity type
           # Extract P31 from Wikidata
           wikidata_instances = self._extract_instance_of(wikidata_json)

           # Get standard type
           standard_type = self.type_mapper.get_standard_type(
               wikipedia_type=entity.type,
               wikidata_instance_qids=wikidata_instances
           )

           # Load appropriate property configuration
           property_config = self.config_manager.get_properties_for_type(standard_type)

           # ... continue with parsing ...

       def _extract_instance_of(self, wikidata_json: Dict) -> List[str]:
           """Extract P31 (instance of) QIDs from Wikidata JSON"""
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
                       qid = claim['mainsnak']['datavalue']['value']['id']
                       qids.append(qid)
                   except (KeyError, TypeError):
                       continue

               return qids
           except Exception as e:
               logger.error(f"Failed to extract P31 instance types: {e}")
               return []
   ```

5. **Fallback Logic:**
   - **Primary:** Use Wikidata P31 (instance of) - most authoritative
   - **Secondary:** Use Wikipedia type from extraction
   - **Tertiary:** Default to "other" for unknown types
   - **Override:** Allow manual type specification in entity metadata

6. **Type Override Mechanism:**
   ```python
   # Manual overrides for specific entities
   # config/type_overrides.json
   {
       "Q1001": "person",  # Force Mahatma Gandhi as person
       "Q83891": "dynasty"  # Force Mughal Empire as dynasty
   }

   def get_standard_type_with_override(
       self,
       qid: str,
       wikipedia_type: Optional[str] = None,
       wikidata_instance_qids: Optional[List[str]] = None
   ) -> str:
       """Get standard type with manual override support"""
       # Check for manual override first
       if qid in self.overrides:
           return self.overrides[qid]

       # Otherwise use normal logic
       return self.get_standard_type(wikipedia_type, wikidata_instance_qids)
   ```

7. **Create Generic "Other" Configuration:**

   For entities that don't fit person/location/event/dynasty/political_entity:

   ```yaml
   # config/properties/other.yaml
   entity_type: other
   description: Generic configuration for miscellaneous entities
   properties:
     - property_id: P31
       label: instance_of
       value_type: wikibase-item
       priority: high

     - property_id: P571
       label: inception
       value_type: time
       priority: medium

     - property_id: P576
       label: dissolved_abolished
       value_type: time
       priority: medium

     - property_id: P17
       label: country
       value_type: wikibase-item
       priority: low
   ```

**Deliverables:**
- Wikipedia type to standard type mapping dictionary
- Wikidata P31 to standard type mapping dictionary
- EntityTypeMapper class with unified logic
- Type validation and property config resolution
- Fallback mechanisms
- Override capability
- Generic "other" configuration
- Unit tests for all type mappings
- Documentation with examples

---

### **Phase 3: Integration** (Steps 7-9)

#### **Step 7: Create Wikidata Enrichment Module**

**Objective:** Orchestrate complete Wikidata enrichment process

**Tasks:**
1. Create `WikidataEnricher` class:
   ```python
   class WikidataEnricher:
       def __init__(
           self,
           config_manager: PropertyConfigManager,
           wikidata_client: WikidataClient,
           entity_cache: EntityReferenceCache,
           parser: WikidataParser
       ):
           self.config_manager = config_manager
           self.wikidata_client = wikidata_client
           self.entity_cache = entity_cache
           self.parser = parser
           self.logger = logging.getLogger(__name__)

       def enrich_entity(
           self,
           wikipedia_data: Dict,
           entity: WikiEntity
       ) -> Dict:
           """
           Enrich Wikipedia data with Wikidata structured data

           Returns: wikipedia_data with added structured_key_data field
           """
           pass

       def _fetch_wikidata(self, qid: str) -> Optional[Dict]:
           """Fetch from cache or API"""
           pass

       def _get_property_config(self, entity_type: str) -> List[Dict]:
           """Get property configuration for entity type"""
           pass
   ```

2. Enrichment workflow:
   ```python
   def enrich_entity(self, wikipedia_data: Dict, entity: WikiEntity) -> Dict:
       start_time = time.time()

       # Extract QID
       qid = wikipedia_data.get('qid')
       if not qid:
           self.logger.warning(f"No QID found for {entity.title}")
           wikipedia_data['structured_key_data_extracted'] = False
           return wikipedia_data

       # Check cache
       cached_data = self.entity_cache.get(qid)
       if cached_data:
           self.logger.debug(f"Cache hit for {qid}")

       # Fetch from Wikidata
       wikidata_json = self._fetch_wikidata(qid)
       if not wikidata_json:
           wikipedia_data['structured_key_data_extracted'] = False
           return wikipedia_data

       # Get property config
       entity_type = self._detect_entity_type(wikidata_json, entity.type)
       property_config = self._get_property_config(entity_type)

       # Parse and transform
       structured_data = self.parser.parse_entity(
           wikidata_json,
           property_config
       )

       # Add to wikipedia_data
       wikipedia_data['structured_key_data'] = structured_data
       wikipedia_data['structured_key_data_extracted'] = True

       # Add timing info
       fetch_time = time.time() - start_time
       wikipedia_data['extraction_metadata']['wikidata_fetch_time'] = fetch_time

       return wikipedia_data
   ```

3. Error handling:
   - Missing QID → set flag to false, continue
   - API timeout → retry, then fail gracefully
   - Parse error → log error, set flag to false
   - All errors logged with context

4. Performance tracking:
   - Log fetch time per entity
   - Track cache hit rate
   - Monitor API call count
   - Report statistics periodically

**Deliverables:**
- WikidataEnricher orchestrator class
- Complete enrichment workflow
- Error handling for all scenarios
- Performance tracking
- Unit and integration tests

---

#### **Step 8: Integrate into Existing Pipeline**

**Objective:** Add Wikidata enrichment to extraction pipeline

**Tasks:**
1. Modify `WikipediaExtractionPipeline` class:
   ```python
   class WikipediaExtractionPipeline:
       def __init__(self, config: Optional[PipelineConfig] = None):
           # Existing initialization...

           # NEW: Wikidata components
           if config.enable_wikidata_enrichment:
               self.property_config_manager = PropertyConfigManager()
               self.wikidata_client = WikidataClient()
               self.entity_cache = EntityReferenceCache(
                   cache_file=str(self.state_dir / "entity_cache.pkl")
               )
               self.wikidata_parser = WikidataParser(self.entity_cache)
               self.wikidata_enricher = WikidataEnricher(
                   self.property_config_manager,
                   self.wikidata_client,
                   self.entity_cache,
                   self.wikidata_parser
               )
   ```

2. Update `process_single_entity` method:
   ```python
   def process_single_entity(self, entity: WikiEntity) -> List[WikiEntity]:
       try:
           # Skip if already processed
           if entity.qid in self.processed_qids:
               return []

           # Extract Wikipedia data (EXISTING)
           data = asyncio.run(self.extract_entity(entity))
           if not data:
               return []

           # NEW: Enrich with Wikidata
           if self.config.enable_wikidata_enrichment:
               try:
                   data = self.wikidata_enricher.enrich_entity(data, entity)
               except Exception as e:
                   logger.error(f"Wikidata enrichment failed for {entity.qid}: {e}")
                   data['structured_key_data_extracted'] = False

           # Save data (EXISTING)
           self.save_entity_data(data, entity)

           # Mark as processed and process links (EXISTING)
           with self.lock:
               self.processed_qids.add(entity.qid)
               self.statistics.total_extracted += 1

           new_entities = self.process_entity_links(data, entity)
           return new_entities

       except Exception as e:
           logger.error(f"Error processing entity {entity.title}: {e}")
           raise
   ```

3. Add configuration options:
   ```python
   @dataclass
   class PipelineConfig:
       # Existing fields...

       # NEW: Wikidata configuration
       enable_wikidata_enrichment: bool = True
       wikidata_max_retries: int = 3
       wikidata_timeout: int = 10
       wikidata_rate_limit: float = 1.0  # requests per second
   ```

4. Update state persistence:
   ```python
   def _save_state(self):
       # Existing state save...

       # NEW: Save entity cache
       if hasattr(self, 'entity_cache'):
           self.entity_cache._save_to_disk()
   ```

**Deliverables:**
- Modified WikipediaExtractionPipeline class
- Configuration options
- Backward compatibility maintained
- State persistence for cache
- Integration tests

---

#### **Step 9: Update Excel Export Logic**

**Objective:** Include structured data in Excel summaries

**Tasks:**
1. Modify `_update_type_excel` method:
   ```python
   def _update_type_excel(self, entity_type: str, data: Dict, entity: WikiEntity):
       try:
           type_dir = self.base_path / entity_type
           excel_path = type_dir / f"{entity_type}_summary.xlsx"

           # Prepare row data (EXISTING)
           row_data = {
               'qid': data.get('qid'),
               'title': data.get('title'),
               'type': entity_type,
               # ... existing fields
           }

           # NEW: Add structured data fields
           if data.get('structured_key_data_extracted'):
               structured_data = data.get('structured_key_data', {})

               # Type-specific fields
               if entity_type == 'human':
                   row_data['birth_date'] = self._extract_simple_value(
                       structured_data, 'P569'
                   )
                   row_data['death_date'] = self._extract_simple_value(
                       structured_data, 'P570'
                   )
                   row_data['father_name'] = self._extract_entity_name(
                       structured_data, 'P22'
                   )
                   row_data['mother_name'] = self._extract_entity_name(
                       structured_data, 'P25'
                   )
                   row_data['spouse_count'] = self._count_array_values(
                       structured_data, 'P26'
                   )

               elif entity_type == 'event':
                   row_data['start_date'] = self._extract_simple_value(
                       structured_data, 'P580'
                   )
                   row_data['end_date'] = self._extract_simple_value(
                       structured_data, 'P582'
                   )
                   row_data['location'] = self._extract_entity_name(
                       structured_data, 'P276'
                   )
                   row_data['participant_count'] = self._count_array_values(
                       structured_data, 'P710'
                   )

               elif entity_type == 'place':
                   row_data['coordinates'] = self._extract_coordinates(
                       structured_data, 'P625'
                   )
                   row_data['population'] = self._extract_quantity(
                       structured_data, 'P1082'
                   )
                   row_data['parent_location'] = self._extract_entity_name(
                       structured_data, 'P131'
                   )

           # Save Excel (EXISTING logic)
           # ...
   ```

2. Helper methods for data extraction:
   ```python
   def _extract_simple_value(self, structured_data: Dict, property_id: str) -> str:
       """Extract simple value (dates, strings)"""
       if property_id in structured_data:
           value = structured_data[property_id].get('value')
           if isinstance(value, dict):
               return value.get('value', '')
           return str(value)
       return ''

   def _extract_entity_name(self, structured_data: Dict, property_id: str) -> str:
       """Extract entity name from wikibase-item"""
       if property_id in structured_data:
           value = structured_data[property_id].get('value', {})
           return value.get('name', '')
       return ''

   def _count_array_values(self, structured_data: Dict, property_id: str) -> int:
       """Count items in array"""
       if property_id in structured_data:
           value = structured_data[property_id].get('value', [])
           if isinstance(value, list):
               return len(value)
       return 0

   def _extract_coordinates(self, structured_data: Dict, property_id: str) -> str:
       """Extract coordinates as string"""
       if property_id in structured_data:
           value = structured_data[property_id].get('value', {})
           lat = value.get('latitude')
           lon = value.get('longitude')
           if lat and lon:
               return f"{lat}, {lon}"
       return ''

   def _extract_quantity(self, structured_data: Dict, property_id: str) -> str:
       """Extract quantity with unit"""
       if property_id in structured_data:
           value = structured_data[property_id].get('value', {})
           amount = value.get('amount')
           unit = value.get('unit_label', '')
           if amount:
               return f"{amount} {unit}".strip()
       return ''
   ```

3. Update master Excel:
   ```python
   def update_master_excel(self):
       # Existing logic...

       # Add structured data availability
       rows.append({
           # ... existing fields
           'has_structured_data': data.get('structured_key_data_extracted', False),
           'num_structured_properties': len(
               data.get('structured_key_data', {})
           )
       })
   ```

**Deliverables:**
- Updated Excel export with structured data columns
- Helper methods for data extraction
- Type-specific column mapping
- Updated master summary
- Documentation of new columns

---

### **Phase 4: Testing & Optimization** (Steps 10-12)

#### **Step 10: Testing Strategy**

**Objective:** Comprehensive testing at all levels

**Tasks:**
1. Unit tests for each component:
   ```python
   # test_property_config_manager.py
   def test_load_person_config():
       manager = PropertyConfigManager()
       config = manager.get_properties_for_type('human')
       assert 'P569' in [p['property_id'] for p in config]

   # test_wikidata_client.py
   @mock.patch('requests.Session.get')
   def test_fetch_entity_success(mock_get):
       mock_get.return_value.json.return_value = {...}
       client = WikidataClient()
       data = client.fetch_entity_data('Q1001')
       assert data is not None

   # test_entity_cache.py
   def test_cache_hit():
       cache = EntityReferenceCache()
       cache.put('Q123', {'name': 'Test'})
       assert cache.get('Q123')['name'] == 'Test'
       assert cache.get_hit_rate() == 1.0

   # test_wikidata_parser.py
   def test_parse_time_value():
       parser = WikidataParser(EntityReferenceCache())
       result = parser._parse_time_value({
           'time': '+1869-10-02T00:00:00Z',
           'precision': 11
       })
       assert result['value'] == '1869-10-02'
   ```

2. Integration tests with real APIs:
   ```python
   # test_integration.py
   def test_full_enrichment_mahatma_gandhi():
       """Test with real Wikidata API for Q1001 (Mahatma Gandhi)"""
       enricher = WikidataEnricher(...)
       wikipedia_data = {'qid': 'Q1001', 'title': 'Mahatma Gandhi'}
       result = enricher.enrich_entity(wikipedia_data, entity)

       assert result['structured_key_data_extracted'] == True
       assert 'P569' in result['structured_key_data']
       assert result['structured_key_data']['P569']['value']['value'] == '1869-10-02'

   @pytest.mark.parametrize("qid,entity_type", [
       ('Q1001', 'human'),  # Mahatma Gandhi
       ('Q1156', 'place'),  # Mumbai
       ('Q129053', 'event'),  # Battle of Panipat
       ('Q83891', 'dynasty'),  # Mughal Empire
   ])
   def test_multiple_entity_types(qid, entity_type):
       """Test enrichment for different entity types"""
       pass
   ```

3. Error scenario tests:
   ```python
   def test_missing_qid():
       wikipedia_data = {'title': 'Unknown Entity'}
       result = enricher.enrich_entity(wikipedia_data, entity)
       assert result['structured_key_data_extracted'] == False

   @mock.patch('requests.Session.get')
   def test_api_timeout_retry(mock_get):
       mock_get.side_effect = requests.Timeout()
       client = WikidataClient()
       data = client.fetch_entity_data('Q1001')
       assert mock_get.call_count == 3  # max retries

   def test_malformed_response():
       parser = WikidataParser(EntityReferenceCache())
       result = parser.parse_entity({'invalid': 'data'}, [])
       assert result == {}
   ```

4. Performance tests:
   ```python
   def test_cache_performance():
       cache = EntityReferenceCache()
       # Add 1000 entities
       for i in range(1000):
           cache.put(f'Q{i}', {'name': f'Entity {i}'})

       # Test lookup speed
       start = time.time()
       for i in range(1000):
           cache.get(f'Q{i}')
       duration = time.time() - start

       assert duration < 0.1  # Should be near-instant

   def test_enrichment_timing():
       """Ensure enrichment doesn't add >2s per entity"""
       start = time.time()
       result = enricher.enrich_entity(wikipedia_data, entity)
       duration = time.time() - start

       assert duration < 2.0
   ```

**Deliverables:**
- Comprehensive unit test suite
- Integration tests with real APIs
- Error scenario tests
- Performance tests
- CI/CD pipeline integration
- Test coverage report (target: >80%)

---

#### **Step 11: Performance Optimization**

**Objective:** Minimize performance impact on extraction pipeline

**Tasks:**
1. Batch property fetching:
   ```python
   def fetch_multiple_entities(self, qids: List[str]) -> Dict[str, Dict]:
       """
       Fetch multiple entities in single API call
       Wikidata supports: /entities?ids=Q1|Q2|Q3
       """
       # Group QIDs in batches of 50 (API limit)
       batches = [qids[i:i+50] for i in range(0, len(qids), 50)]

       results = {}
       for batch in batches:
           response = self._make_batch_request(batch)
           results.update(response)

       return results
   ```

2. Request caching with TTL:
   ```python
   class WikidataClient:
       def __init__(self):
           self.request_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour TTL

       def fetch_entity_data(self, qid: str) -> Optional[Dict]:
           # Check cache first
           if qid in self.request_cache:
               return self.request_cache[qid]

           # Fetch from API
           data = self._make_request(qid)
           self.request_cache[qid] = data
           return data
   ```

3. Optimize JSON parsing:
   ```python
   # Use ujson for faster JSON parsing
   import ujson as json

   def parse_entity(self, wikidata_json: Dict, property_config: List[Dict]) -> Dict:
       # Only extract configured properties, skip rest
       property_ids = {p['property_id'] for p in property_config}

       claims = wikidata_json.get('entities', {}).values()[0].get('claims', {})
       filtered_claims = {k: v for k, v in claims.items() if k in property_ids}

       # Process only filtered claims
       return self._parse_claims(filtered_claims, property_config)
   ```

4. Parallel entity reference lookups:
   ```python
   def _resolve_entity_references(self, entity_qids: List[str]) -> Dict[str, Dict]:
       """Resolve multiple entity references in parallel"""
       with ThreadPoolExecutor(max_workers=5) as executor:
           futures = {
               executor.submit(self._fetch_entity_reference, qid): qid
               for qid in entity_qids
           }

           results = {}
           for future in as_completed(futures):
               qid = futures[future]
               results[qid] = future.result()

           return results
   ```

5. Performance monitoring:
   ```python
   class PerformanceMonitor:
       def __init__(self):
           self.metrics = {
               'api_calls': 0,
               'cache_hits': 0,
               'cache_misses': 0,
               'avg_fetch_time': [],
               'total_enrichment_time': 0
           }

       def log_metrics(self):
           logger.info(f"Wikidata Performance Metrics:")
           logger.info(f"  API calls: {self.metrics['api_calls']}")
           logger.info(f"  Cache hit rate: {self._calculate_hit_rate():.2%}")
           logger.info(f"  Avg fetch time: {self._avg_fetch_time():.2f}s")
   ```

**Deliverables:**
- Batch fetching implementation
- Request caching with TTL
- Optimized JSON parsing
- Parallel processing for entity references
- Performance monitoring dashboard
- Benchmark report

---

#### **Step 12: Documentation & Configuration**

**Objective:** Complete documentation for users and developers

**Tasks:**
1. Configuration guide (`docs/wikidata-configuration-guide.md`):
   - How to add new properties to YAML files
   - Property ID reference (where to find Wikidata property IDs)
   - Entity type mapping configuration
   - Cache configuration and management
   - Performance tuning parameters

2. Data structure documentation (`docs/wikidata-data-structure.md`):
   - Complete schema reference
   - Value type specifications
   - Example outputs for each entity type
   - How to query structured data

3. API reference (`docs/wikidata-api-reference.md`):
   - WikidataClient methods
   - PropertyConfigManager usage
   - EntityReferenceCache operations
   - WikidataParser functions

4. User guide (`docs/wikidata-user-guide.md`):
   - Enabling/disabling Wikidata enrichment
   - Interpreting structured data in JSON files
   - Excel column reference
   - Troubleshooting common issues

5. Developer guide (`docs/wikidata-developer-guide.md`):
   - Architecture overview
   - Adding new value type handlers
   - Extending property configurations
   - Performance optimization techniques

6. Inline code documentation:
   ```python
   def enrich_entity(self, wikipedia_data: Dict, entity: WikiEntity) -> Dict:
       """
       Enrich Wikipedia data with Wikidata structured data.

       This method fetches entity data from Wikidata API, parses configured
       properties, and adds a structured_key_data field to the wikipedia_data
       dictionary. The process includes caching, error handling, and performance
       tracking.

       Args:
           wikipedia_data: Dictionary containing Wikipedia extraction results
           entity: WikiEntity object with metadata (qid, type, etc.)

       Returns:
           Dictionary with added structured_key_data field and extraction flag

       Raises:
           WikidataAPIError: If API calls fail after max retries
           ParseError: If Wikidata response cannot be parsed

       Example:
           >>> enricher = WikidataEnricher(...)
           >>> wikipedia_data = {'qid': 'Q1001', 'title': 'Gandhi'}
           >>> result = enricher.enrich_entity(wikipedia_data, entity)
           >>> result['structured_key_data_extracted']
           True
       """
   ```

**Deliverables:**
- 5 comprehensive documentation files
- Inline docstrings for all classes/methods
- Configuration examples
- Troubleshooting guide
- FAQ document

---

### **Phase 5: Future Extensibility** (Steps 13-14)

#### **Step 13: Prepare for Relationship Queries**

**Objective:** Design data structure to support future relationship queries

**Tasks:**
1. Relationship data structure:
   ```python
   # Add to structured_key_data
   "relationships": {
       "family": {
           "father": {"qid": "Q123", "name": "..."},
           "mother": {"qid": "Q456", "name": "..."},
           "children": [{"qid": "Q789", "name": "..."}, ...],
           "spouse": [{"qid": "Q101", "name": "..."}, ...]
       },
       "political": {
           "positions_held": [
               {
                   "position": {"qid": "Q...", "name": "..."},
                   "start": "1924",
                   "end": "1925"
               }
           ]
       },
       "geographic": {
           "birth_place": {"qid": "Q...", "name": "..."},
           "death_place": {"qid": "Q...", "name": "..."},
           "associated_places": [...]
       }
   }
   ```

2. Relationship tracking configuration:
   ```python
   @dataclass
   class PipelineConfig:
       # ...
       enable_relationship_tracking: bool = False  # Future feature
       relationship_depth: int = 2  # How many hops to track
   ```

3. Placeholder methods:
   ```python
   class RelationshipGraph:
       """Future: Build knowledge graph from relationships"""

       def build_family_network(self, root_qid: str) -> Dict:
           """Build family tree from structured data"""
           pass

       def build_dynasty_succession(self, dynasty_qid: str) -> List[Dict]:
           """Build succession chain for dynasty"""
           pass

       def build_battle_network(self, battle_qid: str) -> Dict:
           """Build participant network for battle"""
           pass

       def query_relationships(
           self,
           qid: str,
           relationship_type: str,
           depth: int = 1
       ) -> List[Dict]:
           """Generic relationship query"""
           pass
   ```

4. Metadata for relationship tracking:
   ```python
   # Add to extraction_metadata
   "relationship_metadata": {
       "family_connections": 5,  # Number of family members found
       "political_connections": 3,
       "geographic_connections": 2,
       "total_unique_entities_referenced": 10
   }
   ```

**Deliverables:**
- Relationship data structure design
- Configuration flags for future features
- Placeholder classes and methods
- Documentation of future capabilities

---

#### **Step 14: Add Dynamic Property Discovery**

**Objective:** Discover and suggest new properties during extraction

**Tasks:**
1. Property discovery logger:
   ```python
   class PropertyDiscoveryLogger:
       def __init__(self, log_file: str = "discovered_properties.json"):
           self.log_file = log_file
           self.discovered = {}

       def log_property(
           self,
           property_id: str,
           entity_type: str,
           sample_value: Any
       ):
           """Log discovered property not in configuration"""
           if property_id not in self.discovered:
               self.discovered[property_id] = {
                   'property_id': property_id,
                   'found_in_types': set(),
                   'sample_values': [],
                   'count': 0
               }

           self.discovered[property_id]['found_in_types'].add(entity_type)
           self.discovered[property_id]['sample_values'].append(sample_value)
           self.discovered[property_id]['count'] += 1

       def save_report(self):
           """Save discovery report"""
           pass
   ```

2. Integration into parser:
   ```python
   def parse_entity(self, wikidata_json: Dict, property_config: List[Dict]) -> Dict:
       configured_props = {p['property_id'] for p in property_config}

       all_claims = wikidata_json.get('claims', {})

       # Parse configured properties
       structured_data = {}
       for prop_id, claims in all_claims.items():
           if prop_id in configured_props:
               # Parse as usual
               pass
           else:
               # Log as discovered
               self.property_discovery_logger.log_property(
                   prop_id,
                   entity_type,
                   claims[0]  # Sample value
               )

       return structured_data
   ```

3. CLI command for property review:
   ```python
   # Add to pipeline CLI
   def review_discovered_properties():
       """Review properties discovered during extraction"""
       logger = PropertyDiscoveryLogger()
       report = logger.load_report()

       print("\nDiscovered Properties (not in configuration):")
       for prop_id, data in sorted(
           report.items(),
           key=lambda x: x[1]['count'],
           reverse=True
       ):
           print(f"\n{prop_id}: Found {data['count']} times")
           print(f"  Entity types: {', '.join(data['found_in_types'])}")
           print(f"  Sample value: {data['sample_values'][0]}")

           # Prompt to add
           add = input("Add to configuration? (y/n): ")
           if add.lower() == 'y':
               entity_type = input("Entity type: ")
               label = input("Property label: ")
               # Add to configuration file
   ```

4. Hot-reload configuration:
   ```python
   class PropertyConfigManager:
       def reload_config(self, entity_type: str):
           """Reload configuration from disk"""
           config_file = self.config_dir / f"{entity_type}.yaml"
           with open(config_file) as f:
               self.configs[entity_type] = yaml.safe_load(f)
           logger.info(f"Reloaded configuration for {entity_type}")
   ```

5. Property usage statistics:
   ```python
   class PropertyUsageTracker:
       def __init__(self):
           self.usage = {}  # {property_id: count}

       def track(self, property_id: str):
           self.usage[property_id] = self.usage.get(property_id, 0) + 1

       def get_report(self) -> Dict:
           """Get usage statistics"""
           return sorted(
               self.usage.items(),
               key=lambda x: x[1],
               reverse=True
           )
   ```

**Deliverables:**
- PropertyDiscoveryLogger class
- Integration into parsing workflow
- CLI command for property review
- Hot-reload configuration capability
- Usage statistics tracking
- Admin documentation

---

## Technical Specifications

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Wikipedia Extraction Pipeline                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Extract Wikipedia│
                    │  Page Data       │
                    └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Wikidata Enrichment Layer                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. PropertyConfigManager                                │  │
│  │     - Load YAML configs per entity type                  │  │
│  │     - Cache property mappings                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. WikidataClient                                       │  │
│  │     - Fetch EntityData from Wikidata API                │  │
│  │     - Retry logic & rate limiting                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. EntityReferenceCache                                 │  │
│  │     - Check cache for QID                                │  │
│  │     - Return cached data or fetch from API               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  4. WikidataParser                                       │  │
│  │     - Parse Wikidata JSON response                       │  │
│  │     - Extract configured properties                      │  │
│  │     - Transform to structured format                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  5. WikidataEnricher (Orchestrator)                      │  │
│  │     - Coordinate all components                          │  │
│  │     - Add structured_key_data to entity                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Save Enhanced  │
                    │  Entity JSON    │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Update Excel   │
                    │  Summaries      │
                    └─────────────────┘
```

### Component Dependencies

```python
# requirements.txt additions
pyyaml>=6.0
requests>=2.31.0
ujson>=5.8.0  # Optional: faster JSON parsing
cachetools>=5.3.0  # For TTL cache
```

### File Structure

```
wikipedia-dashboard/
├── Python_Helper/
│   ├── Extraction_Pipeline.ipynb
│   ├── wiki_extract.py
│   └── wikidata/
│       ├── __init__.py
│       ├── client.py              # WikidataClient
│       ├── cache.py               # EntityReferenceCache
│       ├── parser.py              # WikidataParser
│       ├── enricher.py            # WikidataEnricher
│       ├── config_manager.py      # PropertyConfigManager
│       └── utils.py               # Helper functions
├── config/
│   └── properties/
│       ├── person.yaml
│       ├── event.yaml
│       ├── location.yaml
│       ├── dynasty.yaml
│       └── political_entity.yaml
├── docs/
│   ├── wikidata-integration-implementation-plan.md
│   ├── wikidata-configuration-guide.md
│   ├── wikidata-data-structure.md
│   ├── wikidata-api-reference.md
│   ├── wikidata-user-guide.md
│   └── wikidata-developer-guide.md
├── tests/
│   └── wikidata/
│       ├── test_client.py
│       ├── test_cache.py
│       ├── test_parser.py
│       ├── test_enricher.py
│       ├── test_config_manager.py
│       └── test_integration.py
└── pipeline_state/
    ├── pipeline_state.pkl
    └── entity_cache.pkl           # NEW: Entity reference cache
```

---

## Data Structure Design

### Complete Output Schema

```json
{
  "title": "Mahatma Gandhi",
  "qid": "Q1001",
  "type": "human",

  "content": {
    "extract": "Mohandas Karamchand Gandhi was an Indian lawyer...",
    "summary": "...",
    "description": "pre-eminent leader of Indian nationalism"
  },

  "infobox": {
    "Born": "2 October 1869, Porbandar",
    "Died": "30 January 1948 (aged 78), New Delhi"
  },

  "links": {
    "internal_links": [
      {
        "title": "Indian independence movement",
        "qid": "Q129286",
        "type": "event",
        "shortDesc": "Movement to end British rule"
      }
    ]
  },

  "tables": [...],
  "images": [...],
  "chunks": [...],

  "metadata": {
    "page_id": "19379",
    "page_length": 125432,
    "last_modified": "2025-12-15T10:30:00Z"
  },

  "structured_key_data": {
    "P569": {
      "label": "date_of_birth",
      "value": {
        "value": "1869-10-02",
        "precision": 11,
        "calendar": "gregorian"
      },
      "value_type": "time"
    },
    "P570": {
      "label": "date_of_death",
      "value": {
        "value": "1948-01-30",
        "precision": 11,
        "calendar": "gregorian"
      },
      "value_type": "time"
    },
    "P19": {
      "label": "place_of_birth",
      "value": {
        "qid": "Q200017",
        "name": "Porbandar",
        "description": "city in Gujarat, India",
        "type": "city"
      },
      "value_type": "wikibase-item"
    },
    "P20": {
      "label": "place_of_death",
      "value": {
        "qid": "Q987",
        "name": "New Delhi",
        "description": "capital of India",
        "type": "city"
      },
      "value_type": "wikibase-item"
    },
    "P22": {
      "label": "father",
      "value": {
        "qid": "Q5682621",
        "name": "Karamchand Gandhi",
        "description": "father of Mahatma Gandhi",
        "type": "human"
      },
      "value_type": "wikibase-item"
    },
    "P25": {
      "label": "mother",
      "value": {
        "qid": "Q3042895",
        "name": "Putlibai Gandhi",
        "description": "mother of Mahatma Gandhi",
        "type": "human"
      },
      "value_type": "wikibase-item"
    },
    "P26": {
      "label": "spouse",
      "value": [
        {
          "qid": "Q229858",
          "name": "Kasturba Gandhi",
          "description": "wife of Mahatma Gandhi",
          "type": "human"
        }
      ],
      "value_type": "array"
    },
    "P40": {
      "label": "children",
      "value": [
        {
          "qid": "Q1346144",
          "name": "Harilal Gandhi",
          "description": "eldest son of Mahatma Gandhi",
          "type": "human"
        },
        {
          "qid": "Q3042896",
          "name": "Manilal Gandhi",
          "description": "son of Mahatma Gandhi",
          "type": "human"
        },
        {
          "qid": "Q3042897",
          "name": "Ramdas Gandhi",
          "description": "son of Mahatma Gandhi",
          "type": "human"
        },
        {
          "qid": "Q3042898",
          "name": "Devdas Gandhi",
          "description": "youngest son of Mahatma Gandhi",
          "type": "human"
        }
      ],
      "value_type": "array"
    },
    "P39": {
      "label": "position_held",
      "value": [
        {
          "position": {
            "qid": "Q191954",
            "name": "President of the Indian National Congress",
            "description": "political position",
            "type": "position"
          },
          "start_time": "1924-01-01",
          "end_time": "1924-12-31"
        }
      ],
      "value_type": "array_with_qualifiers"
    },
    "P106": {
      "label": "occupation",
      "value": [
        {
          "qid": "Q40348",
          "name": "lawyer",
          "description": "legal professional",
          "type": "occupation"
        },
        {
          "qid": "Q82955",
          "name": "politician",
          "description": "person involved in politics",
          "type": "occupation"
        }
      ],
      "value_type": "array"
    }
  },

  "structured_key_data_extracted": true,

  "extraction_metadata": {
    "timestamp": "2025-12-20T15:45:00",
    "depth": 0,
    "parent_qid": null,
    "pipeline_version": "2.0",
    "wikidata_fetch_time": 1.23,
    "cache_hits": 4,
    "relationship_metadata": {
      "family_connections": 7,
      "political_connections": 1,
      "total_unique_entities_referenced": 10
    }
  }
}
```

---

## Integration Architecture

### Call Sequence Diagram

```
User                Pipeline               WikidataEnricher    WikidataClient      EntityCache       WikidataParser
 │                     │                          │                   │                  │                 │
 │   run(entity)       │                          │                   │                  │                 │
 │────────────────────>│                          │                   │                  │                 │
 │                     │                          │                   │                  │                 │
 │                     │  extract_wikipedia()     │                   │                  │                 │
 │                     │──────────────────────┐   │                   │                  │                 │
 │                     │                      │   │                   │                  │                 │
 │                     │<─────────────────────┘   │                   │                  │                 │
 │                     │  [wikipedia_data]        │                   │                  │                 │
 │                     │                          │                   │                  │                 │
 │                     │  enrich_entity()         │                   │                  │                 │
 │                     │─────────────────────────>│                   │                  │                 │
 │                     │                          │  get(qid)         │                  │                 │
 │                     │                          │──────────────────────────────────────>│                 │
 │                     │                          │                   │  [cache miss]    │                 │
 │                     │                          │<──────────────────────────────────────│                 │
 │                     │                          │                   │                  │                 │
 │                     │                          │  fetch_entity_data(qid)              │                 │
 │                     │                          │──────────────────>│                  │                 │
 │                     │                          │                   │  [API call]      │                 │
 │                     │                          │                   │──────────────┐   │                 │
 │                     │                          │                   │              │   │                 │
 │                     │                          │  [wikidata_json]  │<─────────────┘   │                 │
 │                     │                          │<──────────────────│                  │                 │
 │                     │                          │                   │                  │                 │
 │                     │                          │  parse_entity()   │                  │                 │
 │                     │                          │──────────────────────────────────────────────────────>│
 │                     │                          │                   │                  │  [parse claims]│
 │                     │                          │                   │                  │  [resolve refs]│
 │                     │                          │  [structured_data]│                  │                 │
 │                     │                          │<──────────────────────────────────────────────────────│
 │                     │                          │                   │                  │                 │
 │                     │  [enriched_data]         │                   │                  │                 │
 │                     │<─────────────────────────│                   │                  │                 │
 │                     │                          │                   │                  │                 │
 │                     │  save_entity_data()      │                   │                  │                 │
 │                     │──────────────────────┐   │                   │                  │                 │
 │                     │                      │   │                   │                  │                 │
 │                     │<─────────────────────┘   │                   │                  │                 │
 │                     │                          │                   │                  │                 │
 │   [success]         │                          │                   │                  │                 │
 │<────────────────────│                          │                   │                  │                 │
```

---

## Testing Strategy

### Test Coverage Matrix

| Component | Unit Tests | Integration Tests | Error Tests | Performance Tests |
|-----------|-----------|------------------|-------------|------------------|
| PropertyConfigManager | ✓ | - | ✓ | - |
| WikidataClient | ✓ | ✓ | ✓ | ✓ |
| EntityReferenceCache | ✓ | - | ✓ | ✓ |
| WikidataParser | ✓ | ✓ | ✓ | - |
| WikidataEnricher | ✓ | ✓ | ✓ | ✓ |
| Pipeline Integration | - | ✓ | ✓ | ✓ |

### Test Entities for Integration Testing

1. **Q1001 - Mahatma Gandhi** (Person)
   - Complex family relationships
   - Multiple positions held
   - Well-documented in Wikidata

2. **Q1156 - Mumbai** (Location)
   - Geographic coordinates
   - Administrative hierarchy
   - Population data

3. **Q129053 - Battle of Panipat** (Event)
   - Start/end dates
   - Location
   - Participants

4. **Q83891 - Mughal Empire** (Political Entity/Dynasty)
   - Inception/dissolution dates
   - Territory
   - Rulers

5. **Q1156 - Delhi Sultanate** (Dynasty)
   - Succession chain
   - Members
   - Territory

### Performance Benchmarks

| Metric | Target | Acceptable | Needs Improvement |
|--------|--------|-----------|------------------|
| API Response Time | < 1s | 1-2s | > 2s |
| Cache Hit Rate | > 70% | 50-70% | < 50% |
| Enrichment Overhead | < 20% | 20-30% | > 30% |
| Memory Usage | < 100MB | 100-200MB | > 200MB |
| Parsing Time | < 0.1s | 0.1-0.5s | > 0.5s |

---

## Performance Targets

### Baseline Metrics (Without Wikidata)

- Average extraction time per entity: ~3s
- Entities per minute: ~20
- Memory usage: ~150MB

### Target Metrics (With Wikidata)

- Average extraction time per entity: < 4s (< 33% increase)
- Entities per minute: > 15
- Memory usage: < 200MB
- Cache hit rate: > 60%
- Wikidata API calls: < 2 per entity (with caching)

### Optimization Strategies

1. **Caching Strategy:**
   - Property mapping cache: 100% hit rate after first load
   - Entity reference cache: Target 60-70% hit rate
   - Request cache with TTL: Reduce duplicate API calls

2. **Batch Processing:**
   - Fetch multiple entity references in single API call
   - Process entity references in parallel (ThreadPoolExecutor)

3. **Selective Fetching:**
   - Only fetch configured properties
   - Skip properties that add noise
   - Filter before parsing (reduce JSON processing)

4. **Rate Limiting:**
   - Default: 1 request/second
   - Configurable for different Wikidata API tiers
   - Exponential backoff on rate limit errors

---

## Risk Mitigation

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|-----------|--------|---------------------|
| API Rate Limiting | High | Medium | Implement request throttling, caching, batch requests |
| Missing QIDs | Medium | Low | Graceful degradation, continue with Wikipedia-only data |
| API Downtime | Low | High | Retry logic, fallback to cached data, set extraction flag to false |
| Data Quality Issues | Medium | Medium | Validate responses, handle malformed data, log errors |
| Performance Degradation | Medium | High | Caching strategy, parallel processing, performance monitoring |
| Configuration Errors | Low | Medium | Validate YAML on load, provide clear error messages |
| Cache Corruption | Low | Medium | Backup mechanism, corruption detection, auto-rebuild |
| Memory Overflow | Low | High | TTL cache with max size, periodic cleanup, monitoring |

### Contingency Plans

1. **Wikidata API Unavailable:**
   - Set `enable_wikidata_enrichment = False`
   - Continue with Wikipedia-only extraction
   - Log entities that need retry
   - Batch re-process when API is back

2. **Performance Below Target:**
   - Increase cache size
   - Reduce configured properties
   - Disable enrichment for low-priority entity types
   - Use batch processing more aggressively

3. **Data Quality Issues:**
   - Manual review of discovered properties
   - Whitelist/blacklist for properties
   - Validation rules per value type
   - Fallback to Wikipedia data if Wikidata is suspect

---

## Future Roadmap

### Phase 6: Relationship Graph (Q1 2026)

- Build in-memory knowledge graph
- Query family networks
- Dynasty succession chains
- Battle participant networks
- Geographic hierarchies

### Phase 7: Advanced Analytics (Q2 2026)

- Auto-generate timelines
- Demographic analysis (birth/death date distributions)
- Geographic visualization
- Network analysis (centrality, communities)

### Phase 8: Data Quality & Validation (Q3 2026)

- Cross-validate Wikipedia vs Wikidata
- Identify inconsistencies
- Flag missing data
- Suggest corrections

### Phase 9: AI-Powered Enhancement (Q4 2026)

- Entity linking with LLMs
- Relationship extraction from text
- Missing data inference
- Automated property discovery

---

## Appendix

### Wikidata Property ID Reference

**Common Properties:**
- P31: instance of
- P569: date of birth
- P570: date of death
- P19: place of birth
- P20: place of death
- P22: father
- P25: mother
- P26: spouse
- P40: child
- P39: position held
- P106: occupation
- P580: start time
- P582: end time
- P625: coordinate location

**Full Reference:** https://www.wikidata.org/wiki/Wikidata:List_of_properties

### Example YAML Configuration

**config/properties/person.yaml:**
```yaml
entity_type: person
description: Configuration for human entities
properties:
  - property_id: P569
    label: date_of_birth
    value_type: time
    priority: high

  - property_id: P570
    label: date_of_death
    value_type: time
    priority: high

  - property_id: P19
    label: place_of_birth
    value_type: wikibase-item
    priority: medium
    fetch_depth: 1

  - property_id: P22
    label: father
    value_type: wikibase-item
    priority: high
    fetch_depth: 1

  - property_id: P25
    label: mother
    value_type: wikibase-item
    priority: high
    fetch_depth: 1

  - property_id: P26
    label: spouse
    value_type: wikibase-item
    priority: medium
    multi_value: true
    fetch_depth: 1

  - property_id: P40
    label: children
    value_type: wikibase-item
    priority: low
    multi_value: true
    fetch_depth: 1
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-20
**Status:** Ready for Implementation
**Estimated Implementation Time:** 6-8 weeks (with testing)

---

*This implementation plan follows senior developer best practices: modular design, comprehensive error handling, performance optimization, thorough testing, complete documentation, and future extensibility while maintaining pragmatic simplicity.*
