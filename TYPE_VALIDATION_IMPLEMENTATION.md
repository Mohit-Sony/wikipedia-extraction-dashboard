# Type Validation for ACTIVE Queue - Implementation Summary

## Overview
Implemented a type mapping validation system that ensures only entities with approved/mapped types can be moved to the ACTIVE queue. Unmapped types must be categorized before extraction.

## Features Implemented

### 1. Type Validation on Queue Movement ✅
**Location**: `backend/api/queues.py:144-156`

- Added validation check when moving entities to ACTIVE queue
- Only entities with mapped types can go to ACTIVE
- Unmapped types are rejected with clear error message
- Other queues (REVIEW, FAILED, REJECTED) accept all types for triage

### 2. Bulk Approve Mapped Entities ✅
**Endpoint**: `POST /api/v1/queues/{queue_type}/bulk-approve-mapped`

**Functionality**:
- Filters all entities in specified queue by type mapping status
- Moves only mapped entities to ACTIVE queue
- Skips unmapped entities with detailed reporting
- Returns comprehensive results:
  - `success_count`: Entities moved to ACTIVE
  - `skipped_count`: Unmapped entities skipped
  - `error_count`: Errors during processing
  - `errors`: List with QID and reason for each skip/error

**Example Response**:
```json
{
  "success_count": 25,
  "skipped_count": 10,
  "error_count": 0,
  "errors": [
    {
      "qid": "Q123456",
      "error": "Type 'princely state' not mapped to approved category"
    }
  ]
}
```

### 3. Queue Type Statistics ✅
**Endpoint**: `GET /api/v1/queues/{queue_type}/type-stats`

**Returns**:
```json
{
  "queue_type": "failed",
  "total": 35,
  "mapped_count": 25,
  "unmapped_count": 10,
  "mapped_types": {
    "person": 15,
    "location": 8,
    "event": 2
  },
  "unmapped_types": ["princely state", "tomb", "business school"]
}
```

### 4. Frontend UI Enhancements ✅

