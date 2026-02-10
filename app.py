import streamlit as st
import sys
import os

# Add 'src' to python path so we can import our modules
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

# --- CSS STYLING ---
st.markdown("""
    <style>
    .movie-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 20px;
        height: 100%;
        border: 1px solid #333;
    }
    .movie-title {
        font-weight: bold;
        font-size: 1.1em;
        margin-top: 10px;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .movie-meta {
        color: #AAA;
        font-size: 0.9em;
        margin-bottom: 10px;
    }
    .match-score {
        color: #4CAF50;
        font-weight: bold;
        font-size: 0.9em;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS & STATE ---

# Initialize state
if 'target_movie_id' not in st.session_state:
    st.session_state['target_movie_id'] = None

def clear_target_movie():
    """Reset the 'Find Similar' state when user searches manually"""
    st.session_state['target_movie_id'] = None

def set_target_movie(movie_id):
    """Callback to update session state for 'Find Similar'"""
    st.session_state['target_movie_id'] = movie_id

# --- SIDEBAR FILTERS ---
with st.sidebar:
    st.title("🎬 Cinematch")
    
    # 1. Search Bar
    query = st.text_input("Search Movies", placeholder="e.g., sad robots, heist movie...", on_change=clear_target_movie)
    
    st.markdown("---")
    
    # 2. Filters
    with st.expander("🔍 Filters", expanded=True):
        GENRE_MAP = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
            80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
            14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
            9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie",
            53: "Thriller", 10752: "War", 37: "Western"
        }
        GENRE_NAME_TO_ID = {v: k for k, v in GENRE_MAP.items()}
        
        selected_genres = st.multiselect("Genres", options=sorted(GENRE_NAME_TO_ID.keys()))
        genre_ids = [GENRE_NAME_TO_ID[name] for name in selected_genres]
        
        min_rating = st.slider("Minimum Rating", 0.0, 10.0, 0.0, 0.5)
        year_range = st.slider("Release Year", 1900, 2025, (1970, 2025))
        safe_search = st.toggle("Safe Search (Hide Adult)", value=False)

    st.markdown("---")

    # 3. Advanced Controls
    with st.expander("⚙️ Advanced", expanded=False):
        boost_weight = st.slider(
            "Popularity Boost", 0.0, 0.5, 0.0, 0.05, 
            help="Higher values favor popular movies over exact text matches."
        )
        sort_options = ["relevance", "rating", "popularity", "newest"]
        sort_by = st.selectbox("Sort By", sort_options, index=0)
        n_results = st.number_input("Results Count", 5, 50, 20)

    # 4. Database Status Footer
    st.markdown("---")
    valid, msg = chroma_manager.validate_database()
    if valid:
        stats = chroma_manager.get_collection_stats()
        st.caption(f"🟢 Database Active\n\nIndexed: {stats['count']:,} movies")
    else:
        st.error("🔴 Database Error")
        st.caption(msg)
        st.stop()

# --- MAIN SEARCH LOGIC ---

if st.session_state['target_movie_id']:
    # CASE 1: "Find Similar" Mode
    st.info(f"Showing movies similar to your selection. [Click here to clear](javascript:window.location.reload())")
    
    results = query_engine.find_similar_movies(
        movie_id=st.session_state['target_movie_id'],
        filters={
            "genres": genre_ids,
            "year_range": year_range,
            "min_rating": min_rating,
            "safe_search": safe_search
        },
        n_results=n_results
    )
    header_text = "More Like This..."

else:
    # CASE 2: Text Search Mode
    results = query_engine.search_movies(
        query=query,
        filters={
            "genres": genre_ids,
            "year_range": year_range,
            "min_rating": min_rating,
            "safe_search": safe_search
        },
        boost_weight=boost_weight,
        sort_by=sort_by,
        n_results=n_results
    )
    
    if query:
        header_text = f"Results for '{query}'"
    else:
        header_text = "Popular Movies"

# --- RE-RANKING (FIX FOR 'THE MARTIAN') ---
# This ensures exact title matches appear at the top
if results and query and not st.session_state['target_movie_id']:
    for movie in results:
        # Boost exact title match
        if query.lower().strip() == movie['title'].lower().strip():
             movie['score'] += 0.5
        # Boost partial starts-with match
        elif movie['title'].lower().startswith(query.lower().strip()):
             movie['score'] += 0.1
    
    # Re-sort if we are sorting by relevance
    if sort_by == "relevance":
        results = sorted(results, key=lambda x: x['score'], reverse=True)

# --- DISPLAY RESULTS ---
st.subheader(header_text)

if not results:
    st.warning("No movies found. Try adjusting your filters.")
else:
    cols = st.columns(4) 
    
    for idx, movie in enumerate(results):
        with cols[idx % 4]:
            # Poster Logic
            if movie['poster_path']:
                poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
            else:
                poster_url = "https://via.placeholder.com/500x750?text=No+Poster"
            
            st.image(poster_url, use_container_width=True)
            
            # Title & Metadata
            st.markdown(f"**{movie['title']}** ({movie['release_year']})")
            
            # Score Badge
            if movie['score'] > 0:
                st.caption(f"⭐ {movie['vote_average']} | Match: {int(movie['score']*100)}%")
            else:
                st.caption(f"⭐ {movie['vote_average']} | Votes: {movie['vote_count']}")
            
            # Button with Callback (FIXED)
            st.button(
                "Find Similar", 
                key=f"btn_{movie['id']}", 
                on_click=set_target_movie, 
                args=(movie['id'],)
            )
            
            # Overview Expander
            with st.expander("Overview"):
                st.write(movie['overview'])
                if movie.get('tagline'):
                    st.caption(f"_{movie['tagline']}_")