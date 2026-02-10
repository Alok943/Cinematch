import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
import os

# Get the folder where this script lives (src)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go UP one level ("..") to find the file in the project root
# Adjust this path if your folder structure is different
DATA_PATH = r"C:\Users\aloks\Desktop\Cinematch_V2\data\processed\movies_merged.csv"
# DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "processed", "movies_merged.csv")

# --- CONFIGURATION ---
COLLECTION_NAME = "cine_match_v1"
PERSIST_DIR = "./chroma_db"

# 1. Standard TMDB Genre Map (ID -> Name)
GENRE_ID_TO_NAME = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

# 2. Reverse Map (Name -> ID)
GENRE_NAME_TO_ID = {v.lower(): k for k, v in GENRE_ID_TO_NAME.items()}

# --- HELPER FUNCTIONS ---

def clean_text(text):
    """
    Cleans text fields and handles 'nan' string literals.
    """
    if pd.isna(text): return ""
    s = str(text).strip()
    return "" if s.lower() == "nan" else s

def safe_get_genre_ids(x):
    """
    Robustly parses genre strings like "Action, Adventure".
    """
    if pd.isna(x) or x == "":
        return []
    
    text_val = str(x).strip().lower()
    if text_val == "nan":
        return []

    ids = []
    parts = text_val.split(",")
    for p in parts:
        clean_name = p.strip()
        if clean_name in GENRE_NAME_TO_ID:
            ids.append(GENRE_NAME_TO_ID[clean_name])
            
    return ids

def generate_super_string(row):
    """
    Constructs the weighted string for embedding.
    ORDER MATTERS: Title (x2) -> Genres -> Keywords -> Overview
    """
    return (
        f"Title: {row['title']}. Title: {row['title']}. "
        f"Genres: {row['genres_display']}. "
        f"Keywords: {row['keywords']}. "
        f"Tagline: {row['tagline']}. "
        f"Overview: {row['overview']}"
    )

def clean_and_prepare_data(csv_path):
    print("🧹 Loading and cleaning data...")
    if not os.path.exists(csv_path):
        print(f"❌ Error: File not found at {csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path, low_memory=False)
    
    # --- A. CRITICAL ID CLEANING ---
    df = df.dropna(subset=['id'])
    df['id'] = df['id'].astype(int)
    df = df.drop_duplicates(subset=['id'])
    
    # --- B. TEXT CLEANING ---
    df['title'] = df['title'].apply(clean_text)
    df.loc[df['title'] == "", 'title'] = "Unknown Title"
    
    df['overview'] = df['overview'].apply(clean_text)
    df['tagline'] = df['tagline'].apply(clean_text)
    df['keywords'] = df['keywords'].apply(clean_text)
    df['genres_display'] = df['genres'].apply(clean_text)
    
    if 'poster_path' in df.columns:
        df['poster_path'] = df['poster_path'].apply(clean_text)
    else:
        df['poster_path'] = ""

    # --- C. NUMERICS ---
    df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce').fillna(0.0)
    df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce').fillna(0).astype(int)
    
    # --- D. DATES ---
    if 'release_date' in df.columns:
        df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
        df['release_year'] = df['release_date'].dt.year.fillna(0).astype(int)
    else:
        df['release_year'] = 0

    # --- E. ADULT CONTENT ---
    if 'adult' in df.columns:
        df['adult'] = df['adult'].astype(str).str.lower() == 'true'
    else:
        df['adult'] = False

    print("   - Parsing genres...")
    df['genre_ids'] = df['genres'].apply(safe_get_genre_ids)

    print(f"✅ Cleaned data: {len(df)} unique movies ready.")
    return df

def build_vector_store():
    # A. Initialize Client
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # --- UPDATED LOGIC START ---
    # We do NOT delete the collection anymore. 
    # We use get_or_create_collection to attach to the existing one.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"}
    )
    
    current_count = collection.count()
    print(f"📂 Connected to '{COLLECTION_NAME}'. Current movie count: {current_count}")
    # --- UPDATED LOGIC END ---

    # B. Prep Data
    df = clean_and_prepare_data(DATA_PATH)
    if df.empty:
        return
    
    # C. Batch Processing
    batch_size = 500
    total_movies = len(df)
    print(f"🚀 Starting UPSERT (Merge/Update) of {total_movies} movies...")

    for i in range(0, total_movies, batch_size):
        batch = df.iloc[i : i + batch_size]
        
        ids = []
        documents = []
        metadatas = []

        for _, row in batch.iterrows():
            movie_id = str(row['id'])
            doc_text = generate_super_string(row)
            
            # --- METADATA PAYLOAD ---
            meta = {
                "movie_id": int(row['id']),
                "title": str(row['title']),
                "release_year": int(row['release_year']),
                "vote_average": float(row['vote_average']),
                "vote_count": int(row['vote_count']),
                "poster_path": str(row['poster_path']),
                "genres_display": str(row['genres_display']),
                "overview": str(row['overview']),
                "tagline": str(row['tagline']),
                "adult": bool(row['adult']) 
            }
            
            # --- ONE-HOT ENCODING ---
            current_genre_ids = row['genre_ids']
            for genre_id in GENRE_ID_TO_NAME.keys():
                meta[f"genre_{genre_id}"] = (genre_id in current_genre_ids)

            ids.append(movie_id)
            documents.append(doc_text)
            metadatas.append(meta)

        # --- UPDATED LOGIC: UPSERT ---
        # upsert() will update existing IDs and insert new IDs.
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"   - Synced batch {i} to {i+len(batch)} (Upserted)")

    final_count = collection.count()
    print(f"✅ DONE! Collection '{COLLECTION_NAME}' is now up to date.")
    print(f"📊 Total movies in database: {final_count} (Added/Updated: {final_count - current_count} new entries net change)")

if __name__ == "__main__":
    build_vector_store()