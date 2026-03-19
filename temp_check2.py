import chromadb 
client = chromadb.PersistentClient(path='chroma_db') 
col = client.get_collection('cine_match_v1') 
result = col.get(where={'original_language': {'$eq': 'hi'}}, limit=5, include=['metadatas']) 
for m in result['metadatas']: 
    print(m['title'], m['original_language']) 
