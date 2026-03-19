
import chromadb
client = chromadb.PersistentClient(path='chroma_db')
col = client.get_collection('cine_match_v1')
result = col.get(limit=1, include=['metadatas'])
print(result['metadatas'][0].keys())
