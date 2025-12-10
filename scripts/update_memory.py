#!/usr/bin/env python3
"""Update memory with clearer instruction for knowledge graph visualization."""
import sys
sys.path.insert(0, '/home/ubuntu/medical-graphrag-assistant')

from src.memory import VectorMemory

mem = VectorMemory()

# Find and delete the old correction
results = mem.recall("knowledge graph", memory_type="correction", top_k=5)
for r in results:
    if "graph plot" in r["text"].lower():
        print(f"Deleting: {r['text']}")
        mem.forget(memory_id=r["memory_id"])

# Add clearer correction
new_text = "IMPORTANT: For queries like 'what is in the knowledge graph?' - ALWAYS use plot_entity_network tool to show a network visualization with nodes and edges. Do NOT use plot_entity_distribution (bar chart)."
mem_id = mem.remember("correction", new_text, {"source": "user_correction"})
print(f"Added new memory: {mem_id}")
print(f"New text: {new_text}")
