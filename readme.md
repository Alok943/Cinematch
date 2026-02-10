## 🚧 Limitations

### Current Known Issues

#### 1. **Semantic Understanding Gap**
- **Issue**: The system struggles to distinguish between literal and contextual word meanings
- **Examples**: 
  - Searching "Parasite" returns biological horror films instead of the Oscar-winning Korean thriller
  - "Lady Bird" matches films with "bird" in the title rather than similar coming-of-age dramas
  - "Die Hard" returns films with "die" in the title instead of action thrillers
- **Impact**: ~46% of test queries show this weakness

#### 2. **Title Token Over-Reliance**
- **Issue**: Heavy weighting on exact word matches in titles
- **Examples**:
  - "The Tree of Life" → matches any film with "tree" in title
  - "Amélie" → matches "Emmanuelle" series (completely different genre)
- **Impact**: Reduces thematic recommendation quality

#### 3. **International & Art House Film Accuracy**
- **Issue**: Lower accuracy for non-English and arthouse cinema
- **Examples**:
  - "Casablanca" returns random Italian films
  - "Citizen Kane" doesn't appear in top results for its own search
- **Impact**: ~20% accuracy drop for international titles

#### 4. **Genre Context Missing**
- **Issue**: Genre classification not used as a hard filter
- **Examples**:
  - Horror film queries sometimes return unrelated genres
  - Romance/drama confusion in edge cases
- **Impact**: User trust degradation

#### 5. **Cold Start Problem**
- **Issue**: New/obscure films with sparse data get poor recommendations
- **Impact**: Limited coverage for films with <10 ratings

### Performance Metrics

| Metric | Score |
|--------|-------|
| **Franchise Detection** | 95% ✅ |
| **Popular Films (>1000 ratings)** | 85% ✅ |
| **Niche/Art Films (<100 ratings)** | 30% ⚠️ |
| **Genre Coherence** | 60% ⚠️ |
| **Semantic Accuracy** | 35% ❌ |
| **Overall System Accuracy** | 65% |

---

## 🚀 Future Enhancements

### 🔥 High Priority (Quick Wins)

#### 1. **Semantic Analysis Integration**
```python