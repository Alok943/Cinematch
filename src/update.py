import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
API_KEY     = "9a7f2c468ef72e78bb6f619bea50488b"
BASE_PATH   = r"C:\Users\aloks\Desktop\Cinematch_V2\data\processed\movies_filtered.csv"
NEW_PATH    = r"C:\Users\aloks\Desktop\Cinematch_V2\data\raw\movies_new.csv"
OUTPUT_PATH = r"C:\Users\aloks\Desktop\Cinematch_V2\data\processed\movies_updated.csv"

def get_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def check_database_status():
    if not os.path.exists(BASE_PATH):
        print(f"❌ File not found: {BASE_PATH}")
        return
    try:
        df = pd.read_csv(BASE_PATH)
        df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
        valid_dates = df.dropna(subset=['release_date'])
        if valid_dates.empty:
            print("⚠️ No valid release dates found.")
            return
        latest = valid_dates.sort_values('release_date', ascending=False).iloc[0]
        oldest = valid_dates.sort_values('release_date', ascending=True).iloc[0]
        print(f"\n📊 DATABASE REPORT")
        print(f"-------------------")
        print(f"Total Movies : {len(df):,}")
        print(f"Oldest Movie : {oldest['title']} ({oldest['release_date'].date()})")
        print(f"Latest Movie : {latest['title']} ({latest['release_date'].date()})")
        print(f"-------------------")
    except Exception as e:
        print(f"⚠️ Error: {e}")

def fetch_new_movies(pages_to_fetch=5):
    session = get_session()
    print(f"\n🚀 Fetching {pages_to_fetch} pages of new movies (last 6 months)...")

    new_movies = []

    for page in range(1, pages_to_fetch + 1):
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": API_KEY,
            "language": "en-US",
            "page": page,
            "primary_release_date.gte": "2025-09-01",
            "primary_release_date.lte": "2026-03-18",
            "sort_by": "primary_release_date.desc"
        }

        try:
            response = session.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"❌ Error on page {page}: {response.status_code}")
                continue

            results = response.json().get('results', [])
            print(f"   Processing Page {page}/{pages_to_fetch} ({len(results)} movies)...")

            for movie in results:
                movie_id = movie['id']
                details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                details_params = {"api_key": API_KEY, "append_to_response": "keywords"}

                try:
                    details_resp = session.get(details_url, params=details_params, timeout=5)
                    details = details_resp.json()

                    k_list = [k['name'] for k in details.get('keywords', {}).get('keywords', [])]
                    g_list = [g['name'] for g in details.get('genres', [])]

                    row = {
                        "id":           movie_id,
                        "title":        movie.get('title'),
                        "overview":     movie.get('overview'),
                        "genres":       ", ".join(g_list),
                        "vote_average": movie.get('vote_average'),
                        "vote_count":   movie.get('vote_count'),
                        "release_date": movie.get('release_date'),
                        "poster_path":  movie.get('poster_path'),
                        "tagline":      details.get('tagline', ''),
                        "keywords":     ", ".join(k_list),
                        "adult":        movie.get('adult', False)
                    }
                    new_movies.append(row)
                    time.sleep(0.38)

                except Exception as e:
                    print(f"   Skipping movie ID {movie_id}: {e}")

        except Exception as e:
            print(f"❌ Connection error on page {page}: {e}")

    if new_movies:
        new_df = pd.DataFrame(new_movies)
        new_df.to_csv(NEW_PATH, index=False)
        print(f"\n✅ Fetched {len(new_df)} new movies → saved to movies_new.csv")
    else:
        print("❌ No movies fetched.")
def check_new_movies_status():
    if not os.path.exists(NEW_PATH):
        print(f"❌ movies_new.csv not found. Run option 2 first.")
        return
    try:
        df = pd.read_csv(NEW_PATH)
        df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
        valid = df.dropna(subset=['release_date'])
        latest = valid.sort_values('release_date', ascending=False).iloc[0]
        oldest = valid.sort_values('release_date', ascending=True).iloc[0]
        print(f"\n📊 NEW MOVIES REPORT")
        print(f"-------------------")
        print(f"Total Fetched: {len(df):,}")
        print(f"Oldest: {oldest['title']} ({oldest['release_date'].date()})")
        print(f"Latest: {latest['title']} ({latest['release_date'].date()})")
        print(f"-------------------")
    except Exception as e:
        print(f"⚠️ Error: {e}")
def merge_datasets():
    if not os.path.exists(BASE_PATH):
        print(f"❌ Base file not found: {BASE_PATH}")
        return
    if not os.path.exists(NEW_PATH):
        print(f"❌ New movies file not found. Run option 2 first.")
        return

    base_df = pd.read_csv(BASE_PATH)
    new_df  = pd.read_csv(NEW_PATH)

    before = len(base_df)
    combined = pd.concat([base_df, new_df]).drop_duplicates(subset=['id'], keep='last')
    after = len(combined)

    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ Merged!")
    print(f"   Base movies    : {before:,}")
    print(f"   New movies     : {len(new_df):,}")
    print(f"   Total (deduped): {after:,}")
    print(f"   Net new added  : {after - before:,}")
    print(f"   Saved to       : movies_updated.csv")

# --- MENU ---
if __name__ == "__main__":
    print("\n🎬 Cinematch Data Updater")
    print("==========================")
    print("1. Check Latest Movie in DB")
    print("2. Fetch New Movies (last 6 months)")
    print("3. Merge → movies_updated.csv")
    print("4. Check Fetched Movies")
    choice = input("\nEnter choice (1, 2, 3 or 4): ")

    if choice == "1":
        check_database_status()
    elif choice == "2":
        try:
            p_input = input("How many pages? (Default 5, max ~20 for 6 months): ")
            pages = int(p_input) if p_input.strip() else 5
            fetch_new_movies(pages)
        except ValueError:
            print("❌ Invalid number.")
    elif choice == "3":
        merge_datasets()
    elif choice == "4":          # ← ADD THIS
        check_new_movies_status()
    else:
        print("❌ Invalid choice.")