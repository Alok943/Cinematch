import chromadb
from chromadb.utils import embedding_functions
import pandas as pd

# --- CONFIGURATION ---
# MUST match what you used in build_vector.py
PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "cine_match_v1"

def test_search(query_text):
    print(f"\n🔎 Querying for: '{query_text}'...")
    
    # 1. Connect to the existing DB
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    
    # 2. Get the collection
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
    except Exception as e:
        print(f"❌ Error: Could not find collection. Did the build script finish? \n{e}")
        return

    # 3. Search
    results = collection.query(
        query_texts=[query_text],
        n_results=3,
        # SAFE SEARCH: Filter out adult content by default
        where={"adult": False} 
    )

    # 4. Display Results
    # Chroma returns lists of lists (because you can query multiple texts at once)
    # We just want the first list [0]
    for i in range(len(results['ids'][0])):
        title = results['metadatas'][0][i]['title']
        genres = results['metadatas'][0][i]['genres_display']
        dist = results['distances'][0][i] # Lower distance = Better match
        
        print(f"   {i+1}. {title} | Genres: {genres} | Score: {dist:.4f}")

# --- RUN THE TEST ---
if __name__ == "__main__":
    # Test 1: Specific Title (Should be #1 match)
    test_search("Swiss Army Man")
    
    # Test 2: Semantic Concept (No title match)
    test_search("A movie about a robot that falls in love")