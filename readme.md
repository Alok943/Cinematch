# 🎬 Cinematch V2 — Intelligent Movie Search + Recommendation Engine

Cinematch V2 is a **hybrid movie recommender system** that combines **strict title search** with **semantic recommendations** to deliver accurate and relevant movie suggestions.

Unlike basic recommenders, Cinematch separates **search intent** from **discovery**, ensuring users always get the correct movie first — followed by meaningful recommendations.

---

## ✨ Key Highlights

* 🎯 **Two-Stage Retrieval System**

  * Stage 1: Exact & robust title matching (handles typos, punctuation)
  * Stage 2: Semantic recommendations using embeddings

* 🧠 **Smart Query Understanding**

  * Handles inputs like:

    * `"interstellar"` → returns exact movie + similar films
    * `"spiderman"` → correctly matches *Spider-Man*

* 🔍 **Semantic Search Engine**

  * Natural language queries like:

    * `"mind bending sci-fi"`
    * `"sad robot story"`

* 🎬 **Watch Trailer Integration**

  * TMDB-based trailers with YouTube fallback for missing results

* 🧹 **Noise Filtering System**

  * Removes irrelevant results using:

    * similarity thresholds
    * genre overlap constraints
    * duplicate filtering

* ⚖️ **Hybrid Ranking**

  * Combines:

    * semantic similarity
    * popularity (vote count)
    * recency (tie-breaker)

---

## 🏗️ System Architecture

```
User Query
   ↓
[Stage 1] Title Matching
   ↓
Top Result (Exact Movie)
   ↓
[Stage 2] Semantic Engine
   ↓
Similar Movies (Filtered + Ranked)
```

---

## 🧠 Core Design Philosophy

> “Search and Recommendation are NOT the same problem.”

Cinematch solves this by:

| Component       | Approach                          |
| --------------- | --------------------------------- |
| Title Search    | Strict + fallback (typo tolerant) |
| Recommendations | Pure embedding-based              |
| Ranking         | Similarity + popularity           |
| Filtering       | Genre-aware + threshold-based     |

---

## ⚙️ Tech Stack

* **Frontend**: Streamlit
* **Vector DB**: ChromaDB
* **Embeddings**: Sentence Transformers
* **Dataset**: TMDb (+ optional IMDb enrichment)

---

## 📊 Features Breakdown

### 🔍 1. Title Search (Robust)

* Handles:

  * `batman` → The Batman (2022)
  * `ironman` → Iron Man (2008)
  * `spiderman` → Spider-Man

### 🌌 2. Semantic Recommendations

* Based on:

  * plot similarity
  * genre overlap
  * embedding distance

### 🎯 3. Smart Filtering

* Genre
* Year range
* Rating
* Language

### 🎬 4. Trailer System

* TMDB API (primary)
* YouTube fallback (secondary)

---

## 📦 Installation

```bash
git clone https://github.com/yourusername/cinematch_v2.git
cd cinematch_v2

python -m venv venv
source venv/bin/activate  # or Windows equivalent

pip install -r requirements.txt
```

---

## 🗄️ Build Vector Database

```bash
cd src
python build_vector.py
```

---

## 🚀 Run the App

```bash
streamlit run app.py
```

---

## 🧪 Example Queries

| Query          | Output                            |
| -------------- | --------------------------------- |
| `interstellar` | Exact movie + similar space films |
| `spiderman`    | Correct franchise handling        |
| `sad robots`   | Emotional sci-fi movies           |
| `heist movie`  | Crime/thriller recommendations    |

---

## 🔥 What Makes This Project Stand Out

Most recommender systems:

* ❌ mix title + semantic search → noisy results
* ❌ fail on typos or variations

Cinematch:

* ✅ separates concerns (search vs recommend)
* ✅ handles real-world messy input
* ✅ delivers consistent results

---

## ⚠️ Limitations

* TMDB trailer coverage is incomplete (handled via fallback)
* No user personalization (content-based only)
* Depends on dataset quality

---

## 🚀 Future Improvements

* [ ] User preference learning (collaborative filtering)
* [ ] Better diversity in recommendations
* [ ] Multi-language support
* [ ] Watchlist / favorites system
* [ ] Deployment (Streamlit Cloud / AWS)

---

## 🙌 Acknowledgements

* TMDb (movie data & posters)
* ChromaDB (vector database)
* Sentence Transformers (embeddings)
* Streamlit (UI)

---

## 📌 Author

Built by **Alok Singh**
B.Tech AI & ML

---

## ⭐ Final Note

This project focuses on **real-world system design**, not just model building.

> Clean logic > complex models
