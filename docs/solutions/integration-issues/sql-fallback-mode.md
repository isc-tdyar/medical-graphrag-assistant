# Solution: SQL Fallback Mode for Missing FHIR REST API

**Category:** integration-issues
**Date:** 2026-01-18
**Project:** medical-graphrag-assistant

## Problem Symptom
E2E tests for radiology tools (e.g., `get_patient_imaging_studies`) were skipping or failing with 404 errors when running against the EC2 IRIS instance. This was because the standard InterSystems HealthShare FHIR REST API was not configured or licensed on that specific instance.

## Root Cause Analysis
The application architecture assumed a standard FHIR REST repository (`/fhir/r4`) would always be available. In the cloud/spot-instance environment, IRIS was running as a standard SQL/Vector database without the HealthShare extensions enabled. The data (Medical Images, Clinical Notes) was stored in standard SQL tables (`SQLUser.*`, `VectorSearch.*`), but the MCP tools were only designed to call the REST endpoint.

## Investigation Steps
1. SSH into EC2 and check running containers: `docker ps`.
2. Attempt to curl the FHIR metadata endpoint: `curl http://localhost:52773/csp/healthshare/demo/fhir/r4/metadata`.
3. Check IRIS tables directly via SQL shell: `SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES`.
4. Discovered that while FHIR resources weren't in the standard repo, they were present in custom SQL tables like `SQLUser.MedicalImageVectors`.

## Working Solution
Implemented a **SQL Fallback Mode** in the adapter layer (`src/adapters/fhir_radiology_adapter.py`):
1. Create an `_is_fhir_available()` check that pings the metadata endpoint.
2. In each search method, try the FHIR REST API first.
3. If REST fails, fallback to a standard SQL query against the verified `SQLUser` tables.
4. **CRITICAL**: Transform the raw SQL rows into valid **FHIR R4 JSON** structures (e.g., `ImagingStudy`, `DiagnosticReport`) before returning.
5. Update MCP tools to use these adapter methods instead of making direct HTTP calls.

## Prevention Strategies
- **Graceful Degradation**: Always design adapters with multiple data source strategies (REST -> SQL -> Cache -> Demo).
- **Schema-first Adapters**: Ensure the output of an adapter is always schema-compliant (FHIR R4 in this case) regardless of the input source (SQL or REST).
- **Environment Detection**: Use `conftest.py` to auto-detect the environment capabilities and skip REST-only tests when necessary.

## Cross-references
- `src/adapters/fhir_radiology_adapter.py`
- `mcp-server/fhir_graphrag_mcp_server.py`
- Sprint: `012-fix-test-failures`
