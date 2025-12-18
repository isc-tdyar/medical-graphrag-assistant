# Quickstart: MIMIC-CXR Vector Search

**Date**: 2025-12-18 | **Branch**: `009-mimic-cxr-vector-setup`

## Prerequisites

1. **Running IRIS container** with VectorSearch schema enabled
2. **NV-CLIP service** available at `NVCLIP_BASE_URL`
3. **MIMIC-CXR data** (optional, for ingestion)
   - Requires PhysioNet credentialed access for full dataset
   - ~377K chest X-ray images

## Quick Setup

### 1. Verify Table Exists

After starting the Docker container, the table should be auto-created:

```sql
-- Connect to IRIS and verify
SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages;
-- Should return 0 (empty) without error
```

### 2. Test MCP Tool (Empty Table)

```bash
# Via Streamlit UI
# Click "Pneumonia X-rays" button
# Should return "No images found" message (not an error)
```

### 3. Ingest Sample Images

```bash
# From repository root
python scripts/ingest_mimic_cxr.py \
  --source /path/to/mimic-cxr-sample \
  --limit 100 \
  --batch-size 32
```

Expected output:
```
Connecting to IRIS...
Checking NV-CLIP service...
Found 100 DICOM files
Processing batch 1/4...
Processing batch 2/4...
Processing batch 3/4...
Processing batch 4/4...
Ingestion complete: 100 images processed, 0 failed
```

### 4. Test Search

```bash
# Via Streamlit chat
> Search for chest X-rays with pneumonia pattern

# Expected response includes similarity scores
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_HOST` | localhost | IRIS database host |
| `IRIS_PORT` | 1972 | IRIS SuperServer port |
| `NVCLIP_BASE_URL` | http://localhost:8002/v1 | NV-CLIP embedding service |

### Ingestion CLI Options

```bash
python scripts/ingest_mimic_cxr.py --help

Options:
  --source PATH        Directory containing DICOM files (required)
  --batch-size INT     Images per NV-CLIP request (default: 32)
  --limit INT          Max images to process (default: all)
  --skip-existing      Skip images already in database
  --dry-run            Show what would be processed
  --create-fhir        Create FHIR ImagingStudy resources
```

## Troubleshooting

### "Table does not exist" Error

The table DDL should run on container startup. If missing:

```sql
-- Run manually in IRIS terminal
DO $SYSTEM.SQL.Execute("CREATE TABLE IF NOT EXISTS VectorSearch.MIMICCXRImages (...)")
```

### "NV-CLIP service unavailable"

1. Check service is running: `curl $NVCLIP_BASE_URL/health`
2. Verify GPU is available: `nvidia-smi`
3. Check logs: `docker logs nvclip`

### "No images found" for valid query

1. Verify table has data: `SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages`
2. Lower similarity threshold: `min_similarity: 0.3`
3. Check embedding dimensions match (should be 1024)

### Slow ingestion (<1 img/sec)

1. Increase batch size: `--batch-size 64`
2. Ensure GPU is being used by NV-CLIP
3. Check network latency to NV-CLIP service

## Next Steps

After basic setup:

1. Run full MIMIC-CXR ingestion (~377K images, ~10 hours on GPU)
2. Create FHIR ImagingStudy resources for hybrid search
3. Test patient-filtered queries via Streamlit UI
