# Feature Specification: MIMIC-CXR Vector Search Table Setup

**Feature Branch**: `009-mimic-cxr-vector-setup`
**Created**: 2025-12-18
**Status**: Draft
**Input**: User description: "set up mimic-cxr vector search tables and populate them as part of our system for ingesting data for system setup"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Vector Table Creation on System Setup (Priority: P1)

When deploying the medical-graphrag-assistant system (via Docker container startup or setup script), the VectorSearch.MIMICCXRImages table should be automatically created if it doesn't exist, ensuring the medical image search feature has its required database schema ready.

**Why this priority**: Without the table, the medical_image_search tool fails with "table does not exist" error. This blocks all medical image search functionality.

**Independent Test**: After running the IRIS container setup, verify table exists by executing `SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages` - query should return 0 (empty table) without error.

**Acceptance Scenarios**:

1. **Given** a fresh IRIS container with no VectorSearch schema, **When** the container starts and runs initialization scripts, **Then** the VectorSearch.MIMICCXRImages table exists with correct schema (columns: ImageID, SubjectID, StudyID, DicomID, ImagePath, ViewPosition, Vector, EmbeddingModel, Provider, FHIRResourceID, CreatedAt)

2. **Given** an existing IRIS container with the table already created, **When** the initialization script runs again, **Then** the script skips creation (idempotent) and preserves existing data

---

### User Story 2 - Batch Image Ingestion Script (Priority: P2)

A Python script that processes MIMIC-CXR DICOM files, generates NV-CLIP embeddings via the embedding service, and inserts records into the VectorSearch.MIMICCXRImages table. Supports batch processing with progress reporting and error recovery.

**Why this priority**: Once the table exists, we need a way to populate it with actual medical image vectors. This enables the semantic search functionality.

**Independent Test**: Run the ingestion script with a small subset of DICOM files (e.g., 10 images). Verify records appear in the table with valid 1024-dimensional vectors.

**Acceptance Scenarios**:

1. **Given** a directory containing MIMIC-CXR DICOM files and a running NV-CLIP service, **When** the ingestion script runs with `--source /path/to/mimic-cxr --limit 100`, **Then** 100 images are vectorized and inserted into the table with progress output

2. **Given** the ingestion script has already processed some images, **When** running again with `--skip-existing`, **Then** only new images are processed (avoiding duplicate work)

3. **Given** a DICOM file that cannot be read (corrupted), **When** the ingestion script encounters it, **Then** an error is logged, the file is skipped, and processing continues with remaining files

---

### User Story 3 - Integration with Docker Compose Setup (Priority: P3)

The table creation SQL and sample data population are integrated into the Dockerfhir/docker-compose.yaml workflow, so a developer can run `docker compose up` and have a working medical image search with sample data.

**Why this priority**: Reduces friction for new developers and demo setups. Not strictly required for production deployments where data is ingested separately.

**Independent Test**: Run `docker compose down -v && docker compose up -d` from Dockerfhir/, wait for initialization, then execute a medical image search query through the Streamlit UI.

**Acceptance Scenarios**:

1. **Given** a clean Docker environment, **When** running `docker compose up -d` in Dockerfhir/, **Then** within 5 minutes, the VectorSearch.MIMICCXRImages table exists with at least 50 sample images vectorized

2. **Given** the docker-compose setup completed, **When** using the Streamlit UI to search for "chest X-ray with pneumonia", **Then** results are returned with similarity scores

---

### User Story 4 - FHIR-Integrated Hybrid Search (Priority: P1)

MCP tools can perform hybrid searches combining FHIR query syntax (patient filters, date ranges, encounter context) with vector similarity search. Images in VectorSearch.MIMICCXRImages are linked to FHIR ImagingStudy/DiagnosticReport resources via SubjectID mapping.

**Why this priority**: The core value proposition of this system is combining structured FHIR data with semantic image search. Without FHIR integration, the image search operates in isolation from patient context.

**Independent Test**: Query for "find chest X-rays similar to pneumonia for patient X" where X is a known patient in the FHIR repository. Verify results are filtered to that patient's images only.

**Acceptance Scenarios**:

1. **Given** a patient with SubjectID "p10000032" exists in FHIR and has images in VectorSearch.MIMICCXRImages, **When** calling `search_medical_images` with query "pneumonia" and patient_id filter, **Then** only images belonging to that patient are returned with similarity scores

2. **Given** FHIR ImagingStudy resources exist with references to image paths, **When** the ingestion script processes images, **Then** it creates/updates FHIR ImagingStudy resources to maintain bidirectional linkage

3. **Given** a hybrid search MCP tool, **When** called with FHIR filters (patient, date range, view position) and semantic query "consolidation pattern", **Then** SQL query combines FHIR patient lookup with vector cosine similarity in a single efficient query

4. **Given** FHIR DiagnosticReport resources exist with impression text, **When** performing hybrid search, **Then** the system can optionally include DiagnosticReport content in relevance ranking

---

### User Story 5 - FHIR Resource Creation on Image Ingestion (Priority: P2)

When images are ingested into the vector table, corresponding FHIR ImagingStudy resources are created or updated in the FHIR repository, ensuring every image is discoverable via standard FHIR queries.

**Why this priority**: Enables FHIR-first workflows where clinicians discover images through FHIR APIs, then use vector search for similarity analysis. Also ensures compliance with healthcare data standards.

