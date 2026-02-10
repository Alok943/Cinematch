import chromadb
from sentence_transformers import SentenceTransformer
import streamlit as st
from chroma_manager import get_collection
import math
import traceback
import ast
import re

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

    # 2. Safe Search
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

def _parse_list_from_metadata(value):
    """Safely parse a stringified list from metadata (e.g., '[28, 12]')"""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.startswith('['):
        try:
            return ast.literal_eval(value)
        except:
            return []
    return []

def _is_documentary_search(query):
    """
    Check if the user is explicitly searching for documentaries.
    """
    if not query:
        return False
    
    doc_keywords = [
        'documentary', 'documentaries', 'doc', 'real story', 
        'true story', 'real life', 'based on true events',
        'biography', 'biopic', 'historical account'
    ]
    
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in doc_keywords)

def _apply_documentary_penalty(movies, query, penalty_factor=0.3):
    """
    Reduce scores for documentaries unless explicitly searched for.
    
    Args:
        movies: List of processed movie dicts
        query: User's search query
        penalty_factor: Score multiplier for docs (0.3 = 70% reduction)
    
    Returns:
        Modified movies list with adjusted scores
    """
    if _is_documentary_search(query):
        return movies  # No penalty if user wants documentaries
    
    DOCUMENTARY_ID = 99
    
    for movie in movies:
        genre_ids = movie.get('genre_ids', [])
        if DOCUMENTARY_ID in genre_ids:
            movie['score'] = movie['score'] * penalty_factor
            movie['is_penalized'] = True  # For debugging
    
    return movies

def _process_results(raw_results, boost_weight, final_k, query=""):
    """
    Blends Semantic Score with Popularity and standardizes output keys.
    """
    processed_movies = []
    
    # Safety check for empty results
    if not raw_results or not raw_results.get('ids') or not raw_results['ids'][0]:
        return []
        
    ids = raw_results['ids'][0]
    metadatas = raw_results['metadatas'][0]
    distances = raw_results['distances'][0] if 'distances' in raw_results else [0]*len(ids)

    # Calculate Max Popularity for normalization
    batch_votes = [m.get('vote_count', 0) for m in metadatas]
    max_vote = max(batch_votes) if batch_votes else 1
    max_log_vote = math.log(max_vote + 1) if max_vote > 0 else 1

    for i in range(len(ids)):
        meta = metadatas[i]
        
        # 1. Semantic Score (1 - distance)
        # Handle cases where distance might be missing (popular fetch)
        sim_score = max(0, 1 - distances[i]) if i < len(distances) else 0
        
        # 2. Popularity Score
        vote_count = meta.get('vote_count', 0)
        pop_score = math.log(vote_count + 1)
        norm_pop = pop_score / max_log_vote 

        # 3. Blended Score
        final_score = (sim_score * (1 - boost_weight)) + (norm_pop * boost_weight)

        # 4. Data Extraction
        # Ensure genre_ids is a list so app.py can map it
        genre_ids = _parse_list_from_metadata(meta.get('genre_ids'))
        
        # Clean overview text
        overview = meta.get('overview', '').strip()
        if len(overview) > 200:
            overview = overview[:197] + "..."
        
        processed_movies.append({
            "id": ids[i],
            "title": meta.get('title'),
            "poster_path": meta.get('poster_path'),
            "overview": overview,
            "tagline": meta.get('tagline', ''),
            "release_year": int(meta.get('release_year', 0)),
            "release_date": meta.get('release_date', ''),
            "genre_ids": genre_ids,
            "vote_average": round(meta.get('vote_average', 0), 1),
            "vote_count": int(vote_count),
            "score": round(final_score, 3),
            "is_penalized": False
        })

    # Apply documentary penalty BEFORE sorting
    processed_movies = _apply_documentary_penalty(processed_movies, query)

    # Sort by Blended Score
    processed_movies.sort(key=lambda x: x['score'], reverse=True)
    
    return processed_movies[:final_k]

def _fetch_popular_movies(filters, n_results):
    """
    FALLBACK: Fetch movies based on filters and sort by popularity.
    """
    collection = get_collection()
    if not collection: return []
    
    where_clause = _build_where_clause(filters)
    
    try:
        results = collection.get(
            where=where_clause,
            limit=n_results * 2,
            include=['metadatas']
        )
        
        # Mock wrapper to reuse _process_results logic
        mock_results = {
            'ids': [results['ids']],
            'metadatas': [results['metadatas']],
            'distances': [[1.0] * len(results['ids'])]
        }
        
        processed = _process_results(mock_results, boost_weight=1.0, final_k=n_results, query="")
        
        # Explicit sort by vote count for popular view
        processed.sort(key=lambda x: x['vote_count'], reverse=True)
        return processed
        
    except Exception as e:
        print(f"Popular Fetch Error: {e}")
        return []

def search_movies(query, filters=None, boost_weight=0.0, sort_by="relevance", n_results=20):
    filters = filters or {}
    
    # CASE 1: Empty Query -> Popular
    if not query or query.strip() == "":
        return _fetch_popular_movies(filters, n_results)
        
    # CASE 2: Semantic Search
    collection = get_collection()
    if not collection: return []

    where_clause = _build_where_clause(filters)
    model = load_model()

    try:
        query_vector = model.encode(query).tolist()
        fetch_k = n_results * 3

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            where=where_clause,
            include=['metadatas', 'distances']
        )
        
        # Pass query to _process_results for documentary penalty
        candidates = _process_results(results, boost_weight, fetch_k, query=query)
        
        # Final Sorting
        if sort_by == "rating":
            candidates = [c for c in candidates if c['vote_count'] > 50]
            candidates.sort(key=lambda x: x['vote_average'], reverse=True)
        elif sort_by == "popularity":
            candidates.sort(key=lambda x: x['vote_count'], reverse=True)
        elif sort_by == "newest":
            candidates.sort(key=lambda x: x['release_year'], reverse=True)
            
        return candidates[:n_results]

    except Exception as e:
        print(f"Search Error: {e}")
        traceback.print_exc()
        return []

def find_similar_movies(movie_id, filters=None, n_results=20):
    collection = get_collection()
    if not collection: return []

    try:
        movie_id_str = str(movie_id)
        source = collection.get(ids=[movie_id_str], include=['embeddings'])
        
        if not source.get('ids') or not source.get('embeddings'):
            print(f"Error: Movie ID {movie_id_str} not found.")
            return []
            
        source_vector = source['embeddings'][0]
        
        filters = filters or {}
        where_clause = _build_where_clause(filters)
        
        results = collection.query(
            query_embeddings=[source_vector],
            n_results=n_results + 5,
            where=where_clause,
            include=['metadatas', 'distances']
        )
        
        processed = _process_results(results, boost_weight=0, final_k=n_results + 5, query="")
        
        # Exclude self
        filtered = [m for m in processed if str(m['id']) != movie_id_str]
        return filtered[:n_results]

    except Exception as e:
        print(f"Find Similar Error: {e}")
        traceback.print_exc()
        return []