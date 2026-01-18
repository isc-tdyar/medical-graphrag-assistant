# Solution: Connecting to Remote IRIS via DBAPI

**Category:** environment-setup
**Date:** 2026-01-18
**Project:** medical-graphrag-assistant

## Problem Symptom
Code using the `intersystems-irispython` driver (DBAPI) failed to connect or query remote IRIS instances on EC2. Errors included "instance not found" or authentication failures, despite the instance being up.

## Root Cause Analysis
1. **Namespace mismatch**: The EC2 instance was configured with a specific `DEMO` namespace for FHIR data, but the code defaulted to `USER` or `%SYS`.
2. **Legacy API usage**: Some scripts attempted to use the "Native SDK" (`iris.createIRIS()`), which is often not available in standard Python environments unless specific binary extensions are compiled and installed.
3. **Inconsistent hostnames**: Environment variables like `IRIS_HOST` were defaulting to `localhost`, causing failures when running outside of the EC2 instance without an SSH tunnel.

## Investigation Steps
1. Use `nc -zv [IP] 1972` to verify the SQL port is open.
2. Check namespaces on EC2: `docker exec iris-fhir iris list`.
3. Verify table locations: `SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES`.
4. Discovered that `DEMO` is the primary namespace for this application's data.

## Working Solution
1. **Standardize DBAPI**: Always use `DatabaseConnection.get_connection()` from `src.db.connection`.
2. **Centralize Fallbacks**: Update `tests/conftest.py` and `rag_pipeline.py` to use `44.200.206.67` as the default fallback for `IRIS_HOST`.
3. **Use the correct Namespace**: Explicitly set `IRIS_NAMESPACE=DEMO` in the environment or as a fallback.
4. **Remove Native SDK dependencies**: Replace `iris.createIRIS(conn)` with standard DBAPI cursor patterns:
   ```python
   cursor = conn.cursor()
   cursor.execute("SELECT ...")
   ```

## Prevention Strategies
- **Health Check CLI**: Run `python -m src.cli --env aws check-health` before every development session.
- **Unified config**: Use a single YAML or environment profile for all database connection parameters.
- **Schema verification**: Ensure `fix-environment` command is run against the correct namespace.

## Cross-references
- `OPS.md`
- `tests/conftest.py`
- `src/db/connection.py`
- Sprint: `012-fix-test-failures`
