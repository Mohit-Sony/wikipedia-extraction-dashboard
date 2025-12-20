# Brainstorming Session Results

**Session Date:** 2025-12-20
**Facilitator:** Business Analyst Mary
**Participant:** Mohit Soni
**Status:** In Progress (Paused for Documentation)

---

## Executive Summary

**Topic:** Integrating Wikidata EntityData API into Wikipedia Extraction Pipeline for Enhanced Structured Data

**Session Goals:**
- Focus on integrating Wikidata's EntityData API to extract structured linked data (father, mother, birth/death dates, etc.)
- Enhance existing extraction pipeline without replacing current functionality
- Design optimal, performant solution with caching and modern data structures
- Support multiple entity types: Person, Event, Location, Dynasty, Political Entity

**Techniques Used:**
1. First Principles Thinking (Completed)
2. Morphological Analysis (Completed)
3. SCAMPER Method (Completed)
4. Question Storming (In Progress)

**Total Ideas Generated:** 25+ architectural decisions and implementation patterns

**Key Themes Identified:**
- Enhancement layer approach - no conflict with existing Wikipedia extraction
- Property-centric data structure with value type metadata
- Multi-level caching strategy for optimization
- Modular configuration per entity type
- Future-ready design for relationship queries and knowledge graphs

---

## Technique Sessions

### First Principles Thinking - 15 minutes

**Description:** Breaking down the fundamental requirements and architecture of Wikidata integration

**Key Decisions Made:**

1. **Linked Entity Data Depth**
   - One level deep only (no recursive nesting)
   - For linked entities (father, mother, etc.), extract: QID, Label/Name, Description (4-5 words), Type/Instance
   - Pragmatic approach to avoid data explosion

2. **Property Mapping Strategy**
   - External configuration files (JSON/YAML) per entity type
   - Dictionary-based mapping in code with dynamic extension capability
   - Ability to add new properties during execution when discovered

3. **Integration Philosophy**
   - Not a new system - enhancement to current extraction
   - Add new field `structured_key_data` to existing extraction output
   - No conflict resolution needed between Wikipedia and Wikidata data
   - Both sources maintain independent fields

**Insights Discovered:**
- Wikidata uses property IDs (P569 for date of birth, P22 for father, etc.)
- Need to map human-readable names to Wikidata property IDs
- Integration point: After Wikipedia extraction, add Wikidata as enhancement layer
- Clean separation of concerns prevents complexity

**Notable Connections:**
- Existing pipeline structure supports enhancement pattern well
- Current error handling and retry logic can be extended to Wikidata calls
- Existing entity type classification aligns with Wikidata instance types

---

### Morphological Analysis - 20 minutes

**Description:** Systematically mapping parameters and exploring optimal combinations

**Parameters Analyzed:**

#### Parameter 1: Caching Strategy

**Decision:**
- **Property mapping cache:** Full caching of P569 → date_of_birth mappings
- **Entity reference cache:** Cache QID → {name, description, type, key_data}
- **Purpose:** Avoid duplicate lookups when entities are cross-referenced
- **Implementation:** Use dictionary/map structures for O(1) lookup performance

#### Parameter 2: Error Handling

**Decision:**
- Retry up to 3 times maximum for Wikidata API failures
- Save current Wikipedia data even if Wikidata fails
- Add flag: `structured_key_data_extracted: true/false`
- Log errors for manual review if needed

#### Parameter 3: Data Storage Structure

**Decision:** Property-centric with enhanced metadata

**Structure:**
```json
{
  "structured_key_data": {
    "P569": {
      "label": "date_of_birth",
      "value": "1869-10-02",
      "value_type": "time"
    },
    "P22": {
      "label": "father",
      "value": {
        "qid": "Q123",
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
          "qid": "Q456",
          "name": "Kasturba Gandhi",
          "description": "wife of Mahatma Gandhi",
          "type": "human"
        }
      ],
      "value_type": "array"
    }
  }
}
```

