# Tasks: MIMIC-CXR Vector Search Table Setup

**Input**: Design documents from `/specs/009-mimic-cxr-vector-setup/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in spec - test tasks omitted per task generation rules.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Scripts: `scripts/`
- MCP Server: `mcp-server/`
- Docker: `Dockerfhir/`
- Tests: `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency verification

- [ ] T001 Verify pydicom dependency is installed in requirements.txt at mcp-server/requirements.txt
- [ ] T002 [P] Verify intersystems-irispython dependency in mcp-server/requirements.txt
- [ ] T003 [P] Verify requests library for NV-CLIP API calls in mcp-server/requirements.txt

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add VectorSearch.MIMICCXRImages DDL to Dockerfhir/iris.script with CREATE TABLE IF NOT EXISTS pattern
- [ ] T005 [P] Create indexes for SubjectID, StudyID, ViewPosition, FHIRResourceID in Dockerfhir/iris.script
- [ ] T006 Verify VECTOR(DOUBLE, 1024) type and VECTOR_COSINE function work in IRIS (test query)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automated Vector Table Creation on System Setup (Priority: P1)

**Goal**: When deploying the system via Docker, the VectorSearch.MIMICCXRImages table is automatically created if it doesn't exist.

**Independent Test**: After running the IRIS container setup, verify table exists by executing `SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages` - query should return 0 (empty table) without error.

### Implementation for User Story 1

- [ ] T007 [US1] Add VectorSearch schema creation to Dockerfhir/iris.script if not exists
- [ ] T008 [US1] Add MIMICCXRImages table DDL with all columns per data-model.md in Dockerfhir/iris.script
- [ ] T009 [US1] Ensure DDL is idempotent (IF NOT EXISTS or equivalent) in Dockerfhir/iris.script
- [ ] T010 [US1] Document table schema in Dockerfhir/README.md or inline comments

**Checkpoint**: At this point, `docker compose up` should create the table automatically

---

## Phase 4: User Story 4 - FHIR-Integrated Hybrid Search (Priority: P1)

**Goal**: MCP tools can perform hybrid searches combining FHIR patient context with vector similarity search.

**Independent Test**: Query for "find chest X-rays similar to pneumonia for patient X" where X is a known patient. Verify results are filtered to that patient's images only.

### Implementation for User Story 4

- [ ] T011 [US4] Create search_medical_images MCP tool skeleton in mcp-server/fhir_graphrag_mcp_server.py
- [ ] T012 [US4] Implement text-to-embedding conversion via NV-CLIP API in mcp-server/fhir_graphrag_mcp_server.py
- [ ] T013 [US4] Implement VECTOR_COSINE similarity query against VectorSearch.MIMICCXRImages in mcp-server/fhir_graphrag_mcp_server.py
- [ ] T014 [US4] Add patient_id filter parameter to search_medical_images per contracts/search-medical-images.yaml
- [ ] T015 [US4] Add view_position filter parameter to search_medical_images
- [ ] T016 [US4] Add limit and min_similarity parameters with defaults (10, 0.5)
- [ ] T017 [US4] Handle NV-CLIP service unavailable with graceful error response (503)
- [ ] T018 [US4] Handle empty results gracefully with "No images found" message
- [ ] T019 [US4] Return ImageResult objects with similarity scores per contract schema
- [ ] T020 [US4] Add search_medical_images tool to Streamlit UI quick actions in mcp-server/streamlit_app.py

**Checkpoint**: At this point, hybrid search should work for any populated table

---

## Phase 5: User Story 2 - Batch Image Ingestion Script (Priority: P2)

**Goal**: A Python script that processes MIMIC-CXR DICOM files, generates NV-CLIP embeddings, and inserts records into the vector table.

**Independent Test**: Run the ingestion script with a small subset of DICOM files (e.g., 10 images). Verify records appear in the table with valid 1024-dimensional vectors.

### Implementation for User Story 2

- [ ] T021 [US2] Create scripts/ingest_mimic_cxr.py with argparse CLI structure
- [ ] T022 [US2] Implement --source PATH argument for DICOM directory path
- [ ] T023 [US2] Implement --batch-size INT argument (default: 32)
- [ ] T024 [US2] Implement --limit INT argument for max images to process
- [ ] T025 [US2] Implement --skip-existing flag to skip already-ingested images
- [ ] T026 [US2] Implement --dry-run flag to preview what would be processed
- [ ] T027 [P] [US2] Create DICOM file discovery function using pydicom in scripts/ingest_mimic_cxr.py
- [ ] T028 [P] [US2] Create DICOM metadata extraction function (SubjectID, StudyID, ViewPosition, ImageID)
- [ ] T029 [US2] Implement file size check - skip files >100MB with warning
- [ ] T030 [US2] Implement NV-CLIP service health check before starting ingestion
- [ ] T031 [US2] Implement batch embedding generation via NV-CLIP POST /v1/embeddings
- [ ] T032 [US2] Implement IRIS database connection using intersystems-irispython
- [ ] T033 [US2] Implement INSERT statement for VectorSearch.MIMICCXRImages with parameterized query
- [ ] T034 [US2] Implement progress reporting (images processed, time elapsed, estimated remaining)
- [ ] T035 [US2] Implement error handling - log errors for individual files, continue processing
- [ ] T036 [US2] Implement retry logic with exponential backoff for IRIS connection failures (3 retries)
- [ ] T037 [US2] Add checkpoint logic - save progress every 100 images for recovery

