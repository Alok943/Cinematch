import sys
sys.path.append("./src")
from sentence_transformers import SentenceTransformer
from chroma_manager import get_collection

model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')
collection = get_collection()

query = "psychological thriller mind bending twist ending"
query_vector = model.encode(query).tolist()

target_titles = ["Shutter Island", "Gone Girl", "Memento", "Inception", "Black Swan", "Prisoners"]

results = collection.query(
    query_embeddings=[query_vector],
    n_results=500,
    include=['metadatas', 'distances']
)

print(f"Query: '{query}'\n")
for i, meta in enumerate(results['metadatas'][0]):
    if meta['title'] in target_titles:
        sim = round(1 - results['distances'][0][i], 3)
        print(f"  Rank {i+1:>3} | {meta['title']:<30} | sim={sim} | votes={meta['vote_count']}")