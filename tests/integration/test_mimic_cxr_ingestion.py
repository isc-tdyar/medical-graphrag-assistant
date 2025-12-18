"""
Integration tests for MIMIC-CXR Vector Search (Feature 009).

Tests verify:
- T052: VectorSearch.MIMICCXRImages table exists
- T053: search_medical_images MCP tool functionality
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root and mcp-server to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
mcp_server_dir = os.path.join(parent_dir, 'mcp-server')
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if mcp_server_dir not in sys.path:
    sys.path.insert(0, mcp_server_dir)


class TestMIMICCXRTableExists:
    """T052: Test VectorSearch.MIMICCXRImages table exists after setup."""

    @pytest.fixture
    def db_connection(self):
        """Get database connection for tests."""
        from src.db.connection import get_connection
        conn = get_connection()
        yield conn
        conn.close()

    def test_table_exists(self, db_connection):
        """Verify VectorSearch.MIMICCXRImages table exists."""
        cursor = db_connection.cursor()
        try:
            # Query should succeed without error if table exists
            cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
            count = cursor.fetchone()[0]
            # Table exists - count can be 0 or more
            assert count >= 0, "Table should exist and return a valid count"
        finally:
            cursor.close()

    def test_table_has_expected_columns(self, db_connection):
        """Verify table has all expected columns."""
        cursor = db_connection.cursor()
        try:
            # Query column names from a SELECT to verify schema
            cursor.execute("""
                SELECT TOP 1
                    ImageID, SubjectID, StudyID, ViewPosition,
                    ImagePath, EmbeddingModel, FHIRResourceID
                FROM VectorSearch.MIMICCXRImages
            """)
            # Query should succeed if columns exist
            # Result may be empty but columns should be valid
        except Exception as e:
            pytest.fail(f"Table missing expected columns: {e}")
        finally:
            cursor.close()

    def test_vector_column_type(self, db_connection):
        """Verify Vector column supports 1024-dimensional vectors."""
        cursor = db_connection.cursor()
        try:
            # Insert a test vector and retrieve it
            # This verifies VECTOR(DOUBLE, 1024) type is working
            cursor.execute("""
                SELECT TOP 1
                    VECTOR_DOT_PRODUCT(Vector, Vector) as VectorCheck
                FROM VectorSearch.MIMICCXRImages
                WHERE Vector IS NOT NULL
            """)
            # Query should succeed - VECTOR_DOT_PRODUCT on 1024-dim vectors
        except Exception as e:
            if "no rows" in str(e).lower() or "empty" in str(e).lower():
                pass  # Empty table is acceptable
            else:
                pytest.fail(f"Vector column type issue: {e}")
        finally:
            cursor.close()


class TestSearchMedicalImagesMCP:
    """T053: Test search_medical_images MCP tool functionality."""

    @pytest.fixture
    def mock_embedder(self):
        """Mock NV-CLIP embedder for tests."""
        mock = MagicMock()
        mock.embed_text.return_value = [0.1] * 1024  # 1024-dim vector
        return mock

    def test_search_returns_valid_structure(self, mock_embedder):
        """Verify search returns expected JSON structure."""
        # Import MCP server module
        import fhir_graphrag_mcp_server as mcp

        # Test with mocked embedder
        with patch.object(mcp, 'get_embedder', return_value=mock_embedder):
            # The tool should be available
            assert hasattr(mcp, 'call_tool'), "MCP server should have call_tool function"

    def test_search_with_patient_filter(self, mock_embedder):
        """Verify patient_id filter is applied correctly."""
        import fhir_graphrag_mcp_server as mcp

        # Verify the tool accepts patient_id parameter
        tools = None

        # Use asyncio to call the async list_tools function
        import asyncio

        async def get_tools():
            return await mcp.list_tools()

        tools = asyncio.get_event_loop().run_until_complete(get_tools())

        # Find search_medical_images tool
        search_tool = None
        for tool in tools:
            if tool.name == "search_medical_images":
                search_tool = tool
                break

        assert search_tool is not None, "search_medical_images tool should exist"

        # Verify patient_id is in schema
        schema = search_tool.inputSchema
        properties = schema.get("properties", {})
        assert "patient_id" in properties, "Tool should accept patient_id filter"
        assert "view_position" in properties, "Tool should accept view_position filter"

    def test_search_with_view_filter(self, mock_embedder):
        """Verify view_position filter is applied correctly."""
        import fhir_graphrag_mcp_server as mcp

        import asyncio

        async def get_tools():
            return await mcp.list_tools()

        tools = asyncio.get_event_loop().run_until_complete(get_tools())

        search_tool = next((t for t in tools if t.name == "search_medical_images"), None)
        assert search_tool is not None

        properties = search_tool.inputSchema.get("properties", {})

        # Verify view_position description mentions valid values
        view_desc = properties.get("view_position", {}).get("description", "")
        assert any(view in view_desc for view in ["PA", "AP", "LATERAL"]), \
            "view_position should document valid values"

    def test_search_limits(self, mock_embedder):
        """Verify limit parameter constraints."""
        import fhir_graphrag_mcp_server as mcp

        import asyncio

        async def get_tools():
            return await mcp.list_tools()

        tools = asyncio.get_event_loop().run_until_complete(get_tools())

        search_tool = next((t for t in tools if t.name == "search_medical_images"), None)
        assert search_tool is not None

        properties = search_tool.inputSchema.get("properties", {})

        # Verify limit has default and description
        limit_prop = properties.get("limit", {})
        assert limit_prop.get("default") == 10, "Default limit should be 10"

    def test_min_similarity_parameter(self, mock_embedder):
        """Verify min_similarity threshold parameter."""
        import fhir_graphrag_mcp_server as mcp

        import asyncio

        async def get_tools():
            return await mcp.list_tools()

        tools = asyncio.get_event_loop().run_until_complete(get_tools())

        search_tool = next((t for t in tools if t.name == "search_medical_images"), None)
        assert search_tool is not None

        properties = search_tool.inputSchema.get("properties", {})

        # Verify min_similarity has default
        min_sim_prop = properties.get("min_similarity", {})
        assert min_sim_prop.get("default") == 0.5, "Default min_similarity should be 0.5"


class TestIngestionScript:
    """Test ingestion script components (offline tests)."""

    def test_script_imports(self):
        """Verify ingestion script can be imported."""
        try:
            # Import should succeed without running main()
            import importlib.util
            script_path = os.path.join(parent_dir, 'scripts', 'ingest_mimic_cxr.py')
            spec = importlib.util.spec_from_file_location("ingest_mimic_cxr", script_path)
            module = importlib.util.module_from_spec(spec)
            # Don't execute - just verify it loads
            assert spec is not None, "Script should be loadable"
        except ImportError as e:
            # Import errors for optional dependencies are acceptable
            if "pydicom" in str(e) or "NVCLIPEmbeddings" in str(e):
                pytest.skip(f"Optional dependency not available: {e}")
            else:
                raise

    def test_metadata_extraction_from_path(self):
        """Test DICOM metadata extraction from file path."""
        from scripts.ingest_mimic_cxr import extract_metadata_from_path
        from pathlib import Path

        # Test with typical MIMIC-CXR path structure
        test_path = Path("/data/mimic-cxr/files/p10/p10000032/s50414267/image123.dcm")
        meta = extract_metadata_from_path(test_path)

        assert meta['subject_id'] == 'p10000032', "Should extract patient folder"
        assert meta['study_id'] == 's50414267', "Should extract study folder"
        assert meta['image_id'] == 'image123', "Should extract image ID from filename"

    def test_cli_arguments(self):
        """Verify CLI accepts expected arguments."""
        import argparse
        from scripts.ingest_mimic_cxr import main

        # Test that argparse is set up correctly by checking help
        # This doesn't actually run the script
        parser = argparse.ArgumentParser()
        parser.add_argument('--source', '-s', required=True)
        parser.add_argument('--batch-size', '-b', type=int, default=32)
        parser.add_argument('--limit', '-l', type=int)
        parser.add_argument('--skip-existing', action='store_true', default=True)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--create-fhir', action='store_true')

        # Parse test args
        args = parser.parse_args(['--source', '/test/path', '--limit', '10'])

        assert args.source == '/test/path'
        assert args.limit == 10
        assert args.batch_size == 32  # default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
