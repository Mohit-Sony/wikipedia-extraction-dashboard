# Project Brief: Wikipedia Extraction Dashboard with Wikidata Integration

---

## Executive Summary

The Wikipedia Extraction Dashboard is a full-stack application designed to extract, analyze, and visualize structured data from Wikipedia articles focused on Indian History. The system performs depth-based traversal of Wikipedia pages, extracts entity information (people, places, events, dynasties, political entities), and presents them through an interactive web dashboard with real-time monitoring capabilities.

**Primary Problem:** Researchers and historians need a systematic way to extract and analyze structured historical data from Wikipedia, but manual extraction is time-consuming and lacks the ability to capture linked relationships and structured metadata from Wikidata.

**Target Market:** Academic researchers, historians, students, and data analysts working with Indian History content who require organized, queryable historical data with relationship mapping.

**Key Value Proposition:** Automated extraction pipeline with real-time monitoring dashboard that combines Wikipedia narrative content with Wikidata's structured linked data, enabling comprehensive historical research with relationship tracking and knowledge graph capabilities.

---

## Problem Statement

**Current State:**
Researchers studying Indian History need to manually extract information from hundreds of interconnected Wikipedia articles. This process is:
- Extremely time-consuming and error-prone
- Lacks systematic tracking of entity relationships (dynasties, rulers, battles, locations)
- Cannot easily capture structured metadata (birth/death dates, family relationships, geographic hierarchies)
- Provides no visibility into extraction progress or data quality

**Impact:**
- Research projects that should take weeks take months
- Inconsistent data quality due to manual extraction errors
- Lost insights from untracked entity relationships
- No structured data for advanced analysis or visualization

**Why Existing Solutions Fall Short:**
- Generic web scrapers don't understand Wikipedia's structure or entity types
- Manual copy-paste loses relationship context
- Existing tools don't integrate Wikidata's rich structured metadata
- No solutions provide real-time monitoring for long-running extractions

**Urgency:** With the current manual approach, comprehensive analysis of Indian History entities is practically infeasible. Automating this process unlocks research capabilities that are currently impossible.

---

## Proposed Solution

**Core Concept:**
A two-tier extraction system that:
1. **Wikipedia Extraction Layer**: Depth-based traversal of Wikipedia pages extracting narrative content, infobox data, and entity classifications
2. **Wikidata Enhancement Layer**: Enriches extracted entities with structured linked data from Wikidata's EntityData API (family relationships, dates, geographic hierarchies, political positions)

**Key Differentiators:**
- **Enhancement Architecture**: Wikidata integration augments rather than replaces Wikipedia data - both sources coexist independently
- **Entity-Type Intelligence**: Custom property configurations for each entity type (Person, Event, Location, Dynasty, Political Entity)
- **Real-Time Monitoring**: WebSocket-based dashboard showing extraction progress, statistics, and live updates
- **Relationship-Ready Design**: Property-centric data structure designed for future knowledge graph and relationship queries
- **Performance Optimization**: Multi-level caching (property mappings, entity references) with configurable depth control

**Why This Succeeds:**
- Clean separation of concerns prevents architectural complexity
- Modular configuration allows easy extension to new entity types
- Graceful degradation ensures Wikipedia data is preserved even if Wikidata fails
- Future-ready design supports advanced queries without re-extraction

**High-Level Vision:**
Transform historical research from manual, isolated article reading into systematic, relationship-aware data exploration with interactive visualization and knowledge graph capabilities.

---

## Target Users

### Primary User Segment: Academic Researchers & Historians

**Profile:**
- Researchers studying Indian History (dynasties, battles, political movements, historical figures)
- Graduate students working on thesis research
- Professional historians writing books or papers
- Age: 25-65, comfortable with technology but not necessarily developers

**Current Behaviors:**
- Manually reading Wikipedia articles and taking notes
- Creating spreadsheets or documents to track relationships
- Cross-referencing multiple sources manually
- Spending 60-70% of research time on data collection vs. analysis

**Specific Needs:**
- Systematic extraction of entities across interconnected topics
- Tracking family relationships in royal dynasties
- Understanding geographic and political hierarchies
- Monitoring extraction progress for large-scale projects (100+ pages)
- Exportable data for further analysis

**Goals:**
- Reduce data collection time from months to days
- Ensure comprehensive coverage of related entities
- Access structured metadata for quantitative analysis
- Build relationship maps and timelines

### Secondary User Segment: Data Analysts & Digital Humanities Professionals

**Profile:**
- Data scientists working with historical datasets
- Digital humanities professionals building knowledge bases
- Developers creating history education applications
- Technical background, comfortable with APIs and data formats

