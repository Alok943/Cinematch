from chroma_manager import get_collection
import re

def _normalize_title(text):
    """The ultimate normalization: strips articles, punctuation, AND spaces."""
    if not text: return ""
    text = text.lower().strip()
    text = re.sub(r'^(the|a|an)\s+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = text.replace(" ", "")   # 🔥 The critical fix
    return text

def run_migration():
    print("🎬 Starting DB Migration...")
    collection = get_collection()
    if not collection:
        print("❌ Could not connect to ChromaDB.")
        return

    # Note on your cut-off optimization: For massive DBs, you'd use limit/offset here. 
    # For a few thousand movies, pulling it into memory once is completely fine.
    data = collection.get(include=['metadatas'])
    ids = data['ids']
    metas = data['metadatas']
    updates = []
    
    # Debug counter
    print_count = 0

    for i in range(len(ids)):
        meta = metas[i]
        
        # Only update if it doesn't already have the normalized field
        if 'normalized_title' not in meta:
            original_title = meta.get('title', '')
            norm_title = _normalize_title(original_title)
            
            # Safety print for the first 5 updates
            if print_count < 5:
                print(f"🔍 DEBUG: '{original_title}' → '{norm_title}'")
                print_count += 1
                
            meta['normalized_title'] = norm_title
            updates.append((ids[i], meta))

    if updates:
        print(f"\n🔄 Updating {len(updates)} records in batches...")
        batch_size = 500
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            batch_ids = [x[0] for x in batch]
            batch_metas = [x[1] for x in batch]
            collection.update(ids=batch_ids, metadatas=batch_metas)
            print(f"   ... Processed {min(i + batch_size, len(updates))}/{len(updates)}")
            
        print("✅ Migration complete! Database is now strictly normalized.")
    else:
        print("⚡ DB is already normalized. No changes needed.")

if __name__ == "__main__":
    run_migration()