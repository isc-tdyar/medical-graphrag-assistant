# Feature Specification: Enhanced GraphRAG FHIR Extraction

**Feature Branch**: `010-enhanced-graphrag-extraction`
**Created**: 2025-12-18
**Status**: Draft
**Input**: Consolidation of identified improvements to GraphRAG knowledge extraction from FHIR data, including structured resource extraction, PPR-based search, and automated pipeline integration.

## Problem Statement

The current GraphRAG implementation in medical-graphrag-assistant has significant limitations:

1. **Regex-only extraction**: Uses simple pattern matching, missing structured FHIR data
2. **DocumentReference-only**: Only extracts from narrative text, ignoring coded data in Condition, MedicationRequest, Procedure, Observation, AllergyIntolerance
3. **No patient/encounter linking**: RAG.Entities table lacks PatientID/EncounterID columns, preventing patient-scoped searches
4. **Keyword-only search**: `graph_search` uses SQL LIKE queries, no graph traversal or multi-hop reasoning
5. **Manual batch process**: Requires running separate script, not integrated into FHIR ingestion

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Structured FHIR Resource Extraction (Priority: P0)

When FHIR resources are ingested (Condition, MedicationRequest, Procedure, Observation, AllergyIntolerance), entities should be automatically extracted and inserted into RAG.Entities with proper coded terminology (SNOMED-CT, ICD-10, RxNorm).

**Why this priority**: 80%+ of medical data in FHIR is in structured coded resources. Current regex-only extraction misses this entirely.

**Independent Test**: Ingest a FHIR Condition resource with SNOMED code "22298006" (Myocardial infarction). Query `SELECT * FROM RAG.Entities WHERE EntityText LIKE '%myocardial%'`. Expect entity with SNOMED code preserved.

**Acceptance Scenarios**:

1. **Given** a FHIR Condition resource with `code.coding[0].code = "22298006"`, **When** ingested via FHIR endpoint, **Then** RAG.Entities contains entity with EntityText="Myocardial infarction", EntityType="CONDITION", TerminologyCode="SNOMED:22298006"

2. **Given** a FHIR MedicationRequest with RxNorm code "197361" (Furosemide), **When** ingested, **Then** RAG.Entities contains entity with EntityType="MEDICATION", TerminologyCode="RxNorm:197361"

3. **Given** a FHIR Procedure with CPT code, **When** ingested, **Then** RAG.Entities contains entity with EntityType="PROCEDURE", linked to correct patient

---

### User Story 2 - Patient-Scoped Entity Queries (Priority: P0)

Graph queries should support filtering by PatientID to return only entities from a specific patient's records. This enables "find all conditions for patient X" without cross-patient leakage.

**Why this priority**: Medical data privacy requires patient-level access control. Current design cannot scope queries to individual patients.

**Independent Test**: Query `search_knowledge_graph(query="diabetes", patient_id="p10000032")`. Only entities from that patient's FHIR resources should be returned.

**Acceptance Scenarios**:

1. **Given** RAG.Entities has PatientID column populated, **When** searching with patient_id filter, **Then** only that patient's entities are returned

2. **Given** multiple patients with "chest pain" entities, **When** searching "chest pain" without patient filter, **Then** all patients' entities returned with patient attribution

3. **Given** a patient with EncounterID tracking, **When** querying by encounter context, **Then** entities from that encounter are prioritized

---

### User Story 3 - Automated Extraction on FHIR Ingestion (Priority: P1)

When FHIR bundles are posted to the FHIR endpoint, entity extraction should trigger automatically. This eliminates the need for manual batch scripts.

**Why this priority**: Batch processing leads to stale GraphRAG data. Real-time extraction keeps the knowledge graph current.

**Independent Test**: POST a FHIR Bundle with 5 Conditions. Within 30 seconds, verify 5 new entities appear in RAG.Entities.

**Acceptance Scenarios**:

1. **Given** Docker compose brings up IRIS with FHIR endpoint, **When** POST /fhir/r4/Bundle with Conditions, **Then** entities extracted within 30 seconds (async trigger)

2. **Given** extraction configured for specific resource types, **When** posting unsupported type (e.g., Provenance), **Then** no extraction attempted, no errors

