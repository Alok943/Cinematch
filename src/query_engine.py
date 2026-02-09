import chromadb
from sentence_transformers import SentenceTransformer
import streamlit as st
from chroma_manager import get_collection
import math

# Load model once and cache it
@st.cache_resource
def load_model():
    return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def _build_where_clause(filters):
    """
    Constructs the ChromaDB metadata filter dict.
    """
    where_conditions = []
    
    # 1. Genres (OR logic)
    if filters.get('genres'):
        if len(filters['genres']) == 1:
            where_conditions.append({f"genre_{filters['genres'][0]}": True})
        else:
            genre_conditions = [{f"genre_{gid}": True} for gid in filters['genres']]
            where_conditions.append({"$or": genre_conditions})

    # 2. Safe Search (Hide Adult)
    if filters.get('safe_search'):
        where_conditions.append({"adult": False})

    # 3. Year Range
    if filters.get('year_range'):
        start_year, end_year = filters['year_range']
        where_conditions.append({"release_year": {"$gte": start_year}})
        where_conditions.append({"release_year": {"$lte": end_year}})

    # 4. Minimum Rating
    if filters.get('min_rating'):
        where_conditions.append({"vote_average": {"$gte": filters['min_rating']}})

    if not where_conditions:
        return None
    elif len(where_conditions) == 1:
        return where_conditions[0]
    else:
        return {"$and": where_conditions}

def _fetch_popular_movies(filters, n_results):
    """
    FALLBACK: When no text query is provided, fetch movies based on filters 
    and sort by popularity (vote_count).
    """
    collection = get_collection()
    if not collection: return []
    
    where_clause = _build_where_clause(filters)
    
    # We fetch a larger batch to ensure we get the *most* popular ones 
    # within the filtered subset.
    try:
        results = collection.get(
            where=where_clause,
            limit=1000, # Fetch up to 1k candidates
            include=['metadatas']
        )
        
        processed = []
        metadatas = results['metadatas']
        
        for meta in metadatas:
            processed.append({
                "id": meta.get('movie_id'), # stored as int in metadata
                "title": meta.get('title'),
                "poster_path": meta.get('poster_path'),
                "overview": meta.get('overview'),
                "tagline": meta.get('tagline', ''),
                "release_year": int(meta.get('release_year', 0)),
                "genres": meta.get('genres_display', "Unknown"),
                "vote_average": round(meta.get('vote_average', 0), 1),
                "vote_count": meta.get('vote_count', 0),
                "score": 0.0, # No semantic score
                "match_percentage": 0
            })
            
        # Sort by popularity (vote_count) descending
        processed.sort(key=lambda x: x['vote_count'], reverse=True)
        return processed[:n_results]
        
    except Exception as e:
        print(f"Popular Fetch Error: {e}")
        return []

def search_movies(query, filters=None, boost_weight=0.0, sort_by="relevance", n_results=20):
    """
    Main search entry point. Handles both Semantic Search and Empty Query cases.
    """
    filters = filters or {}
    
    # CASE 1: Empty Query -> Path B (Metadata Filter Only)
    if not query or query.strip() == "":
        return _fetch_popular_movies(filters, n_results)
        
    # CASE 2: Semantic Search -> Path A (Vector + Boost)
    collection = get_collection()
    if not collection: return []

    where_clause = _build_where_clause(filters)
    model = load_model()

    try:
        query_vector = model.encode(query).tolist()
        
        # Over-fetch strategy:
        # If we need to re-sort by something other than relevance, we need a larger pool.
        fetch_k = n_results * 5 if (boost_weight > 0 or sort_by != "relevance") else n_results

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            where=where_clause,
            include=['metadatas', 'distances']
        )
        
        # Process and blend scores
        candidates = _process_results(results, boost_weight, fetch_k)
        
        # --- FINAL SORTING STEP ---
        if sort_by == "rating":
            # Filter for significant vote count to avoid 1-vote wonders
            candidates = [c for c in candidates if c['vote_count'] > 100]
            candidates.sort(key=lambda x: x['vote_average'], reverse=True)
            
        elif sort_by == "popularity":
            candidates.sort(key=lambda x: x['vote_count'], reverse=True)
            
        elif sort_by == "newest":
            candidates.sort(key=lambda x: x['release_year'], reverse=True)
            
        # Default is "relevance", which is already sorted by _process_results
        
        return candidates[:n_results]

    except Exception as e:
        print(f"Search Error: {e}")
        return []

def find_similar_movies(movie_id, filters=None, n_results=20):
    """
    Finds movies similar to a specific movie_id using its vector.
    """
    collection = get_collection()
    if not collection: return []

    try:
        # 1. Fetch source vector
        # Note: ids in Chroma are strings, but we search by the stored ID
        source = collection.get(ids=[str(movie_id)], include=['embeddings'])
        
        if not source['embeddings']:
            return []
            
        source_vector = source['embeddings'][0]
        filters = filters or {}
        where_clause = _build_where_clause(filters)
        
        # 2. Query with that vector
        results = collection.query(
            query_embeddings=[source_vector],
            n_results=n_results + 2, # Fetch extra to exclude self
            where=where_clause,
            include=['metadatas', 'distances']
        )
        
        processed = _process_results(results, boost_weight=0, final_k=n_results + 5)
        
        # 3. Exclude the movie itself
        # Ensure strict string comparison for safety
        filtered = [m for m in processed if str(m['id']) != str(movie_id)]
        
        return filtered[:n_results]

    except Exception as e:
        print(f"Find Similar Error: {e}")
        return []

def _process_results(raw_results, boost_weight, final_k):
    """
    Blends Semantic Score (1-distance) with Log-Normalized Popularity.
    """
    processed_movies = []
    if not raw_results['ids']: return []
        
    ids = raw_results['ids'][0]
    metadatas = raw_results['metadatas'][0]
    distances = raw_results['distances'][0] # 0 = identical, 1 = orthogonal (roughly)

    # Calculate Max Popularity in this specific batch for normalization
    batch_votes = [m.get('vote_count', 0) for m in metadatas]
    max_vote = max(batch_votes) if batch_votes else 1
    max_log_vote = math.log(max_vote + 1) if max_vote > 0 else 1

    for i in range(len(ids)):
    

        meta = metadatas[i]
        
        # 1. Semantic Score
        # Chroma cosine distance: 0.0 is perfect match.
        # We invert it so 1.0 is perfect match.
        sim_score = max(0, 1 - distances[i])
        
        # 2. Popularity Score
        vote_count = meta.get('vote_count', 0)
        pop_score = math.log(vote_count + 1)
        norm_pop = pop_score / max_log_vote # Normalized 0.0 to 1.0

        # 3. Blended Score
        final_score = (sim_score * (1 - boost_weight)) + (norm_pop * boost_weight)

        processed_movies.append({
            "id": ids[i],
            "title": meta.get('title'),
            "poster_path": meta.get('poster_path'),
            "overview": meta.get('overview'),
            "tagline": meta.get('tagline', ''),
            "release_year": int(meta.get('release_year', 0)),
            "genres": meta.get('genres_display', "Unknown"),
            "vote_average": round(meta.get('vote_average', 0), 1),
            "vote_count": int(vote_count),
            "score": round(final_score, 3),
            "match_percentage": int(final_score * 100)
        })

    # Sort by Blended Score Descending
    processed_movies.sort(key=lambda x: x['score'], reverse=True)
    
    return processed_movies[:final_k]