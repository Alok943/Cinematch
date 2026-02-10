import chromadb
import streamlit as st
import os

# --- PATH CONFIGURATION ---
POSSIBLE_PATHS = [
    "../data/chroma",       # Standard structure
    "./data/chroma",        # Root execution
    "../chroma_db",         # Legacy
    "./chroma_db"           # Legacy
]

CHROMA_PATH = None
for path in POSSIBLE_PATHS:
    if os.path.exists(path):
        CHROMA_PATH = path
        break

# Fallback
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

# --- FIXED FUNCTION ---
def get_movie_by_id(movie_id: str):
    """
    Retrieve a single movie's metadata by its ID.
    Returns the metadata dict or None if not found.
    """
    try:
        # Use the existing helper function instead of the missing Class
        collection = get_collection()
        if not collection:
            return None

        result = collection.get(
            ids=[str(movie_id)], # Ensure ID is a string
            include=["metadatas"]
        )
        
        if result['ids'] and len(result['ids']) > 0:
            return result['metadatas'][0]
        return None
        
    except Exception as e:
        print(f"Error fetching movie {movie_id}: {e}")
        return None