3. **Given** extraction service temporarily unavailable, **When** FHIR POST received, **Then** FHIR operation succeeds, extraction queued for retry

---

### User Story 4 - Personalized PageRank Graph Search (Priority: P1)

Replace keyword-based `graph_search` with Personalized PageRank (PPR) that traverses entity relationships for multi-hop reasoning. Enables "find entities related to diabetes" to return connected conditions, medications, procedures.

**Why this priority**: Current search cannot discover related entities through relationships. PPR enables semantic graph exploration.

**Independent Test**: Search for "diabetes" with PPR enabled. Expect related entities like "metformin", "kidney disease", "retinopathy" to appear via relationship traversal.

**Acceptance Scenarios**:

1. **Given** entities with relationships (diabetes TREATED_BY metformin), **When** searching "diabetes" with PPR, **Then** "metformin" appears with relationship-derived score

2. **Given** 3-hop relationship chain (symptom -> condition -> medication), **When** searching for symptom, **Then** medication appears with decayed score

3. **Given** bidirectional relationships, **When** searching medication name, **Then** related conditions discovered via reverse traversal

4. **Given** query returns > 50 entities, **When** using PPR, **Then** response time < 500ms

---

### User Story 5 - Entity Embedding Generation (Priority: P2)

Entity embeddings (EmbeddingVector column) should be populated during extraction using the existing embedding service. Enables vector similarity search on entities.

**Why this priority**: Vector embeddings enable semantic similarity queries beyond exact text matching.

**Independent Test**: After extracting entity "myocardial infarction", verify EmbeddingVector is a 384-dimensional vector (not NULL).

**Acceptance Scenarios**:

1. **Given** entity text "acute myocardial infarction", **When** extracted, **Then** EmbeddingVector populated with 384-dim embedding

2. **Given** embedding service unavailable, **When** entity extracted, **Then** entity saved with NULL embedding, logged for retry

3. **Given** existing entity without embedding, **When** running backfill script, **Then** embedding generated and stored

---

### User Story 6 - UMLS Entity Normalization (Priority: P2)

Entities should be normalized to UMLS Concept Unique Identifiers (CUIs) to enable cross-terminology matching. "Heart attack", "myocardial infarction", and "MI" should all map to the same CUI (C0027051).

**Why this priority**: Without normalization, semantically identical entities are treated as different. UMLS provides a unified concept layer across SNOMED, ICD-10, RxNorm.

**Independent Test**: Extract entities "myocardial infarction" and "heart attack" from different documents. Both should have UMLS_CUI="C0027051" enabling them to be recognized as the same concept.

**Acceptance Scenarios**:

1. **Given** entity text "myocardial infarction", **When** normalized, **Then** UMLS_CUI="C0027051", SemanticType="Disease or Syndrome"

2. **Given** entity text "Tylenol" (brand name), **When** normalized, **Then** maps to same CUI as "acetaminophen" (generic)

3. **Given** abbreviation "MI" in clinical context, **When** extracted and normalized, **Then** correctly disambiguated to myocardial infarction CUI (not "mitral insufficiency")

4. **Given** UMLS API unavailable, **When** entity extracted, **Then** entity saved without CUI, flagged for later normalization batch

---

### User Story 7 - Relationship Extraction with Confidence (Priority: P2)

Entity relationships should capture the relationship type (TREATS, CAUSES, ASSOCIATED_WITH), source context, and confidence score.

**Why this priority**: Rich relationship metadata enables weighted graph traversal and explainable results.

**Independent Test**: After processing "Patient takes metformin for diabetes", verify EntityRelationships has row with RelationshipType="TREATS", Context containing original sentence.

**Acceptance Scenarios**:

1. **Given** Condition and MedicationRequest for same patient, **When** extracted, **Then** relationship created with RelationshipType="TREATED_BY"

2. **Given** DocumentReference mentions "chest pain due to anxiety", **When** LLM-extracted, **Then** relationship created with RelationshipType="CAUSED_BY", Confidence > 0.7

3. **Given** relationship from structured FHIR code linking, **When** created, **Then** Confidence = 1.0 (high confidence for coded data)

---

### User Story 7 - Hybrid Search Combining PPR + Vector + FHIR (Priority: P2)

