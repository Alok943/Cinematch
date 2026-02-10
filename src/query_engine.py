import chromadb
from sentence_transformers import SentenceTransformer
import streamlit as st
from chroma_manager import get_collection
import math
import traceback

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

def _fetch_popular_movies(filters, n_results):
    """
    FALLBACK: When no text query is provided, fetch movies based on filters 
    and sort by popularity.
    """
    collection = get_collection()
    if not collection: return []
    
    where_clause = _build_where_clause(filters)
    
    try:
        results = collection.get(
            where=where_clause,
            limit=1000, 
            include=['metadatas']
        )
        
        processed = []
        if results['metadatas']:
            for meta in results['metadatas']:
                processed.append({
                    "id": str(meta.get('movie_id')),  # ← FIXED: Convert to string
                    "title": meta.get('title'),
                    "poster_path": meta.get('poster_path'),
                    "overview": meta.get('overview'),
                    "tagline": meta.get('tagline', ''),
                    "release_year": int(meta.get('release_year', 0)),
                    "genres": meta.get('genres_display', "Unknown"),
                    "vote_average": round(meta.get('vote_average', 0), 1),
                    "vote_count": meta.get('vote_count', 0),
                    "score": 0.0, 
                    "match_percentage": 0
                })
            
        # Sort by popularity
        processed.sort(key=lambda x: x['vote_count'], reverse=True)
        return processed[:n_results]
        
    except Exception as e:
        print(f"Popular Fetch Error: {e}")
        return []

def search_movies(query, filters=None, boost_weight=0.0, sort_by="relevance", n_results=20):
    """
    Main search entry point.
    """
    filters = filters or {}
    
    # CASE 1: Empty Query
    if not query or query.strip() == "":
        return _fetch_popular_movies(filters, n_results)
        
    # CASE 2: Semantic Search
    collection = get_collection()
    if not collection: return []

    where_clause = _build_where_clause(filters)
    model = load_model()

    try:
        query_vector = model.encode(query).tolist()
        
        # Over-fetch for re-ranking
        fetch_k = n_results * 5 if (boost_weight > 0 or sort_by != "relevance") else n_results

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            where=where_clause,
            include=['metadatas', 'distances']
        )
        
        candidates = _process_results(results, boost_weight, fetch_k)
        
        # Final Sorting
        if sort_by == "rating":
            candidates = [c for c in candidates if c['vote_count'] > 100]
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
    """
    Finds movies similar to a specific movie_id using its vector.
    """
    collection = get_collection()
    if not collection: 
        return []

    try:
        # 1. Fetch source vector - ENSURE ID IS STRING
        movie_id_str = str(movie_id)
        
        print(f"DEBUG: Searching for movie_id={movie_id_str}")
        
        source = collection.get(
            ids=[movie_id_str], 
            include=['embeddings', 'metadatas']
        )
        
        print(f"DEBUG: Found IDs={source.get('ids', [])}")
        
        # Safety Check - Fixed!
        if not source.get('ids') or len(source['ids']) == 0:
            print(f"Error: Movie ID {movie_id_str} not found in collection.")
            return []
            
        if source.get('embeddings') is None or len(source['embeddings']) == 0:
            print(f"Error: Movie ID {movie_id_str} has no embedding.")
            return []
            
        source_vector = source['embeddings'][0]
        source_title = source['metadatas'][0].get('title', 'Unknown')
        print(f"DEBUG: Retrieved embedding for '{source_title}'")
        
        filters = filters or {}
        where_clause = _build_where_clause(filters)
        
        # 2. Query with that vector
        results = collection.query(
            query_embeddings=[source_vector],
            n_results=n_results + 5,
            where=where_clause,
            include=['metadatas', 'distances']
        )
        
        processed = _process_results(results, boost_weight=0, final_k=n_results + 5)
        
        # 3. Exclude the movie itself from results
        filtered = [m for m in processed if str(m['id']) != movie_id_str]
        
        print(f"DEBUG: Returning {len(filtered)} similar movies")
        return filtered[:n_results]

    except Exception as e:
        print(f"Find Similar Error: {e}")
        traceback.print_exc()
        return []

def _process_results(raw_results, boost_weight, final_k):
    """
    Blends Semantic Score with Popularity.
    """
    processed_movies = []
    
    # Safety check for empty results
    if not raw_results or not raw_results['ids'] or len(raw_results['ids'][0]) == 0:
        return []
        
    ids = raw_results['ids'][0]
    metadatas = raw_results['metadatas'][0]
    distances = raw_results['distances'][0]

    # Calculate Max Popularity for normalization
    batch_votes = [m.get('vote_count', 0) for m in metadatas]
    max_vote = max(batch_votes) if batch_votes else 1
    max_log_vote = math.log(max_vote + 1) if max_vote > 0 else 1

    for i in range(len(ids)):
        meta = metadatas[i]
        
        # 1. Semantic Score (1 - distance)
        sim_score = max(0, 1 - distances[i])
        
        # 2. Popularity Score
        vote_count = meta.get('vote_count', 0)
        pop_score = math.log(vote_count + 1)
        norm_pop = pop_score / max_log_vote 

        # 3. Blended Score
        final_score = (sim_score * (1 - boost_weight)) + (norm_pop * boost_weight)

        processed_movies.append({
            "id": ids[i],  # ← This is the ChromaDB ID (string like "157336")
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

    # Sort by Blended Score
    processed_movies.sort(key=lambda x: x['score'], reverse=True)
    
    return processed_movies[:final_k]