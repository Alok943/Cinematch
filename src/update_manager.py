import sys
sys.path.append("./src")
from chroma_manager import get_collection

collection = get_collection()

# Check if these obviously missing movies are in DB
test_titles = [
    "Shutter Island",
    "Gone Girl", 
    "Memento",
    "Black Swan",
    "Inception",
    "Prisoners"
]

for title in test_titles:
    result = collection.get(
        where={"title": {"$eq": title}},
        include=["metadatas"],
        limit=1
    )
    if result["ids"]:
        meta = result["metadatas"][0]
        print(f"✅ {title} | Rating: {meta['vote_average']} | Year: {meta['release_year']}")
    else:
        print(f"❌ {title} — NOT IN DB")
test_titles = [
    "Shutter Island",
    "Gone Girl",
    "Memento"
]

for title in test_titles:
    result = collection.get(
        where={"title": {"$eq": title}},
        include=["metadatas", "documents"],
        limit=1
    )
    if result["ids"]:
        print(f"\n{'='*60}")
        print(f"🎬 {title}")
        print(f"Document (super-string):\n{result['documents'][0]}")