#### A. "Send Mapped to Active" Button
**Location**: Queue Manager page header (http://localhost:3000/queues)

**Behavior**:
- Appears when viewing FAILED, REVIEW, or REJECTED queues
- Shows count of mapped entities: "Send Mapped to Active (25)"
- Green button with CheckCircle icon
- Only visible if there are mapped entities

**Confirmation Modal Shows**:
- Total entities to be moved
- Breakdown by mapped type category
- List of unmapped types that will be skipped
- Link to Type Mappings page

#### B. Type Mapping Indicators
**Location**: Queue card title

**Display**:
- Green tag: "X Mapped" (entities with approved types)
- Orange tag: "Y Unmapped" (entities needing type mapping)
- Shows in real-time as you select different queues

#### C. Enhanced Error Messages
When trying to manually move unmapped entity to ACTIVE:
```
Type 'princely state' is not mapped to an approved category.
Current mapping: 'other'.
Please add a type mapping before moving to ACTIVE queue.
```

## Type Mapping System

### Approved Categories
Entities must be mapped to one of these categories:
- `person`
- `location`
- `event`
- `dynasty`
- `political_entity`
- `timeline`
- `other`

### Type Mapping Flow
1. Entity extracted with Wikidata type (e.g., "human", "war", "princely state")
2. Type checked against `type_mappings` table
3. If mapped → Can go to ACTIVE queue
4. If unmapped → Must stay in REVIEW/FAILED until mapped

### Creating Type Mappings
Navigate to: http://localhost:3000/type-mappings

Or use API:
```bash
POST /api/v1/type-mappings
{
  "wikidata_type": "princely state",
  "mapped_type": "political_entity",
  "is_approved": true
}
```

## Usage Instructions

### For Failed Entities (like the 10 we fixed)

1. **Go to Queue Manager**: http://localhost:3000/queues
2. **Select FAILED queue**
3. **Check type stats in header**: e.g., "0 Mapped / 10 Unmapped"
4. **Create type mappings** for unmapped types:
   - Go to Type Mappings page
   - Map each type to an approved category
5. **Return to Queue Manager**
6. **Click "Send Mapped to Active (X)"** button
7. **Review confirmation modal**:
   - See which entities will move
   - See which are still unmapped
8. **Click OK** to move mapped entities to ACTIVE

### For Review Queue

Same process - bulk approve only mapped types from REVIEW → ACTIVE

### Manual Movement

If you try to manually move an unmapped entity:
1. Select entity in queue
2. Try to move to ACTIVE
3. **Error shown**: Type not mapped
4. Create type mapping
5. Try again - now allowed

## Database Schema

### TypeMapping Table
```sql
CREATE TABLE type_mappings (
    id INTEGER PRIMARY KEY,
    wikidata_type VARCHAR UNIQUE NOT NULL,  -- e.g., "princely state"
    wikidata_qid VARCHAR,                   -- e.g., "Q1240096"
    mapped_type VARCHAR NOT NULL,           -- e.g., "political_entity"
    is_approved BOOLEAN DEFAULT FALSE,
    confidence FLOAT DEFAULT 1.0,
    source VARCHAR DEFAULT 'manual',        -- manual, auto, wikidata
    created_at TIMESTAMP,
    created_by VARCHAR,
    notes TEXT
);
```

## Files Modified

### Backend
1. **api/queues.py**
   - Added type validation to `add_to_queue()` (lines 144-156)
   - Added `bulk_approve_mapped_to_active()` endpoint (lines 1008-1132)
   - Added `get_queue_type_stats()` endpoint (lines 1135-1192)

2. **services/type_filter_service.py** (already existed)
   - Provides `is_approved_type()` method
   - Provides `filter_entities_by_approved_types()` method
   - Provides `get_type_mapping()` method

### Frontend
1. **store/api.ts**
   - Added `getQueueTypeStats` query (lines 220-230)
   - Added `bulkApproveMappedToActive` mutation (lines 232-243)
   - Exported hooks: `useGetQueueTypeStatsQuery`, `useBulkApproveMappedToActiveMutation`

2. **pages/QueueManager.tsx**
   - Imported new hooks (lines 23-24)
   - Added `handleBulkApproveMapped()` handler (lines 146-231)
   - Added "Send Mapped to Active" button with conditional rendering (lines 373-386)
   - Added type mapping stats to queue card header (lines 423-434)

## Validation Rules

| From Queue | To Queue | Validation                        | Allowed? |
|-----------|----------|-----------------------------------|----------|
| Any       | ACTIVE   | ✅ Type must be mapped            | Conditional |
| Any       | REVIEW   | ❌ No type validation             | Always |
| Any       | FAILED   | ❌ No type validation             | Always |
| Any       | REJECTED | ❌ No type validation             | Always |
| FAILED    | ACTIVE   | ✅ Type must be mapped + dedup OK | Conditional |

## Testing

### Test Case 1: Unmapped Type to ACTIVE
```bash
# Should FAIL
POST /api/v1/queues/entries
{
  "qid": "Q1240096",  # Type: "princely state" (unmapped)
  "queue_type": "active"
}

# Response: 400 Bad Request
# "Type 'princely state' is not mapped to an approved category"
```

### Test Case 2: Bulk Approve Mapped
```bash
# Should move only mapped entities
POST /api/v1/queues/failed/bulk-approve-mapped

# Response:
{
  "success_count": 5,   # Moved to ACTIVE
  "skipped_count": 5,   # Unmapped types
  "error_count": 0
}
```

### Test Case 3: After Creating Mapping
```bash
# 1. Create mapping
POST /api/v1/type-mappings
{
  "wikidata_type": "princely state",
  "mapped_type": "political_entity"
}

# 2. Try again - Should SUCCESS
POST /api/v1/queues/entries
{
  "qid": "Q1240096",
  "queue_type": "active"
}
```

## Benefits

1. **Data Quality**: Only validated, categorized entities enter extraction pipeline
2. **Type Management**: Centralized type mapping system
3. **User Friendly**: Clear error messages guide users to fix issues
4. **Bulk Operations**: Efficiently process large numbers of entities
5. **Transparency**: Always shows what will/won't be moved and why

## Next Steps

1. **Add Type Mappings** for the 10 failed entities:
   - tomb → location
   - princely state → political_entity
   - business school → location (or other)
   - war → event

2. **Bulk approve** them to ACTIVE queue

3. **Start extraction** - now with type-validated entities!