**Current Behaviors:**
- Using Wikipedia/Wikidata APIs directly with custom scripts
- Building one-off extraction tools for specific projects
- Struggling with API rate limits and data consistency
- Manually cleaning and structuring extracted data

**Specific Needs:**
- Clean, structured JSON output ready for analysis
- Relationship data for network analysis and visualization
- Configurable entity types and properties
- API access to extracted data

**Goals:**
- Reusable extraction pipeline instead of custom scripts
- High-quality structured data without manual cleaning
- Foundation for knowledge graph applications
- Integration with existing data analysis workflows

---

## Goals & Success Metrics

### Business Objectives
- **Launch MVP within 8-10 weeks** with Wikidata integration operational for Person entity type
- **Extract and structure 500+ historical entities** in pilot phase demonstrating system capability
- **Enable relationship-based queries** showing family trees and dynasty succession chains
- **Achieve 95%+ extraction success rate** with graceful handling of Wikipedia/Wikidata API failures

### User Success Metrics
- **Reduce research data collection time by 80%** (from ~100 hours to ~20 hours for typical project)
- **Users can monitor extraction progress in real-time** via dashboard with <5 second update latency
- **100% of extracted entities include Wikidata enrichment** when QID is available
- **Users can export structured data** in JSON/Excel formats within 2 clicks

### Key Performance Indicators (KPIs)
- **Extraction Throughput**: 10-15 pages per minute with Wikidata enrichment
- **API Success Rate**: 95%+ successful Wikipedia fetches, 90%+ successful Wikidata enrichments
- **Data Quality**: <5% missing critical fields for entities with available Wikidata
- **System Uptime**: 99%+ availability for extraction service
- **Cache Hit Rate**: 70%+ for entity reference lookups reducing duplicate API calls
- **User Engagement**: Average session duration >20 minutes indicating active use
- **Data Export Usage**: 60%+ of users export data indicating value delivery

---

## MVP Scope

### Core Features (Must Have)

- **Depth-Based Wikipedia Extraction:** Configurable depth traversal starting from seed page, extracting entity information from Wikipedia articles with infobox parsing and link discovery
  - *Rationale: Foundation of the entire system - must work reliably before adding enhancements*

- **Wikidata Integration for Person Entities:** Extract structured linked data (birth/death dates, birthplace, father, mother, spouse, children, positions held) from Wikidata EntityData API
  - *Rationale: Person is the most common entity type in historical research and demonstrates full integration capabilities*

- **Real-Time Monitoring Dashboard:** WebSocket-connected React dashboard showing extraction status, progress statistics, entity counts, current processing status, approve/reject workflow
  - *Rationale: Essential for user confidence during long-running extractions and demonstrates professional UX*

- **Entity Reference Caching:** Dictionary-based cache for entity lookups (QID → name/description/type) to prevent duplicate API calls
  - *Rationale: Critical for performance - prevents exponential API calls for cross-referenced entities*

- **Property-Centric Data Structure:** Store Wikidata properties with label, value, and value_type metadata supporting time, string, wikibase-item, array, quantity, coordinate types
  - *Rationale: Enables future relationship queries and proper parsing of different data types*

- **Graceful Error Handling:** Retry logic (3 attempts) for API failures, preserve Wikipedia data even if Wikidata fails, flag indicating enrichment success/failure
  - *Rationale: Reliability is critical - partial success is better than total failure*

- **Data Export Functionality:** Export extracted entities and relationships to JSON and Excel formats with relationship preservation
  - *Rationale: Primary user value delivery - researchers need portable data for analysis*

### Out of Scope for MVP
- Event, Location, Dynasty, Political Entity Wikidata integration (Person only for MVP)
- Knowledge graph visualization (relationship data collected but not visualized yet)
- Advanced relationship queries (dynasty succession chains, battle networks)
- Batch processing optimization
- User authentication and multi-user support
- Historical change tracking (re-extraction detection)
- Custom property configuration UI (use config files only)
- API endpoints for programmatic access

### MVP Success Criteria
MVP is successful when:
1. User can start extraction from a seed Wikipedia page with configurable depth
2. System extracts Person entities and enriches with Wikidata including family relationships and key dates
3. Dashboard shows real-time progress with entity counts and current status
4. User can approve/reject extracted entities via dashboard
5. User can export structured data (JSON/Excel) with all Wikidata enrichments preserved
6. System handles API failures gracefully maintaining 90%+ success rate
7. Entity reference cache demonstrates >50% cache hit rate reducing API load

---

## Post-MVP Vision

