import chromadb
import streamlit as st
import os

# --- PATH CONFIGURATION ---
# ./chroma_db is FIRST — that's where app.py downloads the DB on Streamlit Cloud
POSSIBLE_PATHS = [
    "./chroma_db",
    "./data/chroma",
    "../data/chroma",
    "../chroma_db",
]

COLLECTION_NAME = "cine_match_v1"


def _resolve_chroma_path():
    """
    Resolves path at CALL TIME, not import time.
    Critical because DB may be downloaded after this module loads.
    """
    for path in POSSIBLE_PATHS:
        if os.path.exists(path):
            return path
    return "./chroma_db"  # fallback matches download location in app.py


@st.cache_resource
def get_client():
    path = _resolve_chroma_path()
    if not os.path.exists(path):
        print(f"ChromaDB path not found: {path}")
        return None
    print(f"ChromaDB connecting at: {path}")
    return chromadb.PersistentClient(path=path)


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
    path = _resolve_chroma_path()
    if not os.path.exists(path):
        return False, f"Database folder not found. Searched: {POSSIBLE_PATHS}"

    collection = get_collection()
    if collection is None:
        return False, f"Collection '{COLLECTION_NAME}' not found inside {path}."

    count = collection.count()
    if count == 0:
        return False, "Collection exists but is empty."

    return True, f"Connected to ChromaDB at {path}. Index contains {count:,} movies."


def get_collection_stats():
    collection = get_collection()
    if not collection:
        return {"count": 0}
    return {"count": collection.count()}


def get_movie_by_id(movie_id: str):
    try:
        collection = get_collection()
        if not collection:
            return None

        result = collection.get(
            ids=[str(movie_id)],
            include=["metadatas"]
        )

        if result['ids'] and len(result['ids']) > 0:
            return result['metadatas'][0]
        return None

    except Exception as e:
        print(f"Error fetching movie {movie_id}: {e}")
        return None