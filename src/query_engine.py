import chromadb
from sentence_transformers import SentenceTransformer
import streamlit as st
from chroma_manager import get_collection
import math
import traceback
import re
import random

@st.cache_resource
def load_model():
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# --- HELPERS ---

def _normalize_title(text):
    if not text: return ""
    text = text.lower().strip()
    text = re.sub(r'^(the|a|an)\s+', '', text) 
    text = re.sub(r'[^\w\s]', '', text)    
    text = text.replace(" ", "")
    return text.strip()

def _extract_genres(meta):
    return [gid for gid in [28, 12, 16, 35, 80, 99, 18, 10751, 14, 36, 27, 10402, 9648, 10749, 878, 10770, 53, 10752, 37] 
            if meta.get(f"genre_{gid}") == True]

def _format_movie_card(mid, meta, score, is_top=False, is_source=False):
    overview = meta.get('overview', '').strip()
    if len(overview) > 200: overview = overview[:197] + "..."
    
    return {
        "id": mid,
        "title": meta.get('title', 'Unknown'),
        "poster_path": meta.get('poster_path'),
        "overview": overview,
        "tagline": meta.get('tagline', ''),
        "release_year": int(meta.get('release_year', 0)),
        "genre_ids": _extract_genres(meta),
        "vote_average": round(meta.get('vote_average', 0), 1),
        "vote_count": int(meta.get('vote_count', 0)),
        "score": round(score, 3),
        "is_top_result": is_top,
        "is_source": is_source
    }

def _build_where_clause(filters):
    where_conditions = []
    if filters.get('genres'):
        if len(filters['genres']) == 1:
            where_conditions.append({f"genre_{filters['genres'][0]}": True})
        else:
            where_conditions.append({"$or": [{f"genre_{gid}": True} for gid in filters['genres']]})
    if filters.get('year_range'):
        start_year, end_year = filters['year_range']
        where_conditions.append({"release_year": {"$gte": start_year}})
        where_conditions.append({"release_year": {"$lte": end_year}})
    if filters.get('min_rating'):
        where_conditions.append({"vote_average": {"$gte": filters['min_rating']}})
    if filters.get('min_votes'):
        where_conditions.append({"vote_count": {"$gte": filters['min_votes']}})
    if filters.get('language'):
        where_conditions.append({"original_language": {"$eq": filters['language']}})
        
    if not where_conditions: return None
    elif len(where_conditions) == 1: return where_conditions[0]
    return {"$and": where_conditions}

# --- 🔥 UNIVERSE DETECTION LOGIC ---

def _detect_universe(meta):
    """Detects if a movie belongs to a major cinematic universe."""
    text = (
        (meta.get("title") or "") + " " +
        (meta.get("tagline") or "") + " " +  # Fallback for keywords
        (meta.get("overview") or "")
    ).lower()

    # MCU
    if any(x in text for x in ["marvel", "avengers", "iron man", "thor", "captain america", "black widow", "hulk"]):
        return "mcu"
    # DC
    if any(x in text for x in ["dc", "batman", "superman", "joker", "wonder woman", "justice league"]):
        return "dc"
    # Harry Potter
    if any(x in text for x in ["harry potter", "hogwarts", "voldemort"]):
        return "wizarding_world"
    # Star Wars
    if any(x in text for x in ["star wars", "jedi", "sith", "skywalker"]):
        return "star_wars"

    return None

def _apply_universe_boost(source_meta, candidate_meta, score):
    """Applies a strict +0.10 boost if universes match."""
    source_universe = _detect_universe(source_meta)
    if not source_universe:
        return score
        
    candidate_universe = _detect_universe(candidate_meta)
    if source_universe == candidate_universe:
        score += 0.1
        
    return score

# --- STAGE 1: EXACT MATCH LOGIC ---

def _get_top_result_by_title(query, collection):
    query_norm = _normalize_title(query)
    if not query_norm: return None

    # --- LAYER 1: Fast O(1) Lexical Match ---
    res = collection.get(
    where={"normalized_title": query_norm},
    include=['metadatas']
)
    if res and res['ids']:
        candidates = [{"id": res['ids'][i], "meta": res['metadatas'][i]} for i in range(len(res['ids']))]
        candidates.sort(key=lambda x: x['meta'].get('vote_count', 0), reverse=True)
        return candidates[0]

    # --- LAYER 2: Smarter Semantic Fallback ---
    try:
        model = load_model()
        query_vector = model.encode(query).tolist()
        
        fallback_res = collection.query(
            query_embeddings=[query_vector], 
            n_results=10, 
            include=['metadatas', 'distances']
        )

        valid_fallbacks = []
        if fallback_res and fallback_res['ids'] and fallback_res['ids'][0]:
            ids = fallback_res['ids'][0]
            metas = fallback_res['metadatas'][0]
            distances = fallback_res['distances'][0]

            for i in range(len(ids)):
                meta = metas[i]
                sim_score = max(0.0, 1.0 - distances[i])
                db_title_norm = meta.get('normalized_title', _normalize_title(meta.get('title', '')))

                if query_norm == db_title_norm:
                    valid_fallbacks.append({"id": ids[i], "meta": meta, "sim": 1.0})
                elif sim_score > 0.85:
                    valid_fallbacks.append({"id": ids[i], "meta": meta, "sim": sim_score})

            if valid_fallbacks:
                valid_fallbacks.sort(key=lambda x: (x['sim'], x['meta'].get('vote_count', 0)), reverse=True)
                return {"id": valid_fallbacks[0]['id'], "meta": valid_fallbacks[0]['meta']}
                
    except Exception as e:
        print(f"Fallback Search Error: {e}")

    return None