### Phase 2 Features
- **Multi-Entity Wikidata Integration:** Extend Wikidata enrichment to Event, Location, Dynasty, and Political Entity types with entity-specific property configurations
- **Knowledge Graph Visualization:** Interactive network graph showing entity relationships (family trees, dynasty succession, battle participants) using Cytoscape or similar
- **Advanced Relationship Queries:** Query interface for dynasty succession chains, geographic hierarchies, battle allegiances, political position timelines
- **Batch Processing Optimization:** Option to extract all Wikipedia data first, then batch-enrich with Wikidata reducing total processing time
- **Enhanced Analytics:** Statistics dashboard showing entity type distributions, relationship densities, timeline visualizations, geographic distributions

### Long-term Vision (1-2 years)
- **Multi-Domain Support:** Extend beyond Indian History to other historical domains (European History, Ancient Civilizations, etc.) with domain-specific entity types
- **Collaborative Research Platform:** Multi-user support with project management, shared extractions, annotation capabilities, comment threads
- **AI-Powered Insights:** NLP analysis of Wikipedia content for entity disambiguation, relationship extraction beyond Wikidata, timeline generation from narrative text
- **Quality Validation Tools:** Cross-reference Wikipedia and Wikidata for inconsistencies, suggest missing relationships, identify data gaps
- **Public Knowledge Base:** Searchable repository of extracted historical entities available to research community
- **Integration Ecosystem:** APIs for third-party tools, plugins for research platforms (Zotero, Notion), export to graph databases (Neo4j)

### Expansion Opportunities
- **Educational Applications:** Interactive timeline builders for students, quiz generation from structured data, visual learning tools
- **Publishing Tools:** Automated bibliography generation, fact-checking for historical writing, citation network visualization
- **Museum/Archive Integration:** Connect extracted entities to digitized primary sources, museum collections, archival materials
- **Tourism Applications:** Historical location mapping, heritage site connections, historical figure geographic footprints

---

## Technical Considerations

### Platform Requirements
- **Target Platforms:** Web application (desktop and tablet-optimized, mobile responsive not priority for MVP)
- **Browser Support:** Modern browsers (Chrome, Firefox, Safari, Edge) - last 2 versions, no IE support
- **Performance Requirements:**
  - Dashboard real-time updates <5 second latency
  - Page load time <2 seconds
  - Handle extractions of 100+ entities without UI degradation
  - Support concurrent extractions (at least 3 simultaneous processes)

### Technology Preferences

**Frontend:**
- **Framework:** React 18.2+ with TypeScript
- **State Management:** Redux Toolkit (already implemented)
- **UI Library:** Ant Design 5.10+ (existing choice)
- **Visualization:** Recharts for analytics, Cytoscape for future knowledge graphs (already in dependencies)
- **Build Tool:** Vite (existing)
- **Real-Time:** WebSocket connection for extraction status updates

