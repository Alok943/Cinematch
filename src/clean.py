import pandas as pd
from datetime import datetime
import os

FILE_PATH = "data/processed/movies_merged.csv"

def clean_future_movies():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found: {FILE_PATH}")
        return

    print("📂 Loading database...")
    df = pd.read_csv(FILE_PATH)
    
    # 1. Convert Date Column
    df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
    
    # 2. Define "Today"
    today = datetime.now()
    
    # 3. Filter Logic
    # Keep movies where release_date is in the past OR is null (some old movies have no date)
    # We remove strictly 'Future' dates.
    valid_movies = df[
        (df['release_date'] <= today) | 
        (df['release_date'].isna())
    ]
    
    removed_count = len(df) - len(valid_movies)
    
    if removed_count > 0:
        # 4. Save back to CSV
        valid_movies.to_csv(FILE_PATH, index=False)
        print(f"✅ CLEANUP COMPLETE!")
        print(f"   Removed {removed_count} movies from the future.")
        print(f"   New Total: {len(valid_movies)}")
        
        # Show examples of what was removed
        invalid = df[df['release_date'] > today]
        print("\n   Examples of removed movies:")
        print(invalid[['title', 'release_date']].head().to_string(index=False))
    else:
        print("✅ Database is already clean! No future movies found.")

if __name__ == "__main__":
    clean_future_movies()