# --- STAGE 2: RECOMMENDATION LOGIC ---

def _fetch_semantic_recs(query_text, collection, filters, boost_weight, final_k, source_meta=None, min_similarity=0.30):
    model = load_model()
    where_clause = _build_where_clause(filters)
    fetch_k = final_k * 10 
    
    try:
        query_vector = model.encode(query_text).tolist()
        raw_results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            where=where_clause,
            include=['metadatas', 'distances']
        )
    except Exception as e:
        print(f"Vector search failed: {e}")
        return []

    if not raw_results or not raw_results.get('ids') or not raw_results['ids'][0]: return []

    ids = raw_results['ids'][0]
    metadatas = raw_results['metadatas'][0]
    distances = raw_results['distances'][0]

    batch_votes = [m.get('vote_count', 0) for m in metadatas]
    max_log_vote = math.log(max(batch_votes) + 1) if batch_votes and max(batch_votes) > 0 else 1.0

    processed_movies = []
    seen_titles = set()
    source_genres = set(_extract_genres(source_meta)) if source_meta else set()
    
    source_norm = _normalize_title(source_meta.get('title', '')) if source_meta else ""
    franchise_count = 0 
    MAX_FRANCHISE_MOVIES = 4 

    if source_norm:
        seen_titles.add(source_norm)

    for i in range(len(ids)):
        meta = metadatas[i]
        cand_norm_title = meta.get('normalized_title', _normalize_title(meta.get('title', '')))
        
        if cand_norm_title in seen_titles:
            continue
            
        sim_score = min(max(0.0, 1.0 - distances[i]), 1.0)
        # 🔥 GENRE WEIGHTING (important)
        cand_genres = set(_extract_genres(meta))
        if source_genres:
            overlap = source_genres.intersection(cand_genres)
            overlap_ratio = len(overlap) / max(len(source_genres), 1)

            # boost if strong overlap
            sim_score += overlap_ratio * 0.05

            # penalize if weak overlap
            if overlap_ratio < 0.3:
                sim_score -= 0.05
        if sim_score < min_similarity:
            continue
            
        # 🔥 FIX: The Relaxed Genre Escape Hatch
        
        # 🔥 prioritize sci-fi alignment
        if 878 in source_genres:
            if 878 in cand_genres:
                sim_score += 0.05
            else:
                sim_score -= 0.05

        # ❌ remove animation mismatch
        if 16 in cand_genres and 16 not in source_genres:
            continue
        if source_genres:
            has_overlap = source_genres.intersection(cand_genres)
            if not has_overlap and sim_score < 0.5:
                continue

        if source_norm and len(source_norm) >= 4 and source_norm in cand_norm_title:
            franchise_count += 1
            if franchise_count > MAX_FRANCHISE_MOVIES:
                continue 

        vote_count = meta.get('vote_count', 0)
        norm_pop = math.log(vote_count + 1) / max_log_vote
        rating = meta.get("vote_average", 0) / 10

        blended_score = (
            sim_score * 0.6 +
            norm_pop * 0.2 +
            rating * 0.2
        )

        # 🔥 FIX: Apply Universe Boost
        if source_meta:
            blended_score = _apply_universe_boost(source_meta, meta, blended_score)

        processed_movies.append(_format_movie_card(ids[i], meta, blended_score))
        seen_titles.add(cand_norm_title)

    processed_movies.sort(key=lambda x: (x['score'], x['vote_count'], x['release_year']), reverse=True)
    return processed_movies[:final_k]

# --- MAIN ORCHESTRATOR ---

