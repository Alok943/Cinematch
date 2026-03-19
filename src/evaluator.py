# evaluator.py
# Prints results for each query/source in a structured format.
# Claude judges relevance (theme match + rating >= 5.0) and computes metrics.

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from query_engine import search_movies, find_similar_movies
from chroma_manager import get_collection
from eval_data import SEARCH_QUERIES, SIMILAR_MOVIES

K = 10  # Top 10 results per query

# --- HELPER: Look up movie ID by title ---
def get_movie_id_by_title(title):
    collection = get_collection()
    if not collection:
        return None
    try:
        results = collection.get(
            where={"title": {"$eq": title}},
            include=["metadatas"],
            limit=1
        )
        if results["ids"]:
            return results["ids"][0]
        return None
    except Exception as e:
        print(f"   ⚠️ Could not find '{title}': {e}")
        return None

# --- EVALUATE SEARCH ---
def evaluate_search():
    print("\n" + "="*70)
    print("🔍 SEARCH RESULTS — Paste these to Claude for judgement")
    print("="*70)

    for idx, item in enumerate(SEARCH_QUERIES):
        query = item["query"]
        results = search_movies(query=query, filters={}, boost_weight=0.3, n_results=K)

        print(f"\n[S{idx+1}] Query: \"{query}\"")
        if not results:
            print("   ⚠️ No results returned")
            continue
        for rank, r in enumerate(results, 1):
            print(f"   {rank:>2}. {r['title']} ({r.get('release_year', '?')}) | ⭐ {r.get('vote_average', 0):.1f}")

# --- EVALUATE RECOMMENDATIONS ---
def evaluate_recommendations():
    print("\n" + "="*70)
    print("🎯 RECOMMENDATION RESULTS — Paste these to Claude for judgement")
    print("="*70)

    for idx, item in enumerate(SIMILAR_MOVIES):
        source_title = item["source"]
        movie_id = get_movie_id_by_title(source_title)

        print(f"\n[R{idx+1}] Source: \"{source_title}\"")

        if not movie_id:
            print("   ⚠️ Source movie not found in DB — skipping")
            continue

        results = find_similar_movies(movie_id=movie_id, filters={}, n_results=K)
        if not results:
            print("   ⚠️ No results returned")
            continue

        for rank, r in enumerate(results, 1):
            print(f"   {rank:>2}. {r['title']} ({r.get('release_year', '?')}) | ⭐ {r.get('vote_average', 0):.1f}")

# --- MAIN ---
if __name__ == "__main__":
    print("\n🎬 Cinematch Evaluation — Output for Claude Judgement")
    print(f"   K = {K} | Judgement: theme relevance + rating >= 5.0")
    evaluate_search()
    evaluate_recommendations()
    print("\n\n✅ Done. Paste this output to Claude for scoring.")