# Research: MIMIC-CXR Vector Search Table Setup

**Date**: 2025-12-18 | **Branch**: `009-mimic-cxr-vector-setup`

## Technology Decisions

### 1. IRIS VECTOR DDL Pattern

**Decision**: Use `VECTOR(DOUBLE, 1024)` native type with `VECTOR_COSINE` similarity function

**Rationale**:
- Established pattern in existing `VectorSearch.Embeddings` table
- Native IRIS support provides optimal performance
- 1024 dimensions matches NV-CLIP output exactly

**Alternatives Considered**:
- BLOB storage with application-level similarity: Rejected (poor query performance)
- External vector DB (Pinecone): Rejected (violates Constitution III)

**Reference**: Existing `VectorSearch.Embeddings` DDL in `Dockerfhir/iris.script`

### 2. DICOM Parsing Library

**Decision**: Use `pydicom` for DICOM file parsing

**Rationale**:
- Industry standard Python DICOM library
- Handles MIMIC-CXR metadata (SubjectID, StudyID, ViewPosition)
- Graceful handling of corrupted/incomplete files

**Alternatives Considered**:
- SimpleITK: More complex, overkill for metadata extraction
- PIL/OpenCV only: Cannot read DICOM headers

### 3. Image Embedding Pipeline

**Decision**: NV-CLIP via existing NIM endpoint at `NVCLIP_BASE_URL`

**Rationale**:
- Already deployed and tested in system
- 1024-dimensional multimodal embeddings
- Supports both image and text queries for similarity search

**API Pattern**:
```python
POST {NVCLIP_BASE_URL}/v1/embeddings
Content-Type: application/json

{
    "input": [base64_encoded_image],
    "model": "nvclip",
    "input_type": "image"
}
```

### 4. FHIR Patient Linkage Strategy

**Decision**: Best-effort linking via SubjectID to FHIR Patient identifier

**Rationale**:
- MIMIC-CXR uses `pNNNNNNNN` format (e.g., `p10000032`)
- Map to FHIR Patient identifier search
- Graceful fallback: store image even if patient not found

**Mapping Flow**:
```
MIMIC-CXR SubjectID (p10000032)
  → FHIR Patient search: /Patient?identifier=p10000032
  → If found: link via FHIRResourceID column
  → If not found: store with warning, FHIRResourceID = NULL
```

### 5. Batch Processing Pattern

**Decision**: Configurable batch size with progress reporting

**Rationale**:
- NV-CLIP can process multiple images per request
- Balance between throughput and memory usage
- Default batch size: 32 images

**CLI Pattern**:
```bash
python ingest_mimic_cxr.py \
  --source /path/to/mimic-cxr \
  --batch-size 32 \
  --limit 1000 \
  --skip-existing
```

### 6. Idempotency Strategy

**Decision**: Upsert based on ImageID (DICOM SOP Instance UID)

**Rationale**:
- ImageID is globally unique per DICOM specification
- Prevents duplicates on re-runs
- Enables incremental ingestion

**SQL Pattern**:
```sql
-- Check existence
SELECT 1 FROM VectorSearch.MIMICCXRImages WHERE ImageID = ?
-- Insert only if not exists (handled in Python)
```

## Best Practices Applied

### DICOM Processing
- Always validate file before reading full pixel data
- Skip files > 100MB (per clarification - likely CT/MRI, not CXR)
- Log corrupted files but continue processing

### Vector Search Optimization
- Create index after bulk load (faster than incremental)
- Use VECTOR_COSINE for normalized embeddings
- Batch similarity queries when possible

### Error Recovery
- Checkpoint progress every 100 images
- Store failed file list for retry
- NV-CLIP timeout: 30 seconds per batch

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Where does MIMIC-CXR data come from? | Local directory path (--source flag) |
| How to handle >100MB files? | Skip with warning |
| Embedding service unavailable? | Fail gracefully, suggest checking NVCLIP_BASE_URL |
| Patient not in FHIR? | Store image anyway, log warning |