def search_movies(query, filters=None, boost_weight=0.1, sort_by="relevance", n_results=20, random_seed=42):
    filters = filters or {}
    if 'min_votes' not in filters: filters['min_votes'] = 100
    collection = get_collection()
    if not collection: return []

    # AFTER (random each session):
    if not query or query.strip() == "":
        seed_queries = [
    # Emotion-led
    "emotional drama life changing journey",
    "heartbreaking story loss and redemption",
    "feel good uplifting inspiring story",
    "bittersweet coming of age growing up",
    "friendship loyalty trust betrayal",
    "father son relationship emotional bond",
    "mother daughter love sacrifice",
    "grief healing moving on",

    # Genre-led
    "epic action adventure hero saves world",
    "thrilling crime heist mystery suspense",
    "romantic love story fate destiny",
    "mind bending science fiction future",
    "dark psychological thriller obsession",
    "supernatural horror fear survival",
    "dark comedy satire society absurd",
    "family animation adventure fun",
    "historical epic war sacrifice honor",
    "western outlaw justice revenge desert",
    "spy espionage secret mission betrayal",
    "courtroom legal drama justice truth",
    "sports underdog triumph victory",
    "road trip self discovery freedom",

    # Mood-led
    "thought provoking philosophical meaning of life",
    "visually stunning breathtaking cinematography",
    "slow burn atmospheric tension dread",
    "fast paced adrenaline non stop action",
    "witty clever dialogue sharp writing",
    "surreal dreamlike abstract reality",
    "gritty realistic raw street life",
    "wholesome gentle quiet beautiful",

    # Setting-led
    "space exploration astronaut cosmos",
    "underwater ocean deep sea mystery",
    "post apocalyptic survival wasteland",
    "small town secrets dark past",
    "big city ambition dreams success",
    "jungle wilderness nature survival",
    "cold war political intrigue",
]
        random.seed(random_seed)
        chosen_query = random.choice(seed_queries)
        return _fetch_semantic_recs(chosen_query, collection, filters, boost_weight, n_results, min_similarity=0.10)

    top_movie = _get_top_result_by_title(query, collection)

    if top_movie:
        top_card = _format_movie_card(top_movie['id'], top_movie['meta'], 100.0, is_top=True)
        
        title = top_movie['meta'].get('title', '')
        plot = top_movie['meta'].get('overview', '')

        # Extract genres
        genre_ids = _extract_genres(top_movie['meta'])
        genre_str = " ".join([str(g) for g in genre_ids])

        # Extract keywords (fallback: tagline)
        keywords = top_movie['meta'].get('keywords', '') or top_movie['meta'].get('tagline', '')

        rec_query = f"""
        Title: {title}
        Genres: {genre_str}
        Keywords: {keywords}
        Overview: {plot}
        """
        
        rec_filters = filters.copy()
        rec_filters['min_votes'] = 50 
        
        recs = _fetch_semantic_recs(
            rec_query, 
            collection, 
            rec_filters, 
            boost_weight, 
            n_results - 1, 
            source_meta=top_movie['meta'],
            min_similarity=0.15   # 🔥 FIX: Lowered from 0.40 to allow sequels and semantic matches
        )
        top_rated = _get_top_rated_in_genre(
        collection,
        top_movie['meta'],
        filters,
        k=4
    )
        seen_ids = set([top_movie['id']] + [r['id'] for r in recs])
        top_rated = [m for m in top_rated if m['id'] not in seen_ids]
        
        return {
        "top_result": top_card,
        "similar": recs,
        "top_rated": top_rated
    }
        
    else:
        return _fetch_semantic_recs(query, collection, filters, boost_weight, n_results, min_similarity=0.15)

def find_similar_movies(movie_id, filters=None, boost_weight=0.1, n_results=20):
    collection = get_collection()
    if not collection: return []
    filters = filters or {}
    if 'min_votes' not in filters: filters['min_votes'] = 50

    try:
        source_res = collection.get(ids=[str(movie_id)], include=['metadatas'])
        if not source_res.get('ids'): return []
        meta = source_res['metadatas'][0]

        source_card = _format_movie_card(movie_id, meta, 100.0, is_source=True)
        
        title = meta.get('title', '')
        plot = meta.get('overview', '')
        query_text = f"{title}. {plot}".strip()

        recs = _fetch_semantic_recs(
            query_text, 
            collection, 
            filters, 
            boost_weight, 
            n_results - 1, 
            source_meta=meta,
            min_similarity=0.15
        )
        return [source_card] + recs
    except Exception as e:
        print(f"Find Similar Error: {e}")
        return []
    
def _get_top_rated_in_genre(collection, source_meta, filters, k=5):
    source_genres = _extract_genres(source_meta)
    if not source_genres:
        return []

    # Take only 1–2 dominant genres (prevents garbage matches)
    primary_genres = list(source_genres)[:2]

    where_clause = {
        "$or": [{f"genre_{gid}": True} for gid in primary_genres]
    }

    try:
        res = collection.get(
        where=where_clause,
        include=['metadatas'],
        limit=200
)

        if not res or not res.get("ids"):
            return []

        movies = []
        source_norm = _normalize_title(source_meta.get("title", ""))

        for i in range(len(res.get("ids", []))):
            meta = res["metadatas"][i]

            # skip same movie
            if _normalize_title(meta.get("title", "")) == source_norm:
                continue

            # strong quality filter
            if meta.get("vote_count", 0) < 1000:
                continue

            rating = meta.get("vote_average", 0) / 10
            votes = min(meta.get("vote_count", 0) / 10000, 1)

            score = rating * 0.7 + votes * 0.3

            card = _format_movie_card(res["ids"][i], meta, score)
            card["is_top_rated"] = True  # 🔥 mark it

            movies.append(card)

        movies.sort(key=lambda x: x["score"], reverse=True)
        return movies[:k]

    except Exception as e:
        print("Top rated error:", e)
        return []