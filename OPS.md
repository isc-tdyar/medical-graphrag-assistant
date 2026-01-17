# OPS.md - Operations Runbook

**CRITICAL**: This document contains all operational knowledge for the Medical GraphRAG Assistant.
Keep this updated when infrastructure changes!

## Quick Reference

### EC2 Instance
| Field | Value |
|-------|-------|
| **Instance ID** | `i-0fee5f32e867e65c1` |
| **Public IP** | `44.200.206.67` (check if changed after stop/start) |
| **Region** | `us-east-1` |
| **SSH Key** | `~/.ssh/fhir-ai-key-recovery.pem` |
| **SSH Command** | `ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67` |

### Ports
| Service | Port | Description |
|---------|------|-------------|
| IRIS SQL | 1972 | Database connections |
| IRIS Web | 52773 | Management Portal |
| NV-CLIP | 8002 | Image embeddings API |
| Streamlit | 8501 | Chat UI |

### SSH Tunnels (for local development)
```bash
# All-in-one tunnel for local dev
ssh -i ~/.ssh/fhir-ai-key-recovery.pem -L 1972:localhost:1972 -L 52773:localhost:52773 -L 8002:localhost:8002 ubuntu@44.200.206.67

# Individual tunnels
ssh -i ~/.ssh/fhir-ai-key-recovery.pem -L 1972:localhost:1972 ubuntu@44.200.206.67  # IRIS SQL
ssh -i ~/.ssh/fhir-ai-key-recovery.pem -L 8002:localhost:8002 ubuntu@44.200.206.67  # NV-CLIP
```

### Docker Containers on EC2
| Container | Image | Purpose |
|-----------|-------|---------|
| `iris-fhir` | `intersystemsdc/irishealth-community:latest` | IRIS database |
| `nim-nvclip` | `nvcr.io/nim/nvidia/nvclip:1.0.0` | Image embeddings |

### IRIS Connection Details
```python
# Python connection
host = "44.200.206.67"  # or localhost with tunnel
port = 1972
namespace = "USER"
username = "_SYSTEM"
password = "SYS"
```

---

## Common Operations

### Check EC2 Status
```bash
# Check if instance is running
aws ec2 describe-instances --instance-ids i-0fee5f32e867e65c1 \
  --query 'Reservations[0].Instances[0].[State.Name,PublicIpAddress]' \
  --output text --profile PowerUserPlusAccess-122293094970

# Start instance if stopped
aws ec2 start-instances --instance-ids i-0fee5f32e867e65c1 \
  --profile PowerUserPlusAccess-122293094970
```

### Check Services on EC2
```bash
# SSH and check Docker
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker ps'

# Check IRIS instance
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker exec iris-fhir iris list'

# Query tables
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 \
  'docker exec iris-fhir bash -c "echo \"SELECT COUNT(*) FROM SQLUser.ClinicalNoteVectors\" | iris sql IRIS"'
```

### Initialize Database Schema
```bash
# Run from local machine (requires SSH tunnel or direct connection)
cd /Users/tdyar/ws/medical-graphrag-assistant
EC2_HOST=44.200.206.67 python scripts/aws/setup-iris-schema.py

# Or via CLI
python -m src.cli fix-environment --env aws
```

### Run E2E Tests Against EC2
```bash
# Set environment variables
export IRIS_HOST=44.200.206.67
export IRIS_PORT=1972
export IRIS_NAMESPACE=USER
export IRIS_USERNAME=_SYSTEM
export IRIS_PASSWORD=SYS
export FHIR_BASE_URL=http://44.200.206.67:52773/fhir/r4

# Or with SSH tunnel (preferred for security)
# Terminal 1: Start tunnel
ssh -i ~/.ssh/fhir-ai-key-recovery.pem -L 1972:localhost:1972 -L 52773:localhost:52773 ubuntu@44.200.206.67

# Terminal 2: Run tests
export IRIS_HOST=localhost
export FHIR_BASE_URL=http://localhost:52773/fhir/r4
pytest tests/e2e/ -v
```

---

## Database Schema Setup

### Required Tables
The following tables must exist in `SQLUser` schema:

1. **ClinicalNoteVectors** - FHIR clinical documents with embeddings
2. **MIMICCXRImages** (or MedicalImageVectors) - Medical images with NV-CLIP embeddings
3. **Entities** - Knowledge graph entities
4. **EntityRelationships** - Knowledge graph relationships
5. **AgentMemoryVectors** - Agent semantic memory

