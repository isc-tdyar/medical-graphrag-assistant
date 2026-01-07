"""
Synchronize FHIR native resources to SQLUser.FHIRDocuments search table.
Uses the FHIRDocumentAdapter to extract clinical notes from native IRIS tables.
"""

import os
import sys
import json

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db.connection import get_connection
from src.adapters.fhir_document_adapter import FHIRDocumentAdapter

def sync_documents():
    print("================================================================")
    print("SYNC: FHIR Native -> SQLUser.FHIRDocuments")
    print("================================================================")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Initialize Adapter
    adapter = FHIRDocumentAdapter(conn)
    
    # 2. Load all DocumentReference resources
    print("[INFO] Loading documents from FHIR native tables...")
    documents = adapter.load_fhir_documents()
    
    if not documents:
        print("[WARN] No documents found in FHIR native tables.")
        return
        
    # 3. Clear existing search documents (optional but ensures clean sync for demo)
    print(f"[INFO] Syncing {len(documents)} documents to SQLUser.FHIRDocuments...")
    cursor.execute("DELETE FROM SQLUser.FHIRDocuments")
    
    # 4. Insert into search table
    inserted = 0
    for doc in documents:
        try:
            # Prepare data
            fhir_id = doc['id']
            resource_string = json.dumps(doc['metadata']) # Simple representation
            resource_type = "DocumentReference"
            text_content = doc['text']
            
            # Parameterized insert
            sql = """
                INSERT INTO SQLUser.FHIRDocuments 
                (FHIRResourceId, ResourceString, ResourceType, TextContent)
                VALUES (?, ?, ?, ?)
            """
            cursor.execute(sql, (fhir_id, resource_string, resource_type, text_content))
            inserted += 1
            
            if inserted % 50 == 0:
                print(f"  Synced {inserted} documents...")
                
        except Exception as e:
            print(f"  [ERROR] Failed to sync document {doc['id']}: {e}")
            
    conn.commit()
    print(f"\n[SUCCESS] Successfully synced {inserted} documents.")
    
    # 5. Verify
    cursor.execute("SELECT COUNT(*) FROM SQLUser.FHIRDocuments")
    final_count = cursor.fetchone()[0]
    print(f"[VERIFY] Total records in SQLUser.FHIRDocuments: {final_count}")
    
    adapter.close()
    conn.close()

if __name__ == "__main__":
    sync_documents()
