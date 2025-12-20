# Wikidata Integration Module

This module provides functionality to enrich Wikipedia extraction data with structured information from Wikidata's EntityData API.

## Status

**Current Phase:** Phase 1 Complete ✅
**Version:** 1.0.0
**Last Updated:** 2025-12-20

## Components

### ✅ PropertyConfigManager
Manages YAML-based property configurations for different entity types.

**Features:**
- Loads property configurations from `config/properties/`
- Entity type normalization
- Dynamic property addition
- Configuration validation
- Hot-reload capability

**Usage:**
```python
from wikidata import PropertyConfigManager

manager = PropertyConfigManager()
person_props = manager.get_properties_for_type('person')
print(f"Person has {len(person_props)} properties")
```

### ✅ WikidataClient
HTTP client for fetching entity data from Wikidata API.

**Features:**
- Automatic retry with exponential backoff
- Rate limiting (1 req/sec default)
- Batch fetching (up to 50 entities)
- Session management
- Comprehensive error handling

**Usage:**
```python
from wikidata import WikidataClient

with WikidataClient() as client:
    data = client.fetch_entity_data('Q1001')  # Mahatma Gandhi
    if data:
        print("Successfully fetched entity data")
```

### ✅ EntityReferenceCache
Thread-safe cache for entity references with disk persistence.

**Features:**
- In-memory caching with pickle persistence
- Thread-safe operations
- Hit rate tracking
- Auto-save mechanism
- Backup and recovery

**Usage:**
```python
from wikidata import EntityReferenceCache

cache = EntityReferenceCache(cache_file="pipeline_state/entity_cache.pkl")

# Cache an entity
cache.put('Q1001', {
    'qid': 'Q1001',
    'name': 'Mahatma Gandhi',
    'type': 'human'
})

# Retrieve from cache
entity = cache.get('Q1001')

# Get statistics
stats = cache.get_statistics()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

### ⏳ WikidataParser (Placeholder)
Will parse Wikidata JSON responses to structured format.

**Status:** To be implemented in Phase 2, Step 4

### ⏳ WikidataEnricher (Placeholder)
Will orchestrate the complete enrichment process.

**Status:** To be implemented in Phase 3, Step 7

## Configuration Files

Located in `config/properties/`:

- `person.yaml` - Human entities (10 properties)
- `event.yaml` - Event entities (6 properties)
- `location.yaml` - Location entities (6 properties)
- `dynasty.yaml` - Dynasty entities (5 properties)
- `political_entity.yaml` - Political entities (7 properties)
- `other.yaml` - Miscellaneous entities (4 properties)

### Adding New Properties

Edit the appropriate YAML file:

```yaml
properties:
  - property_id: P123
    label: property_name
    value_type: time  # or wikibase-item, quantity, coordinate, string
    priority: high    # or medium, low
    multi_value: true # optional, for array properties
    fetch_depth: 1    # optional, for entity references
```

Then reload the configuration:

```python
manager = PropertyConfigManager()
manager.reload_config('person')
```

## Testing

Run the verification script:

```bash
python3 test_phase1_components.py
```

Expected output:
```
🎉 Phase 1 verification SUCCESSFUL! All components working.
Total: 5/5 tests passed
```

## Dependencies

- `pyyaml>=6.0` - YAML parsing
- `requests>=2.31.0` - HTTP client
- Python 3.7+

## Next Steps

**Phase 2: Data Processing Layer**
- Step 4: Implement WikidataParser
- Step 5: Design enhanced data structure
- Step 6: Build entity type mapping system

See `docs/wikidata-integration-implementation-plan.md` for full roadmap.

## Documentation

- [Implementation Plan](../../docs/wikidata-integration-implementation-plan.md)
- [Phase 1 Completion Summary](../../docs/PHASE1_COMPLETION_SUMMARY.md)

## License

Part of the Wikipedia Extraction Pipeline project.
