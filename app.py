import streamlit as st
import sys
import os
import time

# --- PATH SETUP ---
# Ensures we can import from the 'src' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

import chroma_manager
import query_engine

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Cinematch V2",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GLOBAL CONSTANTS ---
GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie",
    53: "Thriller", 10752: "War", 37: "Western"
}

# --- ENHANCED CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* 1. BACKGROUND ANIMATION */
    .stApp {
        background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e, #1a1a2e);
        background-size: 400% 400%;
        animation: gradientBG 20s ease infinite;
        color: white;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* 2. CARD CONTAINER - The Fix for Alignment */
    .movie-card-container {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        /* Min-height ensures alignment even if plot is short */
        min-height: 540px; 
        margin-bottom: 20px;
        position: relative;
    }

    .movie-card-container:hover {
        transform: translateY(-8px);
        border-color: rgba(76, 175, 80, 0.6);
        box-shadow: 0 16px 48px rgba(76, 175, 80, 0.2);
        background: rgba(255, 255, 255, 0.12);
    }

    /* 3. POSTER IMAGE */
    .poster-div {
        width: 100%;
        height: 320px;
        overflow: hidden;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .poster-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.4s ease;
    }
    
    .movie-card-container:hover .poster-img {
        transform: scale(1.08);
    }

    /* 4. CONTENT AREA */
    .card-content {
        padding: 15px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    /* 5. TITLE */
    .movie-title {
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 8px;
        height: 2.8rem; /* Forces 2 lines max */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-height: 1.4rem;
        color: #fff;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }

    /* 6. BADGES */
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-bottom: 12px;
        min-height: 25px;
    }

    .badge {
        background: rgba(76, 175, 80, 0.2);
        border: 1px solid rgba(76, 175, 80, 0.4);
        color: #4CAF50;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-year {
        background: rgba(33, 150, 243, 0.2);
        border-color: rgba(33, 150, 243, 0.4);
        color: #2196F3;
    }

    /* 7. META ROW (Rating & Match) */
    .meta-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.1);
    }

    .rating-badge {
        font-weight: 700;
        font-size: 0.95rem;
        color: #FFD700;
    }

    .match-score {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.75rem;
    }

   /* 8. OVERVIEW TOGGLE (Enhanced) */
    details {
        margin-bottom: 10px;
        color: rgba(255,255,255,0.7);
        font-size: 0.85rem;
        border-top: 1px solid rgba(255,255,255,0.1); /* Separator line */
        padding-top: 8px;
    }
    
    summary {
        cursor: pointer;
        color: #4CAF50;
        font-weight: 600;
        margin-bottom: 5px;
        outline: none;
        list-style: none; /* Hides default triangle */
    }

    /* Custom Arrows */
    summary::after {
        content: " ▼";
        font-size: 0.8em;
        transition: transform 0.2s;
    }

    details[open] summary::after {
        content: " ▲"; /* Flips arrow when open */
    }
    
    /* Hides default marker in Webkit browsers */
    summary::-webkit-details-marker {
        display: none;
    }
    
    .overview-text {
        font-size: 0.8rem;
        line-height: 1.5;
        background: rgba(0,0,0,0.2); /* Darker background for readability */
        padding: 10px;
        border-radius: 8px;
        margin-top: 5px;
        color: #ddd;
    }

    /* 9. STREAMLIT BUTTON OVERRIDE */
    .stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        padding: 10px;
        text-transform: uppercase;
        font-size: 0.85rem;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(76, 175, 80, 0.5);
    }
    
    /* 10. HEADER STYLE */
    h1 {
        text-align: center;
        background: linear-gradient(135deg, #4CAF50, #45a049, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        padding-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

if 'target_movie_id' not in st.session_state:
    st.session_state['target_movie_id'] = None

if 'search_cache' not in st.session_state:
    st.session_state['search_cache'] = {}

def clear_target_movie():
    st.session_state['target_movie_id'] = None

def set_target_movie(movie_id):
    st.session_state['target_movie_id'] = movie_id

def get_genre_names(genre_ids, max_genres=2):
    """Convert ID list to badge-friendly strings"""
    if not genre_ids: 
        return []
    names = [GENRE_MAP.get(gid, "") for gid in genre_ids[:max_genres]]
    return [n for n in names if n]

def format_year(year):
    return str(year) if year and year > 1900 else "N/A"

def render_movie_card(movie, idx, context="search"):
    """
    Renders a movie card with HTML structure and a unique button key.
    """
    # 1. Prepare Data
    poster_path = movie.get('poster_path')
    if poster_path:
        if not poster_path.startswith("/"):
            poster_path = f"/{poster_path}"
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
    else:
        poster_url = "https://via.placeholder.com/500x750/1a1a2e/4CAF50?text=No+Poster"
    
    title = movie.get('title', 'Unknown Title')
    year = format_year(movie.get('release_year'))
    genres = get_genre_names(movie.get('genre_ids', []), max_genres=2)
    vote_average = movie.get('vote_average', 0.0)
    
    # Clean overview to prevent broken HTML tags and escaping quotes
    overview = movie.get('overview', 'No description available.')
    overview = overview.replace('"', '&quot;').replace("'", "&#39;") 
    if len(overview) > 400:
        overview = overview[:400] + "..."
    
    # Generate Badge HTML
    badges_html = f'<span class="badge badge-year">{year}</span>'
    for g in genres:
        badges_html += f'<span class="badge">{g}</span>'

    match_html = ""
    if movie.get('score', 0) > 0:
        match_pct = int(movie['score'] * 100)
        match_html = f'<div class="match-score">{match_pct}% Match</div>'
    
    # 2. Render HTML
    # Note: We close the container div here, but visually the button below 
    # will appear to be part of the card due to CSS styling.
    st.markdown(f"""
    <div class="movie-card-container">
        <div class="poster-div">
            <img src="{poster_url}" class="poster-img" onerror="this.src='https://via.placeholder.com/500x750/1a1a2e/4CAF50?text=No+Poster'">
        </div>
        <div class="card-content">
            <div class="movie-title" title="{title}">{title}</div>
            <div class="badge-container">
                {badges_html}
            </div>
            <div class="meta-row">
                <div class="rating-badge">⭐ {vote_average}</div>
                {match_html}
            </div>
            <details>
                <summary>Read Plot</summary>
                <div class="overview-text">
                    {overview}
                </div>
            </details>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Native Button (Only ONE call!)
    # We use 'context' to ensure keys are unique between Search and Recommendation views
    st.button(
        "Find Similar 🔍", 
        key=f"btn_{context}_{movie['id']}_{idx}", 
        on_click=set_target_movie, 
        args=(movie['id'],),
        use_container_width=True
    )

# --- SIDEBAR FILTERS ---
with st.sidebar:
    st.header("⚙️ Preferences")
    
    # Form wrapper to prevent constant reloading
    with st.form("filter_form"):
        st.subheader("🎯 Refine Search")
        
        GENRE_NAME_TO_ID = {v: k for k, v in GENRE_MAP.items()}
        selected_genres = st.multiselect(
            "Genres", 
            options=sorted(GENRE_NAME_TO_ID.keys()),
            default=[]
        )
        genre_ids = [GENRE_NAME_TO_ID[name] for name in selected_genres]
        
        min_rating = st.slider("Min Rating", 0.0, 10.0, 5.0, 0.5)
        # Default range set wide to avoid "no results" error
        year_range = st.slider("Release Year", 1970, 2025, (1980, 2025))
        
        with st.expander("🔧 Advanced Sorting"):
            n_results = st.number_input("Results Count", 4, 40, 8, step=4)
            sort_by = st.selectbox("Sort By", ["relevance", "rating", "popularity", "newest"])
            boost_weight = st.slider("Popularity Boost", 0.0, 1.0, 0.1, help="Increase to favor popular movies")

        st.markdown("<br>", unsafe_allow_html=True)
        apply_btn = st.form_submit_button("Apply Filters", use_container_width=True)

    if st.button("🔄 Reset All", type="secondary", use_container_width=True):
        clear_target_movie()
        st.rerun()

# --- MAIN HERO & SEARCH ---
st.title("🎬 Cinematch AI")
st.markdown("##### Discover your next favorite movie with AI-powered recommendations")

# Search Bar - Wrapped in Form for performance
with st.form("search_form"):
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        query = st.text_input(
            "Search", 
            placeholder="e.g., 'time travel paradox with a twist ending'...", 
            label_visibility="collapsed"
        )
    with col2:
        search_submitted = st.form_submit_button("Search 🔍", use_container_width=True)

if search_submitted:
    clear_target_movie()

st.markdown("---")

# --- QUERY LOGIC ---

# Create cache key
cache_key = f"{query}_{genre_ids}_{year_range}_{min_rating}_{boost_weight}_{sort_by}_{n_results}"

with st.spinner("🎬 Analyzing thousands of movies..."):
    
    # MODE 1: Target Movie Selected (Find Similar)
    if st.session_state['target_movie_id']:
        
        # Back Button Logic
        c1, c2 = st.columns([0.8, 0.2])
        with c1:
            st.info(f"💡 Showing recommendations based on your selection")
        with c2:
            if st.button("✖ Clear Selection", use_container_width=True):
                clear_target_movie()
                st.rerun()
        
        # 1. Try Strict Search
        results = query_engine.find_similar_movies(
            movie_id=st.session_state['target_movie_id'],
            filters={
                "genres": genre_ids, 
                "year_range": year_range, 
                "min_rating": min_rating
            },
            n_results=n_results
        )

        # 2. Smart Fallback: If strict search fails, try broad search
        if not results:
            st.warning(f"⚠️ No matches found with your strict filters (Year: {year_range}, Rating > {min_rating}). Showing unfiltered similar movies instead.")
            results = query_engine.find_similar_movies(
                movie_id=st.session_state['target_movie_id'],
                filters={}, # Remove filters
                n_results=n_results
            )
            
        header_text = "🎯 Because you liked that..."

    # MODE 2: Search / Explore
    else:
        # Check Cache (only if not forcing new filters)
        if query and cache_key in st.session_state['search_cache'] and not apply_btn:
            results = st.session_state['search_cache'][cache_key]
        else:
            # Perform Search
            results = query_engine.search_movies(
                query=query if query else "",
                filters={
                    "genres": genre_ids, 
                    "year_range": year_range, 
                    "min_rating": min_rating
                },
                boost_weight=boost_weight,
                sort_by=sort_by,
                n_results=n_results
            )
            
            # Smart Fallback for Search too
            if not results and query:
                 st.warning("⚠️ No exact matches found. Broadening search parameters...")
                 results = query_engine.search_movies(
                    query=query,
                    filters={}, # Remove strict filters
                    boost_weight=boost_weight,
                    sort_by=sort_by,
                    n_results=n_results
                )

            # Update Cache
            if query:
                st.session_state['search_cache'][cache_key] = results
        
        header_text = f"🔍 Results for '{query}'" if query else "🔥 Trending Recommendations"


# --- GRID DISPLAY ---
st.subheader(header_text)

# Initialize results if not already set (safety check)
if 'results' not in locals():
    results = []

if not results:
    if 'query' in locals() and query:
        st.error("⚠️ No movies found even after broadening the search. Try a different search term.")
    else:
        st.info("👋 Welcome! Search for a plot or topic to get started.")
else:
    # 4 Columns Grid
    cols = st.columns(4, gap="medium")
    
    # Determine context for key uniqueness
    # "rec" = Recommendations view (Target Movie Selected)
    # "search" = Standard Search view
    current_context = "rec" if st.session_state.get('target_movie_id') else "search"
    
    for idx, movie in enumerate(results):
        with cols[idx % 4]:
            render_movie_card(movie, idx, context=current_context)

# --- FOOTER ---
st.markdown(
    '<div style="text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem;">'
    'Cinematch AI V2.3 | Enhanced Semantic Search & Filtering'
    '</div>', 
    unsafe_allow_html=True
)