The `hybrid_search` tool should combine PPR graph scores, vector similarity scores, and FHIR search scores using Reciprocal Rank Fusion (RRF).

**Why this priority**: Single-modality search misses relevant results. RRF fusion provides comprehensive retrieval.

**Independent Test**: Search "diabetes medications" with hybrid enabled. Expect results that appear high in any modality (FHIR medication search, vector similar, graph-related) to rank high overall.

**Acceptance Scenarios**:

1. **Given** entity relevant in graph (PPR rank 5) and vector (rank 2), **When** hybrid search, **Then** fused rank higher than either individual

2. **Given** FHIR-only match (no graph relationships), **When** hybrid search, **Then** still appears in results with FHIR-derived score

3. **Given** `graphrag_weight` parameter set to 0.0, **When** hybrid search, **Then** behaves like FHIR-only search

---

### User Story 8 - LLM-Based Extraction for Unstructured Text (Priority: P3)

DocumentReference narrative text should be processed with LLM (Claude via Bedrock) to extract entities and relationships not capturable by regex.

**Why this priority**: Complex clinical narratives contain implicit relationships and nuanced terminology. LLM extraction captures what regex misses.

**Independent Test**: Process radiology report "Findings consistent with pneumonia, possibly viral. Recommend chest CT." Expect entities: pneumonia (CONDITION), chest CT (PROCEDURE); relationship: pneumonia INVESTIGATED_BY chest CT.

**Acceptance Scenarios**:

1. **Given** clinical note with implicit relationship, **When** LLM-extracted, **Then** relationship captured with context

2. **Given** batch of 100 DocumentReferences, **When** LLM extraction runs, **Then** completes in < 5 minutes (batched API calls)

3. **Given** LLM rate limit reached, **When** extraction fails, **Then** retry with exponential backoff, mark documents for re-processing

---

### Edge Cases

- What happens when FHIR resource has no coded terminology (text-only)?
  - Extract entity text as-is with lower confidence, mark for terminology mapping later

- What happens when PPR traversal exceeds depth limit?
  - Cap at configured max_depth (default: 3), return with truncation indicator

- What happens when embedding service returns different dimensions than expected?
  - Log error, skip embedding for that entity, continue processing

- What happens when FHIR resource update changes condition code?
  - Upsert logic: update existing entity if same ResourceID, increment version

- What happens with very long DocumentReference text (>100KB)?
  - Chunk text into 4KB segments, process each chunk, deduplicate entities

- What happens when patient is deleted from FHIR?
  - Cascade delete entities with that PatientID (configurable retention policy)

## Requirements *(mandatory)*

### Schema Changes

- **FR-001**: Add PatientID column to RAG.Entities (foreign key concept to FHIR Patient)
- **FR-002**: Add EncounterID column to RAG.Entities (optional, for encounter-scoped queries)
- **FR-003**: Add TerminologyCode column to RAG.Entities (format: "SYSTEM:CODE", e.g., "SNOMED:22298006")
- **FR-004**: Add TerminologyDisplay column for human-readable code display name
- **FR-005**: Add SourceResourceType column (e.g., "Condition", "MedicationRequest", "DocumentReference")
- **FR-006**: Add ExtractedAt timestamp for extraction audit trail

### Extraction Pipeline

- **FR-010**: Create `FHIREntityExtractor` class supporting Condition, MedicationRequest, Procedure, Observation, AllergyIntolerance
- **FR-011**: Extractor MUST map SNOMED-CT, ICD-10, RxNorm codes to standard entity format
- **FR-012**: Extractor MUST handle missing coded data gracefully (fall back to text)
- **FR-013**: Extractor MUST populate PatientID from resource subject reference
- **FR-014**: Extractor MUST be idempotent (re-processing same resource updates, not duplicates)

### UMLS Normalization

- **FR-015**: System SHOULD normalize entities to UMLS CUIs using UMLS Metathesaurus lookup
- **FR-016**: UMLS normalization MUST map SNOMED-CT, ICD-10, RxNorm codes to corresponding CUIs
- **FR-017**: System MUST store UMLS_SemanticType (e.g., "Disease or Syndrome", "Pharmacologic Substance")
- **FR-018**: Entity search MUST support querying by UMLS_CUI to find semantically equivalent entities
- **FR-019**: UMLS lookup SHOULD use cached local database or API with retry logic
- **FR-020**: Abbreviation disambiguation (e.g., "MI" -> myocardial infarction vs mitral insufficiency) SHOULD use context

