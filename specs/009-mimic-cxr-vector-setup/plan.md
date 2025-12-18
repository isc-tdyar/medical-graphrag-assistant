# Implementation Plan: MIMIC-CXR Vector Search Table Setup

**Branch**: `009-mimic-cxr-vector-setup` | **Date**: 2025-12-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-mimic-cxr-vector-setup/spec.md`

## Summary

Set up the VectorSearch.MIMICCXRImages table in InterSystems IRIS for storing medical chest X-ray image embeddings from MIMIC-CXR dataset. This enables semantic similarity search on medical images via NV-CLIP 1024-dimensional vectors. The feature includes automated table creation on container startup, a batch ingestion script for processing DICOM files from local directories, and hybrid search combining FHIR patient context with vector similarity.

## Technical Context

**Language/Version**: Python 3.11 (ingestion scripts, MCP tools), ObjectScript (IRIS initialization)
**Primary Dependencies**: intersystems-irispython, pydicom, requests (NV-CLIP API), boto3 (FHIR)
**Storage**: InterSystems IRIS with native VECTOR(DOUBLE, 1024) type
**Testing**: pytest (unit/integration), Playwright (UX tests via MCP)
**Target Platform**: AWS EC2 with NVIDIA GPU (g5.xlarge), Docker
**Project Type**: Single (extends existing MCP server architecture)
**Performance Goals**: 10 images/second ingestion (GPU), 1 image/second (CPU); <500ms vector search
**Constraints**: <100MB per DICOM file (skip larger), idempotent operations
**Scale/Scope**: 100,000+ image records, MIMIC-CXR dataset (~377K images)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Authorship | PASS | No AI attribution |
| II. MCP-First | PASS | `search_medical_images` tool exposed via MCP |
| III. Vector DB Purity | PASS | IRIS-only vector storage (VectorSearch schema) |
| IV. Medical Data Integrity | PASS | DICOM metadata preserved, FHIR linkage maintained |
| V. Graceful Degradation | PASS | NV-CLIP unavailable handling, FHIR sync retry |
| VI. TDD & UX Testing | PASS | Playwright tests defined for image search UI |

**Gate Status**: PASS - All principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/009-mimic-cxr-vector-setup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── search-medical-images.yaml
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
scripts/
├── ingest_mimic_cxr.py         # NEW: Batch DICOM ingestion script
└── populate_vector_tables.py    # Existing, may extend

Dockerfhir/
├── iris.script                  # MODIFY: Add VectorSearch.MIMICCXRImages DDL
└── docker-compose.yaml          # MODIFY: Sample data init integration

mcp-server/
├── fhir_graphrag_mcp_server.py  # MODIFY: Add search_medical_images tool
└── streamlit_app.py             # MODIFY: UI for image search results

tests/
├── integration/
│   └── test_mimic_cxr_ingestion.py  # NEW: Integration tests
└── ux/playwright/
    └── medical-image-search.spec.ts  # NEW: Playwright UX tests
```

**Structure Decision**: Single project extension - adds ingestion script and modifies existing MCP server. Follows established patterns from VectorSearch.Embeddings table.

## Complexity Tracking

No violations requiring justification. Feature follows established patterns for vector storage and MCP tools.

## Dependencies & Integration Points

| Component | Interface | Notes |
|-----------|-----------|-------|
| NV-CLIP API | HTTP POST `/v1/embeddings` | 1024-dim vectors, image+text input |
| IRIS VectorSearch | SQL DDL/DML | Native VECTOR type with VECTOR_COSINE |
| FHIR Repository | REST `/ImagingStudy` | Subject reference for patient linkage |
| Streamlit UI | Tool callback | Display image search results |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DICOM parsing errors | Medium | Low | pydicom with fallback, skip corrupted files |
| NV-CLIP rate limits | Low | Medium | Batch size config, retry with backoff |
| FHIR Patient mismatch | Medium | Low | Best-effort linking, log warnings |
| Large file memory | Low | Medium | Skip >100MB files per clarification |

## Phase 0 Outputs

- [research.md](./research.md) - Technology decisions and best practices
- IRIS VECTOR DDL patterns researched
- NV-CLIP embedding API integration patterns

## Phase 1 Outputs

- [data-model.md](./data-model.md) - MIMICCXRImage entity schema
- [contracts/search-medical-images.yaml](./contracts/search-medical-images.yaml) - MCP tool contract
- [quickstart.md](./quickstart.md) - Developer setup guide
