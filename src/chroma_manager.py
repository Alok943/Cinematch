import chromadb
import streamlit as st
import os
import requests

COLLECTION_NAME = "cine_match_v1"
HF_URL = "https://huggingface.co/datasets/Alok8732/chroma.sqlite3/resolve/main/chroma.sqlite3"
LOCAL_DIR = "./chroma_db"
LOCAL_FILE = os.path.join(LOCAL_DIR, "chroma.sqlite3")


def _download_db_from_hf():
    """
    Downloads chroma.sqlite3 from HuggingFace Dataset repo
    into ./chroma_db/ if not already present.
    """
    if os.path.exists(LOCAL_FILE):
        print("ChromaDB already exists locally, skipping download.")
        return True

    os.makedirs(LOCAL_DIR, exist_ok=True)

    print("Downloading ChromaDB from HuggingFace...")
    try:
        response = requests.get(HF_URL, stream=True, timeout=120)
        response.raise_for_status()
        with open(LOCAL_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
        return True
    except Exception as e:
        print(f"HF Download failed: {e}")
        return False


@st.cache_resource
def get_client():
    """
    Downloads DB from HF if needed, then connects PersistentClient.
    Cached for the lifetime of the Streamlit session.
    """
    success = _download_db_from_hf()
    if not success:
        print("Could not download ChromaDB. Aborting.")
        return None

    print(f"ChromaDB connecting at: {LOCAL_DIR}")
    return chromadb.PersistentClient(path=LOCAL_DIR)


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
    if not os.path.exists(LOCAL_FILE):
        return False, f"Database file not found at {LOCAL_FILE}"

    collection = get_collection()
    if collection is None:
        return False, f"Collection '{COLLECTION_NAME}' not found."

    count = collection.count()
    if count == 0:
        return False, "Collection exists but is empty."

    return True, f"Connected to ChromaDB at {LOCAL_DIR}. Index contains {count:,} movies."


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