**Independent Test**: Ingest 10 images, then query FHIR `/ImagingStudy?subject=Patient/X` and verify ImagingStudy resources exist with correct references.

**Acceptance Scenarios**:

1. **Given** a DICOM image with SubjectID "p10000032" is ingested, **When** ingestion completes, **Then** a FHIR ImagingStudy resource exists with subject reference to the corresponding Patient

2. **Given** MIMIC-CXR metadata CSV contains study-level information (AccessionNumber, StudyDate), **When** creating ImagingStudy resources, **Then** metadata is mapped to appropriate FHIR fields

3. **Given** an image already has a corresponding ImagingStudy, **When** re-ingesting the same image, **Then** the existing ImagingStudy is not duplicated (idempotent)

---

### Edge Cases

- What happens when NV-CLIP embedding service is unavailable during ingestion?
  - Script should fail gracefully with clear error message suggesting to check NVCLIP_BASE_URL

- What happens when IRIS database connection fails during ingestion?
  - Script should retry connection 3 times with exponential backoff, then fail with connection details

- What happens with very large DICOM files (>100MB)?
  - Should log warning and skip, or process with memory limits

- What happens when disk space is insufficient for batch processing?
  - Check available space before starting, warn if <1GB available

- What happens when SubjectID in MIMIC-CXR doesn't match any FHIR Patient?
  - Log warning, store image anyway with SubjectID; FHIR linkage is best-effort

- What happens when FHIR server is unavailable during FHIR resource creation?
  - Retry 3 times, then continue with vector insertion only; mark for FHIR sync later

- What happens when performing hybrid search with invalid patient_id filter?
  - Return empty results with warning message, not an error

- What happens when vector table has images but no FHIR ImagingStudy exists?
  - Hybrid search degrades gracefully to vector-only search with warning

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create VectorSearch schema if it doesn't exist on IRIS startup
- **FR-002**: System MUST create MIMICCXRImages table with correct DDL on IRIS startup
- **FR-003**: Table creation MUST be idempotent (safe to run multiple times)
- **FR-004**: Ingestion script MUST support batch size configuration (default: 32 images)
- **FR-005**: Ingestion script MUST report progress (images processed, time elapsed, estimated remaining)
- **FR-006**: Ingestion script MUST log errors for individual files without stopping entire process
- **FR-007**: Ingestion script MUST validate NV-CLIP service availability before starting
- **FR-008**: Ingestion script MUST support `--dry-run` mode to show what would be processed
- **FR-009**: System MUST store 1024-dimensional vectors from NV-CLIP embeddings
- **FR-010**: Each image record MUST include SubjectID, StudyID, ImageID, ViewPosition, and ImagePath

### FHIR Integration Requirements

- **FR-011**: MCP tool `search_medical_images` MUST accept optional `patient_id` parameter to filter results
- **FR-012**: Hybrid search MUST support combining FHIR patient context with vector similarity in single SQL query
- **FR-013**: System SHOULD create FHIR ImagingStudy resources when ingesting new images (best-effort)
- **FR-014**: ImagingStudy resources MUST include subject reference linking to FHIR Patient
- **FR-015**: Ingestion script MUST support `--create-fhir-resources` flag to enable FHIR resource creation
- **FR-016**: Hybrid search results MUST return both similarity score and FHIR resource references
- **FR-017**: System MUST support querying images by FHIR reference (e.g., ImagingStudy/123)
- **FR-018**: Vector search combined with FHIR filters MUST complete in < 1 second for typical queries

### Key Entities

- **MIMICCXRImage**: A chest X-ray image record with vector embedding
  - ImageID (PK): Unique DICOM identifier
  - SubjectID: Patient identifier (maps to FHIR Patient)
  - StudyID: Study/session identifier
  - ViewPosition: PA, AP, LATERAL, LL, SWIMMERS
  - Vector: 1024-dimensional NV-CLIP embedding
  - EmbeddingModel: 'nvidia/nvclip'
  - Provider: 'nvclip'
  - FHIRResourceID: Reference to FHIR ImagingStudy (e.g., "ImagingStudy/123")

- **IngestionJob**: Represents a batch processing run
  - Source directory
  - Total files found
  - Files processed/skipped/failed
  - Start/end timestamps

- **FHIRImagingStudy**: FHIR resource linking to vector table records
  - Subject reference (Patient)
  - Identifier (StudyID)
  - Series containing image references
  - Modality: DX (Digital Radiography)
  - BodySite: Chest

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fresh `docker compose up` creates VectorSearch.MIMICCXRImages table within 60 seconds of container start
- **SC-002**: Ingestion script processes at least 10 images/second with GPU-enabled NV-CLIP, 1 image/second with CPU
- **SC-003**: After ingestion, `medical_image_search` tool returns results with similarity scores for any text query
- **SC-004**: Table supports at least 100,000 image records without performance degradation on vector search (< 500ms query time)
- **SC-005**: System handles re-runs gracefully - no duplicate records, no data loss

### FHIR Integration Success Criteria

- **SC-006**: Hybrid query `search_medical_images(query="pneumonia", patient_id="p10000032")` returns only that patient's images in < 1 second
- **SC-007**: After ingesting 100 images with `--create-fhir-resources`, at least 90 corresponding ImagingStudy resources exist in FHIR
- **SC-008**: FHIR query `/ImagingStudy?subject=Patient/X` returns studies with proper references to vector table
- **SC-009**: MCP tool can perform combined query: "Find pneumonia-like images for patients with diabetes" using FHIR Condition + vector search