**Backend:**
- **Framework:** Python (likely Flask or FastAPI based on project structure)
- **API Integration:**
  - Wikipedia API for page content
  - Wikidata EntityData API (https://www.wikidata.org/wiki/Special:EntityData/{QID}.json)
- **Data Processing:** Python dictionaries/dataclasses for entity models
- **Caching:** In-memory dictionaries (Redis consideration for future)
- **Async Processing:** Background task queue for extractions

**Database:**
- **Primary Storage:** JSON files for extracted entities (current approach)
- **Metadata Storage:** SQLite or PostgreSQL for extraction jobs, status tracking, user approvals
- **Future Consideration:** Graph database (Neo4j) for relationship queries in post-MVP

**Hosting/Infrastructure:**
- **Development:** Local development environment
- **MVP Deployment:** Single-server deployment (VPS or local)
- **Future Cloud:** Consider cloud hosting (AWS/GCP/Azure) for scalability

### Architecture Considerations

**Repository Structure:**
- **Monorepo Approach:** Separate frontend/ and backend/ directories (current structure maintained)
- **Configuration Management:** YAML files in backend/config/properties/ for entity type property mappings
- **Shared Types:** TypeScript interfaces for frontend, Python dataclasses for backend with consistent naming

**Service Architecture:**
- **Extraction Service:** Core Wikipedia/Wikidata extraction engine with depth-based traversal
- **WebSocket Service:** Real-time communication layer for status updates (already implemented based on files)
- **File Service:** JSON file management, Excel export generation (already exists)
- **Sync Service:** Handles database synchronization and job tracking (already exists)

**Integration Requirements:**
- **Wikipedia API:** RESTful API calls with retry logic and rate limiting respect
- **Wikidata EntityData API:** JSON endpoint fetching with property filtering
- **No Authentication Required:** Both APIs are public (rate limits apply)

**Security/Compliance:**
- **Input Validation:** Sanitize Wikipedia page titles to prevent injection
- **Rate Limiting:** Respect Wikipedia/Wikidata API rate limits (conservative approach: 1 request per 100ms)
- **Error Logging:** Comprehensive logging without exposing sensitive paths
- **Data Privacy:** No personal user data collected beyond extraction preferences
- **License Compliance:** Wikipedia content CC BY-SA 3.0, Wikidata CC0 - proper attribution in exports

---

## Constraints & Assumptions

### Constraints

**Budget:** Personal/academic project - no budget for cloud services in MVP (local/self-hosted only)

**Timeline:** 8-10 weeks to MVP with Wikidata integration for Person entities operational

**Resources:**
- Solo developer (Mohit Soni)
- Part-time availability (~15-20 hours/week estimated)
- No dedicated QA or design resources
- Leverage existing brainstorming analysis and architectural decisions

**Technical:**
- Must work with existing codebase structure (React frontend, Python backend)
- Cannot modify existing Wikipedia extraction logic extensively (enhancement layer only)
- API rate limits (Wikipedia/Wikidata) - must implement conservative rate limiting
- Local storage constraints - JSON file approach for MVP, database migration later
- Single-threaded extraction for MVP (parallel processing post-MVP)

### Key Assumptions

- Wikipedia articles on Indian History have sufficient Wikidata coverage (QIDs available)
- Wikidata property mappings for Person entities are stable (P22, P25, P569, P570, etc.)
- Users have technical comfort to run local Python/Node.js applications
- Target users prioritize data quality over extraction speed
- Existing extraction pipeline reliably identifies entity types (human, place, event, etc.)
- Browser WebSocket support is available (no fallback needed)
- JSON file storage is adequate for MVP scale (hundreds of entities, not thousands)
- Users will manually configure extraction depth and seed pages (no automated discovery)
- Property configuration via YAML files is acceptable for MVP (no UI needed)

---

## Risks & Open Questions

### Key Risks

- **API Availability Risk:** Wikipedia or Wikidata API downtime or rate limit changes could block extraction functionality
  - *Impact: HIGH - Core functionality depends on external APIs*
  - *Mitigation: Implement robust retry logic, cache aggressively, monitor API status, consider backup data sources*

- **Wikidata Coverage Gaps:** Historical Indian entities may have incomplete or missing Wikidata entries
  - *Impact: MEDIUM - Reduces value of Wikidata integration*
  - *Mitigation: Graceful degradation (keep Wikipedia data), flag missing enrichments, build manual property addition workflow post-MVP*

- **Performance at Scale:** Extraction of 500+ entities with full Wikidata enrichment may be slower than expected
  - *Impact: MEDIUM - User experience degradation*
  - *Mitigation: Implement entity reference caching early, monitor performance metrics, optimize batch processing if needed*

- **Entity Type Classification Accuracy:** Existing pipeline may misclassify entities affecting Wikidata property mapping
  - *Impact: MEDIUM - Wrong properties extracted for entity type*
  - *Mitigation: Validate entity types against Wikidata P31 (instance of), add manual correction workflow*

- **Data Structure Evolution:** Property-centric structure may not support all future relationship query patterns
  - *Impact: LOW-MEDIUM - May require data migration later*
  - *Mitigation: Design structure review with relationship query use cases, validate with sample queries*

### Open Questions

- **How do we handle entities with missing Wikidata QIDs?**
  - Option A: Skip Wikidata enrichment, flag for manual addition
  - Option B: Attempt fuzzy matching by name/description
  - Option C: Provide UI for manual QID entry

- **What is the optimal caching strategy balance?**
  - How long should property mapping cache persist? (session, permanent, TTL-based)
  - Should entity reference cache have size limits to prevent memory issues?
  - When should cache invalidation occur?

- **How should we handle Wikidata property updates over time?**
  - When new properties are added to config, should we re-process old entities?
  - Flag entities for re-extraction vs. automatic background updates?
  - Version tracking for property configurations?

- **What is the user workflow for extraction monitoring?**
  - Should users be able to pause/resume extractions?
  - How to handle concurrent extractions from same user?
  - Should there be automatic save/checkpoint for long extractions?

- **How deep should linked entity data go?**
  - Current decision: 1 level deep (father → {QID, name, description, type})
  - Should "father" entity also include HIS birth/death dates? Or just reference?
  - Where is the line between useful and data explosion?

- **What happens when Wikipedia and Wikidata conflict?**
  - Current approach: Keep both independent
  - Should we flag conflicts for user review?
  - Provide conflict resolution UI or leave to user's analysis?

### Areas Needing Further Research

- **Wikidata Property ID Stability:** Verify that property IDs (P22, P569, etc.) are stable and won't change
- **API Rate Limiting Details:** Exact rate limits for Wikipedia/Wikidata APIs and best practices
- **Entity Type Mapping:** Complete mapping between Wikipedia entity classifications and Wikidata P31 instance types
- **Relationship Query Patterns:** Research graph database query patterns for dynasty succession, battle networks to validate data structure
- **Export Format Requirements:** Survey target users for preferred export formats (JSON, CSV, Excel, RDF, others?)
- **Knowledge Graph Visualization Libraries:** Evaluate Cytoscape vs. alternatives (vis.js, d3-force) for future Phase 2
- **Performance Benchmarking:** Test extraction throughput with real Wikipedia/Wikidata API calls to establish realistic SLAs

---

## Appendices

### A. Research Summary

**Brainstorming Session (2025-12-20):**
Comprehensive brainstorming session using First Principles Thinking, Morphological Analysis, SCAMPER, and Question Storming techniques. Key outputs:
- Enhancement layer architecture decision (non-conflicting Wikidata integration)
- Property-centric data structure with value_type metadata
- Entity reference caching strategy
- Modular configuration per entity type (Person, Event, Location, Dynasty, Political Entity)
- 25+ architectural decisions documented

**Technical Analysis:**
- Wikidata EntityData API exploration: https://www.wikidata.org/wiki/Special:EntityData/{QID}.json
- Property ID research: P569 (birth date), P22 (father), P25 (mother), P26 (spouse), P40 (children), etc.
- Value type classifications: time, string, wikibase-item, array, quantity, coordinate
- Existing codebase review: React/TypeScript frontend with Redux, Python backend with WebSocket support, JSON file storage

### B. Stakeholder Input

**User (Mohit Soni) Preferences:**
- Pragmatic, minimal-complexity approach
- Clean separation of concerns (no Wikipedia/Wikidata conflict resolution)
- Performance-oriented with caching and optimization
- Future-ready design without over-engineering
- Modular, extensible architecture

**Technical Context:**
- Existing robust extraction pipeline with depth-based traversal
- Processing Indian History entities (dynasties, rulers, battles, places)
- Data saved as JSON files with Excel summaries
- Current entity types: human, place, event, organization, concept
- Frontend: React, Redux, Ant Design, WebSocket integration
- Backend: Python with file service, sync service, WebSocket support

### C. References

- **Wikidata EntityData API:** https://www.wikidata.org/wiki/Special:EntityData/
- **Wikipedia API Documentation:** https://www.mediawiki.org/wiki/API:Main_page
- **Brainstorming Session Results:** docs/brainstorming-session-results.md
- **Frontend Package Configuration:** frontend/package.json
- **Backend Service Architecture:** backend/services/, backend/api/
- **BMAD Core Configuration:** .bmad-core/core-config.yaml

---

## Next Steps

### Immediate Actions

1. **Review and Validate Project Brief** - User reviews this brief for accuracy, provides feedback, approves or requests modifications
2. **Prioritize Open Questions** - User and analyst collaboratively resolve critical open questions (QID handling, caching strategy, conflict handling)
3. **Create Property Configuration Files** - Define YAML configurations for Person entity type with Wikidata property mappings (P569, P22, P25, P26, P40, P39, P106)
4. **Design Wikidata API Client Module** - Specify interface for EntityData fetching with retry logic, error handling, rate limiting
5. **Validate Data Structure** - Create sample JSON outputs demonstrating property-centric structure with all value types
6. **Define Integration Points** - Identify exact code locations in existing extraction pipeline for Wikidata enhancement layer
7. **Establish Performance Benchmarks** - Set measurable targets for extraction throughput, cache hit rates, API success rates

### PM Handoff

This Project Brief provides the full context for **Wikipedia Extraction Dashboard with Wikidata Integration**.

**Next Phase:** Product Requirements Document (PRD) generation. The PM should:
- Review this brief thoroughly and validate all assumptions
- Resolve open questions requiring user input
- Work with user to create detailed PRD section by section
- Define user stories and acceptance criteria for each MVP feature
- Establish technical specifications for Wikidata integration architecture
- Create detailed data models for property-centric structure
- Define API contracts between frontend and backend for Wikidata features

Please start in **PRD Generation Mode**, asking for any necessary clarifications or suggesting improvements to transition from strategic brief to detailed implementation specification.

---

*Project Brief v1.0 - Generated 2025-12-20*
*Powered by BMAD™ Method - Business Analyst Mary*
