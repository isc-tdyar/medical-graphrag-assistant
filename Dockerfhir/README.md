# FHIR Server Docker Setup

Docker configuration for InterSystems IRIS for Health with FHIR R4 repository.

## Quick Start

```bash
cd Dockerfhir
docker compose up -d
```

Wait ~2-3 minutes for FHIR server initialization, then verify:

```bash
curl http://localhost:32783/csp/healthshare/demo/fhir/r4/metadata
```

## Ports

| Port | Service |
|------|---------|
| 32783 | FHIR R4 API (external) |
| 32782 | IRIS SuperServer (for DB connections) |

## Features Initialized on Startup

The `iris.script` runs on container startup and configures:

1. **FHIR R4 Server** at `/csp/healthshare/demo/fhir/r4`
2. **VectorSearch Schema** for medical image embeddings
3. **MIMICCXRImages Table** for chest X-ray vector search

### VectorSearch.MIMICCXRImages Table Schema

```sql
CREATE TABLE VectorSearch.MIMICCXRImages (
    ImageID VARCHAR(128) PRIMARY KEY,
    SubjectID VARCHAR(20) NOT NULL,
    StudyID VARCHAR(20) NOT NULL,
    DicomID VARCHAR(128),
    ImagePath VARCHAR(500) NOT NULL,
    ViewPosition VARCHAR(20),
    Vector VECTOR(DOUBLE, 1024) NOT NULL,
    EmbeddingModel VARCHAR(50) DEFAULT 'nvidia/nvclip',
    Provider VARCHAR(50) DEFAULT 'nvclip',
    FHIRResourceID VARCHAR(100),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes**:
- `idx_mimiccxr_subject` on SubjectID
- `idx_mimiccxr_study` on StudyID
- `idx_mimiccxr_view` on ViewPosition
- `idx_mimiccxr_fhir` on FHIRResourceID

## MIMIC-CXR Data

### Data Source

MIMIC-CXR is a large publicly available dataset of chest X-rays:
- ~377,000 chest radiographs
- 227,835 studies from 65,379 patients
- Requires PhysioNet credentialed access

Access: https://physionet.org/content/mimic-cxr/2.0.0/

### Directory Structure

MIMIC-CXR files follow this structure:
```
mimic-cxr/
  files/
    p10/
      p10000032/
        s50414267/
          02aa804e-bde0afdd-112c0b34-7bc16630-4e384014.dcm
          ...
```

### Ingesting MIMIC-CXR Images

Use the ingestion script to populate the VectorSearch table:

```bash
# From repository root
python scripts/ingest_mimic_cxr.py \
    --source /path/to/mimic-cxr/files \
    --batch-size 32 \
    --limit 1000
```

See `scripts/ingest_mimic_cxr.py --help` for all options.

## Environment Variables

The MCP server and ingestion scripts use these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_HOST` | localhost | IRIS database host |
| `IRIS_PORT` | 1972 | IRIS SuperServer port (use 32782 for Docker) |
| `NVCLIP_BASE_URL` | http://localhost:8002/v1 | NV-CLIP embedding service |
| `FHIR_BASE_URL` | http://localhost:32783/csp/healthshare/demo/fhir/r4 | FHIR API endpoint |

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs iris-fhir

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### FHIR endpoint returns 404

Wait longer for initialization (FHIR setup takes 2-3 minutes):

```bash
# Check container status
docker ps

# Wait for health check to pass
docker inspect iris-fhir --format='{{.State.Health.Status}}'
```

### VectorSearch table doesn't exist

The table should be auto-created on startup. If missing, check logs:

```bash
docker compose logs iris-fhir | grep -i "vectorsearch"
```

Or create manually via IRIS terminal:

```bash
docker exec -it iris-fhir iris session iris
```

Then run the CREATE TABLE statement from iris.script.

### Connection refused on port 32782

Ensure the container is running and ports are mapped:

```bash
docker compose ps
nc -zv localhost 32782
```

## Sample Data Mount (Optional)

To mount sample DICOM files for development:

```yaml
# Add to docker-compose.yaml
volumes:
  - /path/to/mimic-cxr-sample:/mimic-data:ro
```

Then run ingestion from within container:

```bash
docker exec iris-fhir python /scripts/ingest_mimic_cxr.py \
    --source /mimic-data \
    --limit 100
```

## Related Documentation

- [MIMIC-CXR Vector Search Quickstart](../specs/009-mimic-cxr-vector-setup/quickstart.md)
- [Feature 009 Specification](../specs/009-mimic-cxr-vector-setup/spec.md)
- [Ingestion Script](../scripts/ingest_mimic_cxr.py)
