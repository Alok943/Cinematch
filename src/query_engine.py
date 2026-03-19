import chromadb
from sentence_transformers import SentenceTransformer
import streamlit as st
from chroma_manager import get_collection
import math
import traceback
import ast
import re
import random

TITLE_SEARCH_STOPWORDS = {"the", "a", "an", "of", "in", "on", "at", "to"}
# Load model once and cache it
@st.cache_resource
def load_model():
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

@st.cache_resource
@st.cache_resource
def _get_all_titles():
    from chroma_manager import get_collection
    collection = get_collection()
    if not collection:
        return [], [], []
    
    results = collection.get(
        limit=collection.count(),
        include=["metadatas"]
    )
    
    ids = results["ids"]
    titles = [m.get("title_lower", "") for m in results["metadatas"]]
    languages = [m.get("original_language", "") for m in results["metadatas"]]
    
    return ids, titles, languages

def _find_movie_by_title(query: str, preferred_language: str = None):
    query_lower = query.lower().strip()
    ids, titles, languages = _get_all_titles()
    
    first_match = None
    
    for i, title in enumerate(titles):
        if query_lower in title:
            if first_match is None:
                first_match = ids[i]
            if preferred_language and languages[i] == preferred_language:
                return ids[i]
    
    return first_match

def _build_where_clause(filters):
    """
    Constructs the ChromaDB metadata filter dict.
    """
    print(f"DEBUG filters received: {filters}")
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

    # 5. Minimum Vote Count — prevents unrated/obscure films from surfacing
    if filters.get('min_votes'):
        where_conditions.append({"vote_count": {"$gte": filters['min_votes']}})
    # 6. Language Filter
    if filters.get('language'):
        where_conditions.append({"original_language": {"$eq": filters['language']}})
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
    """
    if _is_documentary_search(query):
        return movies

    DOCUMENTARY_ID = 99

    for movie in movies:
        genre_ids = movie.get('genre_ids', [])
        if DOCUMENTARY_ID in genre_ids:
            movie['score'] = movie['score'] * penalty_factor
            movie['is_penalized'] = True

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
    distances = raw_results['distances'][0] if 'distances' in raw_results else [0] * len(ids)

    # Calculate Max Popularity for normalization
    batch_votes = [m.get('vote_count', 0) for m in metadatas]
    max_vote = max(batch_votes) if batch_votes else 1
    max_log_vote = math.log(max_vote + 1) if max_vote > 0 else 1

    for i in range(len(ids)):
        meta = metadatas[i]

        # 1. Semantic Score (1 - cosine distance)
        sim_score = max(0, 1 - distances[i]) if i < len(distances) else 0

        # FIX 3: Lowered threshold from 0.5 -> 0.40
        # 0.5 was too aggressive — it was cutting genuine matches for niche/abstract queries
        # (e.g. Arrival, Shawshank, Beautiful Mind returned garbage because pool was too small)
        #if sim_score < 0.35:
           # continue

        # Stretch passing scores (0.40 to 1.0) into a clean 0.0 to 1.0 scale
        normalized_sim = sim_score

        # 2. Popularity Score
        vote_count = meta.get('vote_count', 0)
        pop_score = math.log(vote_count + 1)
        norm_pop = pop_score / max_log_vote

        # 3. Blended Score
        final_score = (normalized_sim * (1 - boost_weight)) + (norm_pop * boost_weight)
        

        if (query and len(query.strip().split()) <= 2 
    and query.lower().strip() not in TITLE_SEARCH_STOPWORDS
    and query.lower().strip() in meta.get('title', '').lower()):
            final_score += 0.3
        # 4. Data Extraction — reconstruct genre_ids from one-hot metadata flags
        genre_ids = [
            gid for gid in [
                28, 12, 16, 35, 80, 99, 18, 10751, 14, 36, 27,
                10402, 9648, 10749, 878, 10770, 53, 10752, 37
            ]
            if meta.get(f"genre_{gid}") == True
        ]

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

    # Sort by blended score descending
    processed_movies.sort(key=lambda x: x['score'], reverse=True)

    return processed_movies[:final_k]

def _fetch_popular_movies(filters, n_results,random_seed = 42):
    """
    FALLBACK: Used when query is empty. Fetches a random sample of
    movies that pass the filters and returns them shuffled.
    """
    collection = get_collection()
    if not collection:
        return []

    where_clause = _build_where_clause(filters)

    try:
        results = collection.get(
            where=where_clause,
            limit=500,
            include=['metadatas']
        )

        import random
        combined = list(zip(results['ids'], results['metadatas']))
        random.seed(random_seed)
        random.shuffle(combined)

        if not combined:
            return []

        shuffled_ids, shuffled_metas = zip(*combined)

        # distances=1.0 means sim_score=0.0 for all — threshold will cut everything.
        # So we bypass _process_results and sort by vote_count directly here.
        movies = []
        for mid, meta in zip(shuffled_ids, shuffled_metas):
            vote_count = int(meta.get('vote_count', 0))

            genre_ids = [
                gid for gid in [
                    28, 12, 16, 35, 80, 99, 18, 10751, 14, 36, 27,
                    10402, 9648, 10749, 878, 10770, 53, 10752, 37
                ]
                if meta.get(f"genre_{gid}") == True
            ]

            overview = meta.get('overview', '').strip()
            if len(overview) > 200:
                overview = overview[:197] + "..."

            movies.append({
                "id": mid,
                "title": meta.get('title'),
                "poster_path": meta.get('poster_path'),
                "overview": overview,
                "tagline": meta.get('tagline', ''),
                "release_year": int(meta.get('release_year', 0)),
                "release_date": meta.get('release_date', ''),
                "genre_ids": genre_ids,
                "vote_average": round(meta.get('vote_average', 0), 1),
                "vote_count": vote_count,
                "score": 0.0,
                "is_penalized": False
            })

        # Shuffle for variety on homepage, then return top N
        random.shuffle(movies)
        return movies[:n_results]

    except Exception as e:
        print(f"Popular Fetch Error: {e}")
        return []
def _is_title_query(query: str) -> bool:
    return len(query.strip().split()) <= 4

def search_movies(query, filters=None, boost_weight=0.0, sort_by="relevance", n_results=20,random_seed=42):
    filters = filters or {}

    # FIX 1: Wire in min_votes=100 globally to kill 0-vote / 1-vote film leakage
    # Only apply the default if caller hasn't explicitly set it
    if 'min_votes' not in filters:
        filters['min_votes'] = 100

    # CASE 1: Empty Query -> Popular
    if not query or query.strip() == "":
        return _fetch_popular_movies(filters, n_results,random_seed)
    if _is_title_query(query):
        preferred_lang = filters.get('language')
        movie_id = _find_movie_by_title(query,preferred_language = preferred_lang)
        print(f"DEBUG _is_title_query=True, movie_id={movie_id}")
        if movie_id:
            results = find_similar_movies(movie_id, filters=filters, n_results=n_results)
            print(f"DEBUG find_similar returned {len(results)} results")
            return results
    # CASE 2: Semantic Search
    collection = get_collection()
    if not collection:
        return []

    where_clause = _build_where_clause(filters)
    model = load_model()

    try:
        # Apply query expansion to catch trap idioms before encoding
        #optimized_query = _rewrite_query(query)
        query_vector = model.encode(query).tolist()

        # fetch_k = 5x to ensure enough candidates survive the threshold gate
        fetch_k = n_results * 10

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            where=where_clause,
            include=['metadatas', 'distances']
        )

        # Pass ORIGINAL query to documentary penalty, not the expanded one
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


def find_similar_movies(movie_id, filters=None, boost_weight=0.0, n_results=20):
    collection = get_collection()
    if not collection:
        return []

    filters = filters or {}
    if 'min_votes' not in filters:
        print(f"DEBUG min_votes in filters: {filters.get('min_votes')}")
        # Hindi/regional films have fewer votes — lower threshold
        if filters.get('language') and filters['language'] != 'en':
            filters['min_votes'] = 20
        else:
            filters['min_votes'] = 300

    try:
        movie_id_str = str(movie_id)

        # Fetch metadata only — no embeddings fetch (chromadb Rust bug)
        source_meta = collection.get(ids=[movie_id_str], include=['metadatas'])

        if not source_meta.get('ids'):
            print(f"Movie ID {movie_id_str} not found.")
            return []

        meta = source_meta['metadatas'][0]

        # Auto-inject source movie's genres into filter if user hasn't selected any
        if not filters.get('genres'):
            if filters.get('language') and filters['language'] != 'en':
                source_genre_ids = [
                    gid for gid in [
                    28, 12, 16, 35, 80, 99, 18, 10751, 14, 36, 27,
                    10402, 9648, 10749, 878, 10770, 53, 10752, 37
                ]
                    if meta.get(f"genre_{gid}") == True
                ]
                if source_genre_ids:
                    filters['genres'] = source_genre_ids

        title = meta.get('title', '')
        overview = meta.get('overview', '')
        tagline = meta.get('tagline', '')
        query_text = f"{title}. {tagline}. {overview}".strip()

        # Reuse search_movies — it works fine, no Rust query bug there
        results = search_movies(
            query=query_text,
            filters=filters,
            boost_weight=boost_weight,
            n_results=n_results + 1,  # +1 to account for source movie
        )

        # Mark source card, put it first
        source_card = next((m for m in results if str(m['id']) == movie_id_str), None)
        others = [m for m in results if str(m['id']) != movie_id_str]

        if source_card:
            source_card['is_source'] = True
            return [source_card] + others[:n_results - 1]

        return results[:n_results]

    except Exception as e:
        print(f"Find Similar Error: {e}")
        traceback.print_exc()
        return []