**Value Types Supported:**
- `time` - dates
- `string` - text values
- `wikibase-item` - single entity reference
- `array` - multiple values
- `quantity` - numbers with units
- `coordinate` - geographic coordinates

#### Parameter 4: Configuration File Structure

**Decision:** Separate files per entity type
- `config/properties/person.yaml`
- `config/properties/event.yaml`
- `config/properties/location.yaml`
- `config/properties/dynasty.yaml`
- `config/properties/political_entity.yaml`

**Benefits:** Modularity, easier maintenance, clear separation

**Insights Discovered:**
- Value type metadata enables proper parsing and display
- Array support critical for multi-value properties (spouses, children, positions)
- Property-centric structure preserves Wikidata semantics while being queryable

---

### SCAMPER Method - 20 minutes

**Description:** Creative exploration of enhancement opportunities using Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse

#### S - Substitute

**Decision:** No substitution - keep both Wikipedia and Wikidata data independent
- No replacement of Wikipedia infobox extraction
- Both sources in separate fields
- No conflict resolution logic needed

#### C - Combine

**Decision:** Clean separation - no merging strategy needed
- Wikipedia data: existing fields
- Wikidata data: `structured_key_data` field
- Both coexist independently

#### A - Adapt

**Patterns to Adapt:**
- **Batch API requests:** Group multiple entity lookups where possible
- **Property field selection:** Only fetch configured properties per entity type
- **Performance optimization:** Use modern data structures (dictionaries, maps)
- Standard synchronous flow (no lazy loading complexity)

#### M - Modify/Magnify

**Relationship Tracking:**
- Agree with suggestions to design for future relationship queries
- Dynasty succession chains (ruler → heir → heir)
- Battle participants and allegiances
- Geographic hierarchies (place → district → state → country)
- Family networks across royal houses

**Design consideration:** Structure data to make relationship queries easy later

#### P - Put to Other Uses

**Future Use Cases (extract data now, implement later):**
- Generate knowledge graphs
- Auto-create timelines
- Validate Wikipedia data quality
- Build recommendation systems (similar entities)
- Create structured search/filters in dashboard

**Decision:** Leave traces/hooks for future functionality

#### E - Eliminate

**Technical Decision:** Skip properties that add noise:
- Overly granular external database IDs
- Wikimedia category links (unless needed)
- Low-quality or sparse properties
- Overly complex nested structures beyond one level

#### R - Reverse/Rearrange

**Technical Decision:** Stick with current flow
- Wikipedia page → Extract → Add Wikidata enrichment → Process links
- Consider batch processing option: Extract all Wikipedia → Then batch Wikidata enrichments
- Flow optimization to be decided during implementation

**Insights Discovered:**
- Enhancement layer approach reduces complexity
- Future use cases justify structured data extraction effort
- Relationship data opens possibilities for advanced queries and visualizations

---

## Key Entity Type Requirements

### Person
**Priority Properties:**
- Date of birth (P569)
- Place of birth (P19)
- Date of death (P570)
- Place of death (P20)
- Father (P22)
- Mother (P25)
- Children (P40)
- Spouse (P26)
- Position held (P39) - with tenure/office period
- Occupation (P106)

### Event
**Priority Properties:**
- Start time (P580)
- End time (P582)
- Location (P276)
- Participants (P710)
- Participant roles
- Significant event (P793)
- Casualties (P1120)

### Location
**Priority Properties:**
- Coordinates (P625)
- Instance of (P31) - location type
- Located in (P131) - parent location
- Administrative hierarchy (country → state → district → place)
- Population (P1082)
- Area (P2046)

### Dynasty
**Priority Properties:**
- Start time (P571)
- End time (P576)
- Founder (P112)
- Dissolved/abolished (P576)
- Members (P527)
- Territory (P1001)

### Political Entity
**Priority Properties:**
- Instance of (P31)
- Inception (P571)
- Dissolved (P576)
- Head of state (P35)
- Head of government (P6)
- Territory (P1001)
- Capital (P36)

---

## Implementation Architecture Summary

### Core Components

