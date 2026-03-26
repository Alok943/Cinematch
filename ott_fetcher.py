# ott_fetcher.py

import requests
import streamlit as st
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


REGION = "IN"

# Use a string label, not the key itself
TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_watch_providers(movie_id: int) -> list[dict]:
    """
    Fetches streaming providers for a movie in India.
    Returns a list of dicts: [{"name": "Netflix", "logo": "/path.png"}, ...]
    Returns empty list if unavailable or error.
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
    params = {"api_key": TMDB_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=10,verify = False)
        response.raise_for_status()
        data = response.json()

        # Drill into India -> flatrate (subscription)
        india_data = data.get("results", {}).get(REGION, {})
        providers = india_data.get("flatrate", [])  # subscription services only

        return [
            {
                "name": p["provider_name"],
                "logo": f"https://image.tmdb.org/t/p/original{p['logo_path']}"
            }
            for p in providers
            if p.get("logo_path") and p.get("provider_name")
        ]
    except requests.exceptions.SSLError:
        return[]
    except requests.exceptions.ConnectionError:
        return[]
    except Exception as e:
        print(f"OTT fetch error for movie {movie_id}: {e}")
        return []
    
@st.cache_data(ttl=3600)
def get_trailer_key_youtube(movie_title: str, release_year: int = None) -> str:
    """
    Searches YouTube Data API for a movie trailer.
    Falls back to TMDB if not found.
    """
    query = f"{movie_title} official trailer"
    if release_year:
        query += f" {release_year}"

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 3,
        "key": YOUTUBE_API_KEY,
        "videoDefinition": "high",
    }

    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        for item in items:
            video_id = item["id"].get("videoId")
            title_lower = item["snippet"]["title"].lower()
            # Prefer results that mention 'trailer' in title
            if video_id and "trailer" in title_lower:
                return video_id

        # Fallback: return first result regardless
        if items:
            return items[0]["id"].get("videoId")

        return None

    except Exception as e:
        print(f"YouTube trailer fetch error for '{movie_title}': {e}")
        return None
       
@st.cache_data(ttl=3600)
def get_trailer_key(movie_id: int) -> str:
    """
    Fetches the official YouTube trailer key for a movie.
    Returns YouTube video key (e.g. 'dQw4w9WgXcQ') or None if not found.
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
    params = {"api_key": TMDB_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()

        videos = data.get("results", [])

        # Priority: Official Trailer first, then any Trailer, then any video
        for video in videos:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer" and video.get("official"):
                return video["key"]

        for video in videos:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return video["key"]

        for video in videos:
            if video.get("site") == "YouTube":
                return video["key"]

        return None

    except requests.exceptions.SSLError:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        print(f"Trailer fetch error for movie {movie_id}: {e}")
        return None