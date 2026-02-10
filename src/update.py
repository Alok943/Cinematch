import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
# 🔑 PASTE YOUR TMDB API KEY HERE
API_KEY = "9a7f2c468ef72e78bb6f619bea50488b"

# File path
FILE_PATH = "data/processed/movies_merged.csv"

def get_session():
    """
    Creates a requests session with automatic retries.
    Fixes the 'SSLError' and 'Max retries exceeded' issues.
    """
    session = requests.Session()
    retry = Retry(
        total=5,                # Try 5 times before failing
        backoff_factor=1,       # Wait 1s, 2s, 4s... between retries
        status_forcelist=[429, 500, 502, 503, 504], # Retry on these errors
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def check_database_status():
    """Checks the latest movie in the existing CSV."""
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found: {FILE_PATH}")
        return

    try:
        df = pd.read_csv(FILE_PATH)
        # Convert date column to datetime objects, handling errors
        df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
        
        # Drop rows where date is missing for accurate sorting
        valid_dates = df.dropna(subset=['release_date'])
        
        if valid_dates.empty:
            print("⚠️ Database has movies, but no valid release dates found.")
            return

        # Sort by date
        latest = valid_dates.sort_values(by='release_date', ascending=False).iloc[0]
        oldest = valid_dates.sort_values(by='release_date', ascending=True).iloc[0]
        
        print(f"\n📊 DATABASE REPORT")
        print(f"-------------------")
        print(f"Total Movies:   {len(df):,}")
        print(f"Oldest Movie:   {oldest['title']} ({oldest['release_date'].date()})")
        print(f"Latest Movie:   {latest['title']} ({latest['release_date'].date()})")
        print(f"-------------------")
    except Exception as e:
        print(f"⚠️ Error reading database: {e}")

def fetch_new_movies(pages_to_fetch=5):
    """
    Fetches Popular movies from TMDb with FULL metadata 
    (keywords, taglines, genres) to match your schema.
    Only adds movies with status='Released'.
    """
    session = get_session()
    print(f"\n🚀 Fetching {pages_to_fetch} pages of popular movies...")
    
    new_movies = []
    
    # 1. Loop through pages
    for page in range(1, pages_to_fetch + 1):
        url = f"https://api.themoviedb.org/3/movie/popular"
        params = {"api_key": API_KEY, "language": "en-US", "page": page}
        
        try:
            response = session.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"❌ Error fetching page {page}: {response.status_code}")
                continue
                
            results = response.json().get('results', [])
            print(f"   Processing Page {page}/{pages_to_fetch} ({len(results)} movies found)...")
            
            for movie in results:
                movie_id = movie['id']
                
                # 🛑 DETAILS FETCH: Call specific ID to get keywords/tagline AND STATUS
                details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                details_params = {"api_key": API_KEY, "append_to_response": "keywords"}
                
                try:
                    details_resp = session.get(details_url, params=details_params, timeout=5)
                    details = details_resp.json()
                    
                    # --- 🛡️ FILTER: STATUS CHECK ---
                    movie_status = details.get('status', 'Unknown')
                    if movie_status != 'Released':
                        # print(f"      ↪ Skipping '{movie.get('title')}' (Status: {movie_status})")
                        continue

                    # Extract Keywords
                    k_list = [k['name'] for k in details.get('keywords', {}).get('keywords', [])]
                    keywords_str = ", ".join(k_list)
                    
                    # Extract Genres
                    g_list = [g['name'] for g in details.get('genres', [])]
                    genres_str = ", ".join(g_list)

                    # Build the EXACT row structure needed for movies_clean.csv
                    row = {
                        "id": movie_id,
                        "title": movie.get('title'),
                        "overview": movie.get('overview'),
                        "genres": genres_str,
                        "vote_average": movie.get('vote_average'),
                        "vote_count": movie.get('vote_count'),
                        "release_date": movie.get('release_date'),
                        "poster_path": movie.get('poster_path'),
                        "tagline": details.get('tagline', ''),
                        "keywords": keywords_str,
                        "adult": movie.get('adult', False)
                    }
                    new_movies.append(row)
                    
                    # Small sleep to be nice to the API
                    time.sleep(0.38)
                    
                except Exception as e:
                    print(f"   Skipping movie ID {movie_id}: {e}")

        except Exception as e:
            print(f"❌ Connection error on page {page}: {e}")

    # 2. Save Data
    if new_movies:
        new_df = pd.DataFrame(new_movies)
        
        # Load existing if available to append
        if os.path.exists(FILE_PATH):
            try:
                existing_df = pd.read_csv(FILE_PATH)
                # Combine and remove duplicates based on ID
                combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['id'], keep='last')
            except:
                combined_df = new_df
        else:
            combined_df = new_df
            
        combined_df.to_csv(FILE_PATH, index=False)
        print(f"\n✅ SUCCESS! Database updated.")
        print(f"   Added/Updated {len(new_df)} RELEASED movies.")
        print(f"   Total movies now: {len(combined_df)}")
    else:
        print("❌ No new released movies fetched.")

# --- MENU ---
if __name__ == "__main__":
    print("1. Check Latest Movie in DB")
    print("2. Fetch New Popular Movies (Released Only)")
    choice = input("Enter choice (1 or 2): ")
    
    if choice == "1":
        check_database_status()
    elif choice == "2":
        try:
            p_input = input("How many pages to fetch? (Default 5): ")
            pages = int(p_input) if p_input.strip() else 5
            fetch_new_movies(pages)
        except ValueError:
            print("Invalid number.")