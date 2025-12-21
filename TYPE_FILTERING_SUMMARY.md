# Type-Based Filtering System - Implementation Summary

## Overview
This implementation adds a type-based filtering system for managing entity transfers from the review queue to the active queue. Only entities matching approved types (person, location, event, dynasty, political_entity, timeline) will be transferred.

## Components Implemented

### 1. Database Model (`backend/database/models.py`)
- **TypeMapping table**: Stores mappings from Wikidata/Wikipedia types to standardized types
  - `wikidata_type`: Original type from external source
  - `mapped_type`: Standardized type (person, location, event, etc.)
  - `is_approved`: Whether this mapping is approved
  - `source`: Origin of mapping (manual, auto, wikidata)

### 2. Backend Services

#### `backend/services/type_filter_service.py`
- `TypeFilterService`: Core service for type filtering logic
  - `get_type_mapping()`: Get mapped type for a wikidata type
  - `is_approved_type()`: Check if entity type is approved
  - `filter_entities_by_approved_types()`: Filter QIDs by approved types
  - `get_unmapped_types_in_review_queue()`: Get unmapped types needing resolution
  - `create_type_mapping()`: Create new type mapping
  - `get_all_type_mappings()`: Retrieve all mappings
  - `delete_type_mapping()`: Remove a mapping

### 3. API Endpoints (`backend/api/type_mappings.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/type-mappings` | GET | Get all type mappings |
| `/api/v1/type-mappings` | POST | Create new type mapping |
| `/api/v1/type-mappings/{id}` | PUT | Update type mapping |
| `/api/v1/type-mappings/{id}` | DELETE | Delete type mapping |
| `/api/v1/type-mappings/filter` | POST | Filter entities by approved types |
| `/api/v1/type-mappings/unmapped` | GET | Get unmapped types in review queue |
| `/api/v1/type-mappings/approved-types` | GET | Get list of approved types |

### 4. Enhanced Bulk Approve Endpoint

Updated `backend/api/queues.py` - `/queues/review/bulk-approve`:
- Added `filter_by_type` parameter to enable type filtering
- When enabled, only entities with approved types are transferred
- Rejected entities are logged with error "Type not approved for extraction"

**Request Schema:**
```json
{
  "operation": "approve",
  "qids": ["Q123", "Q456", "Q789"],
  "filter_by_type": true,
  "priority": 2
}
```

**Response:**
```json
{
  "success_count": 5,
  "error_count": 0,
  "skipped_count": 2,
  "errors": [
    {"qid": "Q999", "error": "Type not approved for extraction"}
  ]
}
```

### 5. Frontend Dashboard (`frontend/src/pages/TypeMappings.tsx`)

**Features:**
- View all existing type mappings
- Create new type mappings
- Delete mappings
- View unmapped types in review queue with counts
- Quick-map buttons to map unmapped types
- Visual type badges for easy identification

**UI Sections:**
1. **Unmapped Types Section**: Shows types without mappings
   - Entity count per type
   - Example entities
   - Quick-map buttons for each approved type

2. **Existing Mappings Table**: Shows all configured mappings
   - Wikidata type → Standard type
   - Approval status
   - Source (manual/auto)
   - Delete action

3. **Type Legend**: Shows all approved standard types

## Usage Examples

### 1. Create Type Mapping
```bash
curl -X POST http://localhost:8002/api/v1/type-mappings \
  -H "Content-Type: application/json" \
  -d '{
    "wikidata_type": "mega city",
    "mapped_type": "location",
    "is_approved": true,
    "source": "manual",
    "notes": "Large urban areas"
  }'
```

### 2. Bulk Approve with Type Filtering
```bash
curl -X POST http://localhost:8002/api/v1/queues/review/bulk-approve \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "approve",
    "qids": ["Q1001", "Q1002", "Q1003"],
    "filter_by_type": true,
    "priority": 2
  }'
```

### 3. Get Unmapped Types
```bash
curl http://localhost:8002/api/v1/type-mappings/unmapped
```

Response:
```json
[
  {
    "type": "military_commander",
    "count": 15,
    "example_qids": [
      {"qid": "Q123", "title": "Akbar"},
      {"qid": "Q456", "title": "Shivaji"}
    ]
  }
]
```

## Database Migration

To apply the new TypeMapping table, run:

```bash
# Using alembic (if configured)
alembic revision --autogenerate -m "Add TypeMapping table"
alembic upgrade head

# Or manually in Python:
from database.database import init_database
init_database()
```

## Approved Standard Types

The system recognizes these 6 standard types:
1. **person**: Historical figures, rulers, scholars
2. **location**: Cities, regions, monuments, geographical features
3. **event**: Battles, wars, treaties, celebrations
4. **dynasty**: Royal houses, ruling families
5. **political_entity**: Kingdoms, empires, sultanates, republics
6. **timeline**: Historical periods (reserved for future use)

## Integration Points

### For Frontend Developers:
1. Add TypeMappings route to your router
2. Import TypeMappings page component
3. Add link in navigation menu
4. Update ReviewQueue component to include type filter option

### For Backend Developers:
1. Register `type_mappings` router in `main.py` (already done)
2. Run database migration to add TypeMapping table
3. Optionally: Seed initial mappings using `type_mapper.py` constants

## Pre-seeded Mappings

The system includes pre-built mappings in `Python_Helper/wikidata/type_mapper.py`:
- 50+ Wikipedia types mapped
- 40+ Wikidata P31 instance types mapped

These can be bulk-imported to the TypeMapping table if needed.

## Next Steps

1. **Add Migration Script**: Create script to import default mappings
2. **UI Enhancement**: Add type filter checkbox in ReviewQueue bulk actions
3. **Auto-mapping**: Create background job to auto-map new types based on patterns
4. **Statistics**: Add dashboard widget showing type distribution in review queue
5. **Validation**: Add type validation during entity creation

## Testing

Test the complete flow:

1. Add some entities to review queue with various types
2. Create type mappings for some types (map to approved types)
3. Use bulk approve with `filter_by_type: true`
4. Verify only entities with approved types move to active queue
5. Check unmapped types endpoint to see remaining types
6. Create mappings for unmapped types
7. Repeat bulk approve

## API Documentation

Full API docs available at: http://localhost:8002/docs
Look for the "type-mappings" tag in the API explorer.