### Graph Search (PPR)

- **FR-021**: Implement Personalized PageRank with configurable damping_factor (default: 0.5)
- **FR-022**: Support bidirectional edge traversal with reverse_edge_weight parameter
- **FR-023**: PPR MUST complete in < 500ms for graphs up to 10,000 nodes
- **FR-024**: PPR MUST support seed entities from initial keyword/vector match
- **FR-025**: Expose PPR parameters via MCP tool: max_iterations, top_k, damping_factor

### Integration

- **FR-030**: Create IRIS trigger or ObjectScript callback on FHIR resource insert/update
- **FR-031**: Trigger MUST be async (not block FHIR transaction)
- **FR-032**: Provide fallback batch script for bulk re-extraction
- **FR-033**: Support `--resource-types` flag to filter extraction scope

### Key Entities (Updated Schema)

```sql
-- Updated RAG.Entities schema
CREATE TABLE RAG.Entities (
  EntityID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  EntityText VARCHAR(500) NOT NULL,
  EntityType VARCHAR(50) NOT NULL,  -- SYMPTOM, CONDITION, MEDICATION, PROCEDURE, BODY_PART, LAB_VALUE
  ResourceID BIGINT NOT NULL,
  PatientID VARCHAR(100),           -- NEW: FHIR Patient reference (e.g., "p10000032")
  EncounterID VARCHAR(100),         -- NEW: FHIR Encounter reference (optional)
  TerminologyCode VARCHAR(100),     -- NEW: "SNOMED:22298006" or "RxNorm:197361"
  TerminologyDisplay VARCHAR(500),  -- NEW: Human-readable code name
  UMLS_CUI VARCHAR(20),             -- NEW: UMLS Concept Unique Identifier (e.g., "C0027051")
  UMLS_SemanticType VARCHAR(100),   -- NEW: UMLS semantic type (e.g., "Disease or Syndrome")
  SourceResourceType VARCHAR(50),   -- NEW: "Condition", "MedicationRequest", etc.
  Confidence FLOAT NOT NULL,
  EmbeddingVector VECTOR(DOUBLE, 384),
  ExtractedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ExtractedBy VARCHAR(100) DEFAULT 'structured'  -- 'structured', 'llm', 'regex'
);

-- Indexes for efficient queries
CREATE INDEX idx_entities_patient ON RAG.Entities(PatientID);
CREATE INDEX idx_entities_type ON RAG.Entities(EntityType);
CREATE INDEX idx_entities_terminology ON RAG.Entities(TerminologyCode);
CREATE INDEX idx_entities_umls ON RAG.Entities(UMLS_CUI);
```

```sql
-- Updated RAG.EntityRelationships schema
CREATE TABLE RAG.EntityRelationships (
  RelationshipID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  SourceEntityID BIGINT NOT NULL,
  TargetEntityID BIGINT NOT NULL,
  RelationshipType VARCHAR(50) NOT NULL,  -- TREATS, CAUSES, ASSOCIATED_WITH, DIAGNOSED_IN
  ResourceID BIGINT NOT NULL,
  PatientID VARCHAR(100),           -- NEW: For patient-scoped relationship queries
  Confidence FLOAT NOT NULL,        -- 1.0 for coded, <1.0 for inferred
  Context VARCHAR(1000),
  ExtractedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ExtractedBy VARCHAR(100) DEFAULT 'structured'
);

CREATE INDEX idx_relationships_source ON RAG.EntityRelationships(SourceEntityID);
CREATE INDEX idx_relationships_target ON RAG.EntityRelationships(TargetEntityID);
CREATE INDEX idx_relationships_patient ON RAG.EntityRelationships(PatientID);
```

## Architecture

### Component Diagram

