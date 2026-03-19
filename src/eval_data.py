# eval_data.py
# Evaluation dataset for Cinematch — no hardcoded expected lists.
# Claude judges results based on thematic relevance + rating >= 5.0

# --- SEARCH QUERIES (100 total) ---
SEARCH_QUERIES = [

    # --- GENRE: PSYCHOLOGICAL THRILLER (10) ---
    {"query": "psychological thriller mind bending twist ending"},
    {"query": "unreliable narrator mystery suspense"},
    {"query": "paranoia conspiracy thriller"},
    {"query": "serial killer detective cat and mouse"},
    {"query": "dark obsession revenge thriller"},
    {"query": "identity confusion psychological drama"},
    {"query": "trapped isolated location thriller"},
    {"query": "corrupt system whistleblower thriller"},
    {"query": "slow burn tension mystery"},
    {"query": "memory loss amnesia crime thriller"},

    # --- GENRE: HORROR (10) ---
    {"query": "supernatural horror haunted house ghost"},
    {"query": "found footage horror realistic"},
    {"query": "folk horror cult ritual"},
    {"query": "creature monster survival horror"},
    {"query": "psychological horror dread atmospheric"},
    {"query": "slasher teen horror classic"},
    {"query": "zombie apocalypse survival horror"},
    {"query": "possession demonic religious horror"},
    {"query": "body horror transformation grotesque"},
    {"query": "horror comedy dark funny scary"},

    # --- GENRE: SCI-FI (10) ---
    {"query": "space exploration science fiction epic"},
    {"query": "time travel paradox consequences"},
    {"query": "artificial intelligence robot consciousness"},
    {"query": "dystopian future society control"},
    {"query": "alien invasion first contact"},
    {"query": "simulation reality virtual world"},
    {"query": "genetic engineering biotech thriller"},
    {"query": "post apocalyptic survival sci fi"},
    {"query": "space western cowboys future"},
    {"query": "hard science fiction realistic physics"},

    # --- GENRE: ACTION (10) ---
    {"query": "spy espionage action covert operations"},
    {"query": "superhero marvel action ensemble"},
    {"query": "car chase street racing adrenaline"},
    {"query": "martial arts hand to hand combat"},
    {"query": "heist robbery crew planning execution"},
    {"query": "military special forces war action"},
    {"query": "assassin hitman contract killing"},
    {"query": "revenge action one man army"},
    {"query": "bank robbery crime thriller action"},
    {"query": "vigilante justice corruption fighting"},

    # --- GENRE: DRAMA (10) ---
    {"query": "emotional family drama grief loss"},
    {"query": "coming of age teenage growth identity"},
    {"query": "war historical epic sacrifice"},
    {"query": "courtroom legal drama justice"},
    {"query": "addiction recovery struggle drama"},
    {"query": "sports underdog inspirational triumph"},
    {"query": "romance forbidden love tragic"},
    {"query": "political drama power corruption"},
    {"query": "biopic real life inspiring figure"},
    {"query": "prison drama survival redemption"},

    # --- MOOD BASED (15) ---
    {"query": "feel good comedy friendship laughing"},
    {"query": "heartwarming family movie kids"},
    {"query": "dark gritty realistic crime"},
    {"query": "mind blowing ending shocking reveal"},
    {"query": "slow cinema meditative contemplative"},
    {"query": "non linear storytelling complex narrative"},
    {"query": "epic world building fantasy adventure"},
    {"query": "cozy mystery lighthearted detective"},
    {"query": "intense claustrophobic one location"},
    {"query": "bromance male friendship road trip"},
    {"query": "female led empowerment drama"},
    {"query": "quirky indie offbeat humor"},
    {"query": "tearjerker emotional devastating ending"},
    {"query": "feel good musical dance performance"},
    {"query": "based on true events real story crime"},

    # --- BOLLYWOOD / INDIAN CINEMA (20) ---
    {"query": "hindi romantic love story classic"},
    {"query": "bollywood action hero mass entertainer"},
    {"query": "india crime gangster dark thriller"},
    {"query": "hindi comedy friends college drama"},
    {"query": "bollywood family drama emotions"},
    {"query": "hindi biographical sports film"},
    {"query": "south indian action dubbed blockbuster"},
    {"query": "tamil thriller suspense crime"},
    {"query": "hindi horror supernatural ghost"},
    {"query": "bollywood musical dance celebration"},
    {"query": "indian social issue drama message"},
    {"query": "hindi revenge drama justice"},
    {"query": "bollywood coming of age youth"},
    {"query": "hindi war patriotic military"},
    {"query": "indian heist con man thriller"},
    {"query": "bollywood period historical epic"},
    {"query": "telugu mass action hero stylish"},
    {"query": "hindi dark comedy satirical"},
    {"query": "indian family reunion drama emotional"},
    {"query": "bollywood mystery whodunit detective"},

    # --- FRANCHISE / UNIVERSE (15) ---
    {"query": "batman dark knight dc comics"},
    {"query": "wizarding world magic school hogwarts"},
    {"query": "marvel cinematic universe crossover"},
    {"query": "star wars space opera jedi force"},
    {"query": "lord of the rings tolkien fantasy"},
    {"query": "fast furious street racing family crew"},
    {"query": "mission impossible spy action stunts"},
    {"query": "james bond 007 classic spy"},
    {"query": "john wick assassin gun fu action"},
    {"query": "pirates of the caribbean swashbuckler"},
    {"query": "jurassic park dinosaur science gone wrong"},
    {"query": "terminator time travel machine war"},
    {"query": "alien vs predator sci fi horror"},
    {"query": "indiana jones adventure archaeology"},
    {"query": "transformers robots action blockbuster"},
]

# --- SIMILAR MOVIES (40 total) ---
SIMILAR_MOVIES = [

    # --- SCI-FI ---
    {"source": "Interstellar"},
    {"source": "The Matrix"},
    {"source": "Inception"},
    {"source": "Arrival"},
    {"source": "Ex Machina"},
    {"source": "Blade Runner 2049"},
    {"source": "Gravity"},
    {"source": "The Martian"},

    # --- ACTION / THRILLER ---
    {"source": "The Dark Knight"},
    {"source": "Mad Max: Fury Road"},
    {"source": "John Wick"},
    {"source": "Heat"},
    {"source": "Casino Royale"},
    {"source": "The Bourne Identity"},
    {"source": "Sicario"},
    {"source": "No Country for Old Men"},

    # --- DRAMA ---
    {"source": "The Shawshank Redemption"},
    {"source": "Forrest Gump"},
    {"source": "Schindler's List"},
    {"source": "Good Will Hunting"},
    {"source": "A Beautiful Mind"},
    {"source": "The Pursuit of Happyness"},

    # --- HORROR ---
    {"source": "The Conjuring"},
    {"source": "Hereditary"},
    {"source": "Get Out"},
    {"source": "A Quiet Place"},
    {"source": "Midsommar"},

    # --- COMEDY ---
    {"source": "The Hangover"},
    {"source": "Superbad"},
    {"source": "Game Night"},

    # --- ANIMATED ---
    {"source": "Toy Story"},
    {"source": "Spirited Away"},
    {"source": "Up"},
    {"source": "WALL-E"},

    # --- BOLLYWOOD ---
    {"source": "Dilwale Dulhania Le Jayenge"},
    {"source": "3 Idiots"},
    {"source": "Gangs of Wasseypur"},
    {"source": "Andhadhun"},
    {"source": "Dangal"},
    {"source": "PK"},
]