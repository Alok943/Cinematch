import query_engine
import chroma_manager
import sys

def print_header(title):
    print(f"\n{'='*60}")
    print(f"TEST: {title}")
    print(f"{'='*60}")

def test_connection():
    print_header("1. Database Connection & Collection Name")
    exists, msg = chroma_manager.validate_database()
    print(f"Status: {msg}")
    
    if not exists:
        print("❌ CRITICAL: Database not found. Cannot proceed.")
        sys.exit(1)
    
    stats = chroma_manager.get_collection_stats()
    print(f"Collection Count: {stats['count']}")
    
    # Verify Collection Name implicitly by success of above
    print("✅ Connection Successful.")

def test_distance_conversion():
    print_header("2. Distance vs Similarity Sanity Check")
    print("running search for 'love' to trigger your debug prints...")
    
    # This query triggers the _process_results function
    # WATCH YOUR CONSOLE OUTPUT for the "DEBUG: Sample distances" lines you added.
    results = query_engine.search_movies("love", n_results=3)
    
    if results:
        top_score = results[0]['score']
        print(f"\nTop Result: {results[0]['title']}")
        print(f"Score: {top_score}")
        
        if top_score > 1.0 or top_score < 0.0:
            print(f"❌ ERROR: Score {top_score} is out of bounds (0-1). Distance logic likely wrong.")
        else:
            print("✅ Score is within valid bounds (0.0 - 1.0).")
            print("👉 CHECK CONSOLE ABOVE: If 'Sample distances' were ~0.3-0.8, you are good.")
            print("👉 If 'Sample distances' were > 1.0 or < 0, logic is wrong.")

def test_empty_query_fallback():
    print_header("3. Empty Query (Popularity Fallback)")
    print("Searching with query='' (Should return popular movies)...")
    
    results = query_engine.search_movies("", n_results=5)
    
    if not results:
        print("❌ FAILED: No results returned for empty query.")
        return

    # Verify sorting by vote_count
    votes = [r['vote_count'] for r in results]
    print(f"Vote Counts returned: {votes}")
    
    is_sorted = all(votes[i] >= votes[i+1] for i in range(len(votes)-1))
    
    if is_sorted:
        print("✅ SUCCESS: Results are sorted by popularity (vote_count).")
    else:
        print("❌ FAILED: Results are NOT sorted by vote_count.")

def test_sorting_logic():
    print_header("4. Sort By 'Rating'")
    print("Searching 'action', sort_by='rating'...")
    
    results = query_engine.search_movies("action", sort_by="rating", n_results=5)
    
    if not results:
        print("⚠️ No results found to test sorting.")
        return

    ratings = [r['vote_average'] for r in results]
    votes = [r['vote_count'] for r in results]
    
    print(f"Ratings: {ratings}")
    print(f"Votes:   {votes}")
    
    # Check 1: Ratings are descending
    is_sorted = all(ratings[i] >= ratings[i+1] for i in range(len(ratings)-1))
    
    # Check 2: Vote count threshold (>100)
    min_votes_ok = all(v > 100 for v in votes)
    
    if is_sorted and min_votes_ok:
        print("✅ SUCCESS: Results sorted by rating AND verify vote_count > 100.")
    elif not min_votes_ok:
        print("❌ FAILED: Found movies with < 100 votes (Filter failed).")
    else:
        print("❌ FAILED: Ratings are not sorted descending.")

def test_min_rating_filter():
    print_header("5. Min Rating Filter (>= 8.0)")
    
    results = query_engine.search_movies("movie", filters={"min_rating": 8.0}, n_results=5)
    
    if not results:
        print("⚠️ No results found > 8.0 (might be valid).")
        return
        
    ratings = [r['vote_average'] for r in results]
    print(f"Result Ratings: {ratings}")
    
    if all(r >= 8.0 for r in ratings):
        print("✅ SUCCESS: All results are >= 8.0.")
    else:
        print("❌ FAILED: Found results with rating < 8.0.")

if __name__ == "__main__":
    try:
        test_connection()
        test_distance_conversion()
        test_empty_query_fallback()
        test_sorting_logic()
        test_min_rating_filter()
        print("\n✅✅ VERIFICATION COMPLETE ✅✅")
    except Exception as e:
        print(f"\n❌ SCRIPT CRASHED: {e}")
        import traceback
        traceback.print_exc()