**Checkpoint**: At this point, the ingestion script should work end-to-end with a local DICOM directory

---

## Phase 6: User Story 3 - Integration with Docker Compose Setup (Priority: P3)

**Goal**: Table creation and sample data are integrated into docker-compose workflow for easy developer setup.

**Independent Test**: Run `docker compose down -v && docker compose up -d` from Dockerfhir/, wait for initialization, then execute a medical image search query.

### Implementation for User Story 3

- [ ] T038 [US3] Add sample DICOM data location documentation to Dockerfhir/README.md
- [ ] T039 [US3] Create sample data initialization hook in Dockerfhir/docker-compose.yaml (optional volume mount)
- [ ] T040 [US3] Document quickstart workflow for developer setup in specs/009-mimic-cxr-vector-setup/quickstart.md

**Checkpoint**: At this point, docker compose up provides a working environment

---

## Phase 7: User Story 5 - FHIR Resource Creation on Image Ingestion (Priority: P2)

**Goal**: When images are ingested, corresponding FHIR ImagingStudy resources are created or updated.

**Independent Test**: Ingest 10 images, then query FHIR `/ImagingStudy?subject=Patient/X` and verify ImagingStudy resources exist.

### Implementation for User Story 5

- [ ] T041 [US5] Add --create-fhir flag to scripts/ingest_mimic_cxr.py
- [ ] T042 [US5] Implement FHIR Patient lookup by SubjectID via GET /Patient?identifier={SubjectID}
- [ ] T043 [US5] Implement FHIR ImagingStudy resource creation with subject reference
- [ ] T044 [US5] Map MIMIC-CXR metadata to FHIR ImagingStudy fields (Modality: DX, BodySite: Chest)
- [ ] T045 [US5] Update VectorSearch.MIMICCXRImages.FHIRResourceID after ImagingStudy creation
- [ ] T046 [US5] Handle FHIR Patient not found - log warning, continue with vector insertion only
- [ ] T047 [US5] Handle FHIR server unavailable - retry 3 times, then continue without FHIR linkage
- [ ] T048 [US5] Ensure idempotent ImagingStudy creation (check existence before create)

**Checkpoint**: At this point, images have bidirectional FHIR linkage

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T049 [P] Add environment variable documentation (IRIS_HOST, IRIS_PORT, NVCLIP_BASE_URL) to README.md
- [ ] T050 [P] Add troubleshooting section to specs/009-mimic-cxr-vector-setup/quickstart.md
- [ ] T051 Validate quickstart.md workflow end-to-end
- [ ] T052 [P] Add integration test for VectorSearch.MIMICCXRImages table existence in tests/integration/test_mimic_cxr_ingestion.py
- [ ] T053 [P] Add integration test for search_medical_images MCP tool in tests/integration/test_mimic_cxr_ingestion.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Stories 1 and 4 (both P1) can proceed in parallel after Foundational
  - User Story 2 (P2) can proceed after US1 completes (needs table to exist)
  - User Story 5 (P2) depends on US2 (extends ingestion script)
  - User Story 3 (P3) can proceed after US1 and US2 complete
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - Creates the table
- **User Story 4 (P1)**: Can start after Foundational - MCP tool for searching
- **User Story 2 (P2)**: Can start after US1 - Populates the table
- **User Story 5 (P2)**: Depends on US2 - Extends ingestion with FHIR
- **User Story 3 (P3)**: Depends on US1, US2 - Docker integration

### Within Each User Story

- Core infrastructure before specific features
- Error handling after happy path
- Documentation alongside implementation

### Parallel Opportunities

- T002, T003 can run in parallel (different dependencies)
- T005 can run in parallel with T004 (indexes can be added separately)
- T027, T028 can run in parallel (independent functions)
- T049, T050, T052, T053 can run in parallel (independent docs/tests)

---

## Parallel Example: User Story 2

```bash
# Launch independent DICOM functions together:
Task: "Create DICOM file discovery function using pydicom in scripts/ingest_mimic_cxr.py"
Task: "Create DICOM metadata extraction function (SubjectID, StudyID, ViewPosition, ImageID)"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 4 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (table creation)
4. Complete Phase 4: User Story 4 (MCP search tool)
5. **STOP and VALIDATE**: Test table creation and search tool independently
6. Deploy/demo if ready - can manually insert test data to validate search

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (table creation) → Test table exists → Deploy
3. Add User Story 4 (search tool) → Test search works with empty table → Deploy
4. Add User Story 2 (ingestion) → Test with real DICOM files → Deploy
5. Add User Story 5 (FHIR linkage) → Test FHIR integration → Deploy
6. Add User Story 3 (Docker integration) → Test full workflow → Deploy

### Recommended Order for Single Developer

1. T001-T006: Setup + Foundational
2. T007-T010: US1 - Table creation
3. T011-T020: US4 - Search tool (can test with manual data)
4. T021-T037: US2 - Ingestion script
5. T041-T048: US5 - FHIR integration
6. T038-T040: US3 - Docker integration
7. T049-T053: Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Priority order: US1=US4 (P1), US2=US5 (P2), US3 (P3)
