# Data Model: MIMIC-CXR Vector Search

**Date**: 2025-12-18 | **Branch**: `009-mimic-cxr-vector-setup`

## Entities

### VectorSearch.MIMICCXRImages

The primary table for storing chest X-ray image embeddings with MIMIC-CXR metadata.

```sql
CREATE TABLE VectorSearch.MIMICCXRImages (
    -- Primary key: DICOM SOP Instance UID
    ImageID VARCHAR(128) NOT NULL PRIMARY KEY,

    -- MIMIC-CXR identifiers
    SubjectID VARCHAR(20) NOT NULL,           -- Patient ID (e.g., p10000032)
    StudyID VARCHAR(20) NOT NULL,             -- Study identifier
    DicomID VARCHAR(128),                     -- DICOM file name

    -- Image metadata
    ImagePath VARCHAR(500) NOT NULL,          -- Original file path
    ViewPosition VARCHAR(20),                 -- PA, AP, LATERAL, LL, SWIMMERS

    -- Vector embedding
    Vector VECTOR(DOUBLE, 1024) NOT NULL,     -- NV-CLIP embedding
    EmbeddingModel VARCHAR(50) DEFAULT 'nvidia/nvclip',
    Provider VARCHAR(50) DEFAULT 'nvclip',

    -- FHIR linkage (optional, best-effort)
    FHIRResourceID VARCHAR(100),              -- e.g., "ImagingStudy/123"

    -- Audit
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query patterns
CREATE INDEX idx_mimiccxr_subject ON VectorSearch.MIMICCXRImages(SubjectID);
CREATE INDEX idx_mimiccxr_study ON VectorSearch.MIMICCXRImages(StudyID);
CREATE INDEX idx_mimiccxr_view ON VectorSearch.MIMICCXRImages(ViewPosition);
CREATE INDEX idx_mimiccxr_fhir ON VectorSearch.MIMICCXRImages(FHIRResourceID);
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| ImageID | VARCHAR(128) | DICOM SOP Instance UID, globally unique |
| SubjectID | VARCHAR(20) | MIMIC-CXR patient identifier (pNNNNNNNN) |
| StudyID | VARCHAR(20) | MIMIC-CXR study identifier (sNNNNNNNN) |
| DicomID | VARCHAR(128) | Original DICOM filename |
| ImagePath | VARCHAR(500) | Ingestion source path (for debugging) |
| ViewPosition | VARCHAR(20) | Radiographic view: PA, AP, LATERAL, LL |
| Vector | VECTOR(1024) | NV-CLIP 1024-dimensional embedding |
| EmbeddingModel | VARCHAR(50) | Model used for embedding generation |
| Provider | VARCHAR(50) | Embedding service provider |
| FHIRResourceID | VARCHAR(100) | Reference to FHIR ImagingStudy (nullable) |
| CreatedAt | TIMESTAMP | Record creation time |
| UpdatedAt | TIMESTAMP | Last modification time |

### Validation Rules

1. **ImageID**: Must be valid DICOM SOP Instance UID format
2. **SubjectID**: Must match pattern `p[0-9]+`
3. **StudyID**: Must match pattern `s[0-9]+`
4. **ViewPosition**: Must be one of: PA, AP, LATERAL, LL, SWIMMERS
5. **Vector**: Must be exactly 1024 dimensions, non-zero magnitude

### State Transitions

Images have simple lifecycle:
1. **Pending** (file discovered, not yet processed)
2. **Processing** (embedding generation in progress)
3. **Stored** (successfully inserted in table)
4. **Failed** (error during processing, logged)

## Relationships

### To FHIR Resources

```
VectorSearch.MIMICCXRImages.SubjectID
  → FHIR Patient.identifier (best-effort mapping)

VectorSearch.MIMICCXRImages.FHIRResourceID
  → FHIR ImagingStudy.id (when FHIR resource created)
```

### Query Patterns

#### 1. Semantic Image Search (Vector Similarity)

```sql
SELECT
    ImageID, SubjectID, StudyID, ViewPosition,
    VECTOR_COSINE(Vector, ?) as similarity
FROM VectorSearch.MIMICCXRImages
ORDER BY similarity DESC
LIMIT 10
```

#### 2. Patient-Filtered Search (Hybrid)

```sql
SELECT
    ImageID, SubjectID, ViewPosition,
    VECTOR_COSINE(Vector, ?) as similarity
FROM VectorSearch.MIMICCXRImages
WHERE SubjectID = ?
ORDER BY similarity DESC
LIMIT 10
```

#### 3. FHIR-Linked Query

```sql
SELECT
    m.ImageID, m.SubjectID, m.ViewPosition, m.FHIRResourceID,
    VECTOR_COSINE(m.Vector, ?) as similarity
FROM VectorSearch.MIMICCXRImages m
WHERE m.FHIRResourceID IS NOT NULL
  AND m.SubjectID IN (
    SELECT identifier FROM FHIR_Patient WHERE condition_code = ?
  )
ORDER BY similarity DESC
```

## Sample Data

```json
{
  "ImageID": "1.2.840.113654.2.55.XXXXXXX",
  "SubjectID": "p10000032",
  "StudyID": "s50414267",
  "DicomID": "abcd1234.dcm",
  "ImagePath": "/data/mimic-cxr/p10/p10000032/s50414267/abcd1234.dcm",
  "ViewPosition": "PA",
  "Vector": [0.0123, -0.0456, ...],  // 1024 values
  "EmbeddingModel": "nvidia/nvclip",
  "Provider": "nvclip",
  "FHIRResourceID": "ImagingStudy/789",
  "CreatedAt": "2025-12-18T10:30:00Z"
}
```
