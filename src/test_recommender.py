import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import time

# --- CONFIGURATION ---
# This must match your build_vector.py settings
PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "cine_match_v1"

# The Full "Night 4" Test List
test_movies = [
    # Nolan / Mind-Bending
    "The Dark Knight", "Inception", "Interstellar", "Tenet", "The Prestige",
    # MCU
    "Avengers: Endgame", "Iron Man", "Captain America: Civil War", "Spider-Man: No Way Home", "Doctor Strange",
    # Dinos / Monsters
    "Jurassic Park", "The Lost World: Jurassic Park", "Jurassic World", "King Kong", "Godzilla",
    # Epics
    "Titanic", "Avatar", "Avatar: The Way of Water", "Gladiator", "Braveheart",
    # Crime / Mafia
    "The Godfather", "The Godfather Part II", "Goodfellas", "Scarface", "Casino",
    # Tarantino
    "Pulp Fiction", "Reservoir Dogs", "Django Unchained", "Inglourious Basterds", "Kill Bill: Vol. 1",
    # Cyberpunk / Sci-Fi
    "The Matrix", "The Matrix Reloaded", "The Matrix Resurrections", "Blade Runner 2049", "Ex Machina",
    # Cerebral Sci-Fi
    "Arrival", "Annihilation", "Moon", "Her", "Under the Skin",
    # Thriller
    "Se7en", "Zodiac", "Prisoners", "Gone Girl", "Shutter Island",
    # Horror
    "The Conjuring", "Insidious", "Hereditary", "The Nun", "Get Out",
    # Animation
    "Toy Story", "Finding Nemo", "Inside Out", "Coco", "Spider-Man: Into the Spider-Verse",
    # Anime
    "Spirited Away", "Howl’s Moving Castle", "Your Name", "Akira", "Ghost in the Shell",
    # Korean
    "Parasite", "Oldboy", "Train to Busan", "Memories of Murder", "The Handmaiden",
    # Indian
    "RRR", "Baahubali: The Beginning", "Baahubali: The Conclusion", "Dangal", "3 Idiots",
    # Romance
    "La La Land", "The Notebook", "A Star Is Born", "Before Sunrise", "Pride & Prejudice",
    # Action
    "Mad Max: Fury Road", "John Wick", "Die Hard", "Mission: Impossible – Fallout", "Top Gun: Maverick",
    # Indie / A24
    "The Lighthouse", "Midsommar", "The Florida Project", "Swiss Army Man", "Synecdoche, New York"
]

def run_pipeline_test():
    print(f"🔌 Connecting to Real ChromaDB at: {PERSIST_DIR}...")
    
    # 1. Initialize Client
    try:
        client = chromadb.PersistentClient(path=PERSIST_DIR)
        embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        print(f"✅ Collection '{COLLECTION_NAME}' loaded successfully.")
        print(f"📊 Database contains {collection.count()} items.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not load DB. \n{e}")
        return

    print("\n🚀 STARTING 100-MOVIE BATCH TEST")
    print("=" * 120)
    print(f"{'INPUT MOVIE':<35} | {'REAL DATABASE RESULTS (Top 8)'}")
    print("-" * 120)

    # 2. Loop through the list
    for query_movie in test_movies:
        
        # We fetch 9 results: The input movie itself (usually #1) + 8 recommendations
        results = collection.query(
            query_texts=[query_movie],
            n_results=9,
            where={"adult": False} 
        )
        
        # 3. Process Results
        # Chroma returns a list of lists. We grab the first (and only) list.
        found_titles = []
        
        # Extract titles from metadata
        # results['metadatas'][0] is a list of dictionaries for the matches
        if results['metadatas'] and len(results['metadatas'][0]) > 0:
            for item in results['metadatas'][0]:
                title = item.get('title', 'Unknown')
                found_titles.append(title)
        
        # 4. Clean the Output
        # If the first result is the movie itself (Exact Match), remove it to show only recommendations.
        # If the search was fuzzy and didn't find the exact movie first, we just show what it found.
        
        # Normalize for case-insensitive comparison
        query_norm = query_movie.lower()
        if found_titles and found_titles[0].lower() == query_norm:
            recs = found_titles[1:] # Skip the first one
        else:
            recs = found_titles[:8] # Just take top 8
            
        # Format string
        recs_str = ", ".join(recs)
        
        # Print
        print(f"{query_movie:<35} | {recs_str}")

    print("=" * 120)
    print("🏁 Test Complete.")

if __name__ == "__main__":
    run_pipeline_test()