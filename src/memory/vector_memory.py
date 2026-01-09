#!/usr/bin/env python3
"""
Pure IRIS Vector Memory System - Agent learning with semantic search

Stores agent memories as vector embeddings in IRIS for semantic retrieval:
- User corrections and domain knowledge
- User preferences and feedback
- Query history and successful patterns

100% IRIS - No SQLite, just clean vector search.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection


class VectorMemory:
    """Pure IRIS vector-based semantic memory for agent learning."""

    def __init__(self, embedding_model=None):
        """
        Initialize vector memory system.

        Args:
            embedding_model: Optional embedding model (defaults to NVCLIPEmbeddings for text)
        """
        self.embedding_model = embedding_model
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create AgentMemoryVectors table if it doesn't exist."""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'SQLUser' AND TABLE_NAME = 'AgentMemoryVectors'
            """)
            exists = cursor.fetchone()[0] > 0

            if not exists:
                # Create table - pure vector design like MedicalImageVectors
                cursor.execute("""
                    CREATE TABLE SQLUser.AgentMemoryVectors (
                        MemoryID VARCHAR(255) PRIMARY KEY,
                        MemoryType VARCHAR(50) NOT NULL,
                        MemoryText VARCHAR(4000) NOT NULL,
                        Embedding VECTOR(DOUBLE, 1024),
                        Metadata VARCHAR(4000),
                        UseCount INT DEFAULT 1,
                        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        LastUsedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("✅ Created AgentMemoryVectors table in IRIS", file=sys.stderr)
        finally:
            cursor.close()
            conn.close()

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get NV-CLIP text embedding.

        Args:
            text: Text to embed

        Returns:
            1024-dim embedding vector
        """
        if self.embedding_model is None:
            # Lazy load NV-CLIP using configuration
            try:
                from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
                from src.search.base import BaseSearchService
                
                # Get base URL from config
                base_service = BaseSearchService()
                nvclip_config = base_service.config.get('nvclip', {})
                base_url = nvclip_config.get('base_url')
                
                if base_url:
                    print(f"VectorMemory: Initializing NV-CLIP with base_url: {base_url}", file=sys.stderr)
                    self.embedding_model = NVCLIPEmbeddings(base_url=base_url)
                else:
                    self.embedding_model = NVCLIPEmbeddings()
    except Exception as e:
        import sys
        print(f"Error recalling memories: {e}", file=sys.stderr)
        return ""


        # Format as context prompt
        lines = ["# Agent Memory Context\n"]

        for mem in memories:
            mem_type = mem.get('memory_type', 'unknown')
            text = mem.get('text', '')
            use_count = mem.get('use_count', 0)
            similarity = mem.get('similarity')

            lines.append(f"## {mem_type.title()}")
            lines.append(f"{text}")
            if similarity:
                lines.append(f"*(Relevance: {similarity:.2f}, Used {use_count}x)*")
            else:
                lines.append(f"*(Used {use_count}x)*")
            lines.append("")

        return "\n".join(lines)


# Convenience functions for common operations

def remember_correction(correction_text: str, context: Dict = None) -> str:
    """Remember a user correction with vector embedding."""
    memory = VectorMemory()
    return memory.remember('correction', correction_text, context)

def remember_knowledge(knowledge_text: str, context: Dict = None) -> str:
    """Remember domain knowledge with vector embedding."""
    memory = VectorMemory()
    return memory.remember('knowledge', knowledge_text, context)

def remember_preference(preference_text: str, context: Dict = None) -> str:
    """Remember user preference with vector embedding."""
    memory = VectorMemory()
    return memory.remember('preference', preference_text, context)

def recall_similar(query: str, memory_type: str = None, top_k: int = 5) -> List[Dict]:
    """Recall memories semantically similar to query."""
    memory = VectorMemory()
    return memory.recall(query, memory_type, top_k)


if __name__ == '__main__':
    # Demo/test
    print("🧠 Pure IRIS Vector Memory System Demo\n" + "="*60)

    memory = VectorMemory()

    # Store example memories
    print("\n📝 Storing memories with NV-CLIP embeddings...")

    remember_correction(
        "Pneumonia appears as consolidation (white/opaque areas) on chest X-ray, typically in lung bases",
        context={'source': 'user_feedback', 'date': '2025-01-15'}
    )

    remember_knowledge(
        "Cardiomegaly means enlarged heart, visible as increased cardiac silhouette on frontal chest X-ray",
        context={'source': 'medical_reference'}
    )

    remember_preference(
        "User prefers semantic search over keyword search for medical images",
        context={'confidence': 0.9}
    )

    # Test semantic vector search
    print("\n🔍 Testing semantic vector recall...")

    print("\n1. Query: 'What does pneumonia look like on X-ray?'")
    results = recall_similar("What does pneumonia look like on X-ray?", top_k=3)
    for r in results:
        print(f"   [{r['memory_type']}] Similarity: {r['similarity']:.3f}")
        print(f"   {r['text'][:80]}...")

    print("\n2. Query: 'enlarged heart findings'")
    results = recall_similar("enlarged heart findings", top_k=3)
    for r in results:
        print(f"   [{r['memory_type']}] Similarity: {r['similarity']:.3f}")
        print(f"   {r['text'][:80]}...")

    print("\n3. Query: 'user search preferences'")
    results = recall_similar("user search preferences", top_k=3)
    for r in results:
        print(f"   [{r['memory_type']}] Similarity: {r['similarity']:.3f}")
        print(f"   {r['text'][:80]}...")

    # Stats
    print("\n📊 Memory Statistics:")
    stats = memory.get_stats()
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   By type: {stats['type_breakdown']}")

    # Context prompt
    print("\n📝 Context Prompt for 'chest x-ray findings':")
    context = memory.get_context_prompt("chest x-ray findings", max_memories=2)
    print(context)

    print("\n✅ Demo complete - Pure IRIS vector memory working!")