```
FHIR Endpoint (IRIS for Health)
        │
        ├── POST /Bundle  ────────────────┐
        │                                 │
        ▼                                 ▼
   FHIR Storage                  Extraction Trigger
   (HSFHIR_*)                    (ObjectScript callback)
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ FHIREntityExtractor │
                              │                     │
                              │  • Condition        │
                              │  • MedicationRequest│
                              │  • Procedure        │
                              │  • Observation      │
                              │  • AllergyIntolerance│
                              │  • DocumentReference│
                              └─────────┬───────────┘
                                        │
                      ┌─────────────────┼─────────────────┐
                      │                 │                 │
                      ▼                 ▼                 ▼
               Structured          LLM (Bedrock)    Embedding Service
               Extraction          Extraction       (Generate vectors)
                      │                 │                 │
                      └─────────────────┼─────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │    RAG.Entities     │
                              │ RAG.EntityRelationships│
                              └─────────────────────┘
                                        │
                                        │
                      ┌─────────────────┼─────────────────┐
                      │                 │                 │
                      ▼                 ▼                 ▼
                 PPR Search        Vector Search     Keyword Search
                      │                 │                 │
                      └─────────────────┼─────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │   RRF Fusion        │
                              │   (hybrid_search)   │
                              └─────────────────────┘
```

### PPR Algorithm (from HippoRAG2)

```python
def personalized_pagerank(
    seed_entities: List[Tuple[int, float]],  # (entity_id, initial_weight)
    damping_factor: float = 0.5,
    max_iterations: int = 20,
    top_k: int = 50,
    bidirectional: bool = True
) -> List[Tuple[int, float]]:
    """
    Run Personalized PageRank from seed entities.

    Args:
        seed_entities: Starting points with initial weights (from keyword/vector match)
        damping_factor: Probability of following edge vs teleporting back (0.5 = balanced)
        max_iterations: Convergence limit
        top_k: Number of results to return
        bidirectional: Traverse edges in both directions

    Returns:
        Ranked list of (entity_id, ppr_score)
    """
    scores = defaultdict(float)
    for entity_id, weight in seed_entities:
        scores[entity_id] = weight

    # Normalize initial distribution
    total = sum(scores.values())
    scores = {eid: s/total for eid, s in scores.items()}
    seed_dist = dict(scores)

    for _ in range(max_iterations):
        new_scores = defaultdict(float)
        for entity_id, score in scores.items():
            neighbors = get_neighbors(entity_id, bidirectional)
            if neighbors:
                share = damping_factor * score / len(neighbors)
                for neighbor_id in neighbors:
                    new_scores[neighbor_id] += share
            # Teleport back to seed distribution
            new_scores[entity_id] += (1 - damping_factor) * seed_dist.get(entity_id, 0)
        scores = new_scores

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After FHIR bundle ingestion with 50 Conditions, RAG.Entities has 50 new rows with PatientID populated within 60 seconds
- **SC-002**: Structured extraction (Condition, MedicationRequest) captures >95% of coded entities (vs manual review)
- **SC-003**: PPR query "diabetes" returns "metformin" in top 10 results when relationship exists
- **SC-004**: PPR completes in <500ms for 10,000 entity graph
- **SC-005**: Hybrid search RRF improves recall by 20% over single-modality search (measured via test set)
- **SC-006**: Patient-scoped query returns 0 cross-patient entities (privacy compliance)
- **SC-007**: Schema migration runs idempotently without data loss

## Implementation Notes

### Phase 1: Schema & Structured Extraction (Week 1-2)
1. Migrate RAG.Entities schema (add columns, indexes)
2. Create FHIREntityExtractor for Condition, MedicationRequest, Procedure
3. Implement terminology code mapping (SNOMED, RxNorm, ICD-10)
4. Create batch extraction script with `--patient-id` filter

### Phase 2: Integration & PPR (Week 3-4)
1. Create IRIS trigger for async extraction on FHIR POST
2. Port PPR algorithm from HippoRAG2 (~50 lines Python)
3. Integrate PPR into `search_knowledge_graph` MCP tool
4. Add `ppr_enabled` parameter to hybrid_search

### Phase 3: LLM Extraction & Polish (Week 5-6)
1. Add LLM extraction for DocumentReference via Bedrock Claude
2. Create embedding backfill script
3. Performance tuning for large graphs
4. Documentation and test suite
