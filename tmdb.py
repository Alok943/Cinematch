import pandas as pd
import requests
import time
import os

# --- CONFIGURATION ---
# 🔑 PASTE YOUR TMDB API KEY HERE
API_KEY = "9a7f2c468ef72e78bb6f619bea50488b"

# File paths
INPUT_FILE = "data/processed/movies_merged.csv"
OUTPUT_FILE = "data/processed/movies_clean_updated.csv"

def fetch_missing_posters():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Could not find file at {INPUT_FILE}")
        return

    print(f"📂 Loading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # 1. Identify rows with missing posters
    # We look for NaNs or empty strings
    mask = df['poster_path'].isna() | (df['poster_path'].astype(str).str.strip() == "")
    missing_indices = df[mask].index
    
    total_missing = len(missing_indices)
    print(f"🔍 Found {total_missing} movies with missing posters.")
    
    if total_missing == 0:
        print("✅ No missing posters found! Exiting.")
        return

    print("🚀 Starting fetch process... (This may take a while due to rate limits)")
    
    # Header for the table
    print(f"{'IDX':<8} | {'STATUS':<10} | {'MOVIE TITLE'}")
    print("-" * 50)

    updated_count = 0
    
    # 2. Iterate and Fetch
    for i, idx in enumerate(missing_indices):
        row = df.loc[idx]
        title = row['title']
        
        # Try to extract year from release_date (format YYYY-MM-DD)
        year = None
        if pd.notna(row['release_date']):
            try:
                year = str(row['release_date']).split('-')[0]
            except:
                pass

        # Call TMDb API
        new_poster = search_tmdb_poster(title, year)
        
        if new_poster:
            df.at[idx, 'poster_path'] = new_poster
            updated_count += 1
            print(f"{i+1}/{total_missing:<4} | ✅ FOUND   | {title}")
        else:
            print(f"{i+1}/{total_missing:<4} | ❌ NO DATA | {title}")
            
        # ⚠️ RATE LIMITING: Sleep to avoid getting banned
        # TMDb allows ~4 requests per second. We sleep 0.25s to be safe.
        time.sleep(0.33)
        
        # Save progress every 50 records just in case
        if (i + 1) % 50 == 0:
            df.to_csv(OUTPUT_FILE, index=False)
            print(f"💾 ...Progress saved to {OUTPUT_FILE}...")

    # 3. Final Save
    df.to_csv(OUTPUT_FILE, index=False)
    print("\n" + "="*50)
    print(f"🎉 DONE!")
    print(f"Total processed: {total_missing}")
    print(f"Posters found:   {updated_count}")
    print(f"📁 Updated file saved to: {OUTPUT_FILE}")
    print("="*50)
    print("👉 Next Step: Rename 'movies_clean_updated.csv' to 'movies_clean.csv' after verification.")

def search_tmdb_poster(title, year=None):
    """
    Searches TMDb for a movie and returns the poster_path of the first result.
    """
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key":API_KEY,
        "query": title,
        "include_adult": "true"
    }
    if year:
        params["year"] = year # Helps narrow down results (e.g. 'The Martian' 2015 vs 1970)

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                # Return the poster path of the most relevant result
                return data['results'][0].get('poster_path')
    except Exception as e:
        print(f"   ⚠️ API Error: {e}")
    
    return None

if __name__ == "__main__":
    fetch_missing_posters()