### Create Tables SQL
```sql
-- ClinicalNoteVectors
CREATE TABLE IF NOT EXISTS SQLUser.ClinicalNoteVectors (
    ID INT IDENTITY PRIMARY KEY,
    ResourceID VARCHAR(255) UNIQUE,
    PatientID VARCHAR(255),
    DocumentType VARCHAR(255),
    TextContent TEXT,
    SourceBundle VARCHAR(500),
    Embedding VECTOR(DOUBLE, 1024),
    EmbeddingModel VARCHAR(100),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Entities
CREATE TABLE IF NOT EXISTS SQLUser.Entities (
    ID INT IDENTITY PRIMARY KEY,
    EntityText VARCHAR(500),
    EntityType VARCHAR(100),
    Confidence DOUBLE,
    SourceDocID VARCHAR(255)
);

-- EntityRelationships
CREATE TABLE IF NOT EXISTS SQLUser.EntityRelationships (
    ID INT IDENTITY PRIMARY KEY,
    SourceEntityID INT,
    TargetEntityID INT,
    RelationType VARCHAR(100),
    Confidence DOUBLE,
    SourceText VARCHAR(500),
    TargetText VARCHAR(500)
);

-- AgentMemoryVectors
CREATE TABLE IF NOT EXISTS SQLUser.AgentMemoryVectors (
    ID INT IDENTITY PRIMARY KEY,
    MemoryType VARCHAR(50),
    Content TEXT,
    Embedding VECTOR(DOUBLE, 1024),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MedicalImageVectors
CREATE TABLE IF NOT EXISTS SQLUser.MedicalImageVectors (
    ID INT IDENTITY PRIMARY KEY,
    ImageID VARCHAR(255) UNIQUE,
    PatientID VARCHAR(255),
    StudyType VARCHAR(255),
    ImagePath VARCHAR(1000),
    Embedding VECTOR(DOUBLE, 1024),
    RelatedReportID VARCHAR(255)
);
```

---

## Troubleshooting

### SSH Permission Denied
```bash
# Fix key permissions
chmod 600 ~/.ssh/fhir-ai-key-recovery.pem
```

### IRIS Tables Not Found
```bash
# Check what tables exist
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 \
  'docker exec iris-fhir bash -c "echo \"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '"'"'SQLUser'"'"'\" | iris sql IRIS"'

# Re-run schema setup
python -m src.cli fix-environment
```

### NV-CLIP Not Responding
```bash
# Check container status
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker logs nim-nvclip --tail 20'

# Restart if needed
ssh -i ~/.ssh/fhir-ai-key-recovery.pem ubuntu@44.200.206.67 'docker restart nim-nvclip'
```

### EC2 IP Changed After Restart
```bash
# Get new public IP
aws ec2 describe-instances --instance-ids i-0fee5f32e867e65c1 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text --profile PowerUserPlusAccess-122293094970

# Update AGENTS.md with new IP
```

---

## Test Environment Configuration

### pytest.ini / conftest.py settings
Tests should auto-detect EC2 environment. Key environment variables:

```bash
# Required for e2e tests
IRIS_HOST=44.200.206.67      # EC2 IP or localhost with tunnel
IRIS_PORT=1972
IRIS_NAMESPACE=USER
IRIS_USERNAME=_SYSTEM
IRIS_PASSWORD=SYS
NVCLIP_BASE_URL=http://44.200.206.67:8002/v1  # or localhost:8002 with tunnel

# Optional - FHIR REST API (if enabled)
FHIR_BASE_URL=http://44.200.206.67:52773/fhir/r4
```

---

## Last Updated
- **Date**: 2026-01-18
- **EC2 IP Verified**: 44.200.206.67
- **Tables Status**: READY (8 tables created)

### Current Tables on EC2
| Schema | Table | Status |
|--------|-------|--------|
| SQLUser | AgentMemoryVectors | Created |
| SQLUser | ClinicalNoteVectors | Created |
| SQLUser | Entities | Created |
| SQLUser | EntityRelationships | Created |
| SQLUser | MedicalImageVectors | Created |
| SQLUser | PatientImageMapping | Created |
| SQLUser | TestClinicalNoteVectors | Created (test) |
| VectorSearch | PatientImageMapping | Created |

### Test Results (2026-01-18)
```
213 passed, 7 failed, 44 skipped
```
All tests run against live EC2 IRIS - NO MOCKS.