1. **Wikidata API Client**
   - Fetch EntityData from `https://www.wikidata.org/wiki/Special:EntityData/{QID}.json`
   - Retry logic: 3 attempts with exponential backoff
   - Error handling with graceful degradation

2. **Property Configuration Manager**
   - Load property mappings from YAML files per entity type
   - Dynamic property addition capability
   - Cache property mappings in memory

3. **Entity Reference Cache**
   - Dictionary/map structure for QID lookups
   - Store: {qid, name, description, type} for referenced entities
   - Prevent duplicate API calls for cross-referenced entities

4. **Data Parser & Transformer**
   - Parse Wikidata JSON response
   - Extract configured properties per entity type
   - Transform to property-centric structure with value_type metadata
   - Handle multiple value types: time, string, wikibase-item, array, quantity, coordinate

5. **Integration Layer**
   - Called after Wikipedia extraction
   - Adds `structured_key_data` field to existing entity JSON
   - Sets `structured_key_data_extracted` flag
   - No modification to existing Wikipedia data fields

### Data Flow

```
Wikipedia Page Title
    ↓
Extract Wikipedia Data (existing)
    ↓
Fetch Wikidata EntityData (QID from Wikipedia)
    ↓
Check Entity Reference Cache
    ↓
Load Property Config for Entity Type
    ↓
Parse & Transform Wikidata Response
    ↓
Add structured_key_data field
    ↓
Save Enhanced Entity JSON
```

---

## Questions for Implementation (In Progress)

### Technical Questions Identified

1. **How do we map Wikipedia entity types to Wikidata instance types?**
   - Current pipeline uses: "human", "place", "event"
   - Wikidata uses P31 (instance of) with various QIDs
   - Need mapping strategy

2. **What happens when an entity has multiple values for a property?**
   - ✓ Solved: Use array value_type

3. **How do we handle missing QIDs?**
   - What if Wikipedia page doesn't have Wikidata QID?
   - Skip Wikidata enrichment? Log for review?

4. **What's the format for complex Wikidata values?**
   - Dates with precision (year only vs. exact date)
   - Coordinates with precision levels
   - Quantities with units

5. **Should we store raw Wikidata response for debugging?**
   - Or just the parsed structured_key_data?
   - Storage vs. debuggability tradeoff

6. **How do we handle Wikidata property updates?**
   - When new properties added to config files
   - Re-process old entities? Flag for update?

### Questions Pending User Input

*Session paused before completing Question Storming technique. To be continued.*

---

## Next Steps

### To Complete This Brainstorming Session

1. **Complete Question Storming** - Identify remaining implementation questions and edge cases
2. **Categorize Ideas** - Sort into Immediate Opportunities, Future Innovations, and Insights
3. **Define Action Plan** - Prioritize top 3 implementation steps with timelines
4. **Document Reflection** - Capture what worked well and areas for further exploration

### Immediate Actions Available Now

Based on current progress, the following can be started:

1. **Create property configuration files** for each entity type (person, event, location, dynasty, political_entity)
2. **Design Wikidata API client module** with retry logic and error handling
3. **Implement entity reference cache** structure
4. **Define enhanced data structure** with value_type metadata
5. **Plan integration point** in existing extraction pipeline

---

## Session Notes

**Session Flow:**
- Focused, implementation-oriented discussion
- User provided clear requirements and constraints
- Collaborative decision-making on architecture
- Emphasis on optimization, performance, and future extensibility

**User Preferences:**
- Pragmatic, minimal-complexity approach
- Clean separation of concerns
- Future-ready but not over-engineered
- Performance-oriented with caching

**Technical Context:**
- Existing robust extraction pipeline with depth-based traversal
- Processing Indian History entities (dynasties, rulers, battles, places)
- Data saved as JSON files with Excel summaries
- Current entity types: human, place, event, organization, concept

---

*Session paused at: 2025-12-20*
*To resume: Continue with Question Storming technique, then move to Action Planning*

---

*Session facilitated using the BMAD-METHOD™ brainstorming framework*
