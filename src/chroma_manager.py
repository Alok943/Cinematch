import chromadb
import streamlit as st
import os

# --- PATH CONFIGURATION ---
# We check multiple possible locations for the database
POSSIBLE_PATHS = [
    "../data/chroma",       # Correct structure: running from src/
    "./data/chroma",        # Running from root
    "../chroma_db",         # Legacy location
    "./chroma_db"           # Legacy location
]

CHROMA_PATH = None
for path in POSSIBLE_PATHS:
    if os.path.exists(path):
        CHROMA_PATH = path
        break

# Fallback for error messaging
if CHROMA_PATH is None:
    CHROMA_PATH = "../data/chroma"

COLLECTION_NAME = "cine_match_v1" 

@st.cache_resource
def get_client():
    if not os.path.exists(CHROMA_PATH):
        return None
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_collection():
    client = get_client()
    if client is None:
        return None
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"Error fetching collection: {e}")
        return None

def validate_database():
    if not os.path.exists(CHROMA_PATH):
        return False, f"Database folder not found. Searched at: {CHROMA_PATH}"
    
    collection = get_collection()
    if collection is None:
        return False, f"Collection '{COLLECTION_NAME}' not found inside {CHROMA_PATH}."
        
    count = collection.count()
    if count == 0:
        return False, "Collection exists but is empty."
        
    return True, f"Connected to ChromaDB at {CHROMA_PATH}. Index contains {count:,} movies."

def get_collection_stats():
    collection = get_collection()
    if not collection:
        return {"count": 0}
    return {"count": collection.count()}