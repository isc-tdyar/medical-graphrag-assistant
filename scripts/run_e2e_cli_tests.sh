#!/bin/bash
# scripts/run_e2e_cli_tests.sh
# Runs a suite of E2E tests via the CLI chat tool to verify search functionality and tool usage.

echo "======================================================================"
echo "Medical GraphRAG E2E CLI Verification"
echo "======================================================================"

# Set environment
source ~/medical-graphrag/venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
export CONFIG_PATH=config/fhir_graphrag_config.aws.yaml

# Test 1: FHIR / Hybrid Search
echo -e "\n[TEST 1] FHIR / Hybrid Search Verification"
python3 -m src.cli chat "Find patients with cough" --quiet | grep -A 5 "Assistant:"

# Test 2: Knowledge Graph Search
echo -e "\n[TEST 2] Knowledge Graph Verification"
python3 -m src.cli chat "What medications treat hypertension?" --quiet | grep -A 5 "Assistant:"

# Test 3: Medical Image Search
echo -e "\n[TEST 3] Medical Image Search Verification"
python3 -m src.cli chat "Show me chest X-rays of pneumonia" --quiet | grep -A 5 "Assistant:"

# Test 4: Complex Multi-Tool Query
echo -e "\n[TEST 4] Complex Multi-Tool Logic"
# This should trigger multiple tool calls (FHIR + KG)
python3 -m src.cli chat "what patients have allergies or radiology images" --quiet | grep -A 10 "Assistant:"

echo -e "\n======================================================================"
echo "Verification Complete"
echo "======================================================================"
