# 검색 가이드 (Search Guide)

## 🔍 검색이란?

크롤링으로 수집한 연구실 정보에서 원하는 내용을 찾는 과정입니다.

**이 시스템의 특징:**
- 키워드 정확 매칭이 아닌 **의미 기반 검색**
- "AI"로 검색 → "인공지능", "머신러닝", "딥러닝" 모두 찾음
- 벡터 유사도 기반 검색

## 🚀 빠른 시작

### 대화형 검색 (추천)

```bash
cd src
python search_local.py
```

**사용 예시:**
```
🔍 검색어를 입력하세요 (종료: quit): 컴퓨터 비전

검색 결과 (상위 5개):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] AI 연구실 (홍길동 교수) - 점수: 0.856
📄 섹션: research
우리 연구실은 컴퓨터 비전과 딥러닝을 연구합니다...

[2] 비전 연구실 (김철수 교수) - 점수: 0.823
📄 섹션: about
영상 처리 및 이미지 인식 기술을 개발합니다...

...

🔍 검색어를 입력하세요 (종료: quit): quit
```

### 단일 검색

```bash
cd src
python search_local.py --mode search --query "딥러닝" --limit 10
```

## 📊 검색 모드

### 1. 대화형 모드 (기본)

```bash
python search_local.py
```

계속해서 검색어를 입력할 수 있습니다.

### 2. 단일 검색 모드

```bash
python search_local.py --mode search --query "검색어" --limit 5
```

**옵션:**
- `--query`: 검색어
- `--limit`: 결과 개수 (기본값: 5)

### 3. 통계 모드

```bash
python search_local.py --mode stats
```

**출력 예시:**
```
📊 데이터베이스 통계
━━━━━━━━━━━━━━━━━━
연구실: 5개
문서: 23개
평균 품질 점수: 0.78

섹션 분포:
  about: 5개 (22%)
  research: 8개 (35%)
  publication: 6개 (26%)
  project: 3개 (13%)
  join: 1개 (4%)

언어 분포:
  ko: 15개 (65%)
  en: 5개 (22%)
  mixed: 3개 (13%)
```

## 🔧 검색 원리

### 벡터 검색 프로세스

```
1. 검색어 입력
   "컴퓨터 비전"
   ↓
2. 검색어를 벡터로 변환 (임베딩)
   [0.123, -0.456, 0.789, ..., 0.234]
   ↓
3. 모든 문서 벡터와 유사도 계산 (코사인 유사도)
   문서1: 0.856 ← 매우 유사
   문서2: 0.823
   문서3: 0.421
   문서4: 0.156
   ...
   ↓
4. 유사도 순 정렬 및 상위 N개 반환
```

### 코사인 유사도

두 벡터가 얼마나 비슷한지 측정합니다:

```
유사도 1.0 = 완전 동일한 의미
유사도 0.8 = 매우 유사
유사도 0.5 = 보통 유사
유사도 0.0 = 전혀 다름
```

**계산 방법:**
```python
def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)
```

## 💻 Python 코드로 검색

### 기본 검색

```python
from local_storage import LocalVectorStore
from embedding import EmbeddingPipeline

# 초기화
store = LocalVectorStore('./crawl_data')
pipeline = EmbeddingPipeline()

# 검색어를 벡터로 변환
query = "컴퓨터 비전과 딥러닝"
query_emb = pipeline.embed(query)

# 검색
results = store.search_vector(
    query_embedding=query_emb.embedding,
    limit=5
)

# 결과 출력
for i, result in enumerate(results, 1):
    print(f"\n[{i}] {result.lab_name} - 점수: {result.score:.3f}")
    print(f"섹션: {result.section}")
    print(f"텍스트: {result.text[:100]}...")
```

### 필터링 검색

```python
# 특정 섹션만 검색
results = store.search_vector(
    query_embedding=query_emb.embedding,
    limit=5,
    section_filter='research'  # 연구 분야만
)

# 품질 점수 필터
results = store.search_vector(
    query_embedding=query_emb.embedding,
    limit=5,
    min_quality=0.7  # 품질 0.7 이상만
)

# 언어 필터
results = store.search_vector(
    query_embedding=query_emb.embedding,
    limit=5,
    lang_filter='ko'  # 한글만
)
```

### 복합 필터

```python
results = store.search_vector(
    query_embedding=query_emb.embedding,
    limit=10,
    section_filter='research',
    min_quality=0.6,
    lang_filter='ko'
)
```

## 🗄️ PostgreSQL 검색 (고급)

### 벡터 검색

```python
from vector_db import VectorDatabase, DatabaseConfig

# DB 연결
db_config = DatabaseConfig(
    host='localhost',
    port=5432,
    database='labsearch',
    user='postgres',
    password='your_password'
)
db = VectorDatabase(db_config)

# 검색어 임베딩
pipeline = EmbeddingPipeline()
query_emb = pipeline.embed("딥러닝 연구")

# 벡터 검색
results = db.search_vector(
    query_embedding=query_emb.embedding,
    limit=10,
    min_quality=70  # 품질 점수 70% 이상
)

for r in results:
    print(f"[{r.lab_name}] {r.title}")
    print(f"  점수: {r.score:.3f}")
    print(f"  텍스트: {r.text[:100]}...")
```

### 하이브리드 검색 (벡터 + 키워드)

벡터 검색과 키워드 검색을 결합합니다:

```python
results = db.search_hybrid(
    query_text="컴퓨터 비전",  # 키워드
    query_embedding=query_emb.embedding,  # 벡터
    limit=10,
    vector_weight=0.7,    # 벡터 가중치 70%
    keyword_weight=0.3    # 키워드 가중치 30%
)

for r in results:
    print(f"{r.lab_name}: hybrid={r.score:.3f}")
    print(f"  벡터={r.vector_score:.3f}, 키워드={r.keyword_score:.3f}")
```

**하이브리드 점수 계산:**
```
hybrid_score = (vector_score × 0.7) + (keyword_score × 0.3)
```

### SQL로 직접 검색

```sql
-- 벡터 검색 (상위 10개)
SELECT 
    l.name as lab_name,
    d.section,
    d.text,
    1 - (d.embedding <=> %s::vector) as similarity
FROM lab_docs d
JOIN lab l ON d.lab_id = l.lab_id
WHERE d.is_active = TRUE
ORDER BY d.embedding <=> %s::vector
LIMIT 10;

-- 하이브리드 검색 (벡터 + 키워드)
SELECT * FROM hybrid_search(
    query_text := '컴퓨터 비전',
    query_embedding := %s::vector,
    result_limit := 10,
    vec_weight := 0.7,
    kw_weight := 0.3
);
```

## 🎯 검색 최적화

### 1. 검색어 작성 팁

#### 좋은 검색어 ✅
```
"컴퓨터 비전과 딥러닝"
"자연어 처리 연구"
"로봇 제어 알고리즘"
"무선 통신 네트워크"
```

#### 나쁜 검색어 ❌
```
"연구실"  ← 너무 일반적
"교수님"  ← 의미 없음
"ㅋㅋ"    ← 특수 문자
```

### 2. 검색 결과 개수 조정

```python
# 소량 검색 (빠름)
results = store.search_vector(query_emb.embedding, limit=5)

# 대량 검색 (느림)
results = store.search_vector(query_emb.embedding, limit=50)
```

**권장:**
- 일반 사용: limit=5-10
- 상세 검색: limit=20-30
- 전체 검색: limit=50+

### 3. 품질 필터 활용

```python
# 고품질 문서만
results = store.search_vector(
    query_emb.embedding,
    limit=10,
    min_quality=0.8  # 품질 80% 이상
)

# 중저품질 포함
results = store.search_vector(
    query_emb.embedding,
    limit=10,
    min_quality=0.5  # 품질 50% 이상
)
```

## 🔍 검색 메타데이터 활용

### Signals (재랭킹)

검색 결과를 재정렬하는 추가 신호:

```python
# 논문 수가 많은 연구실 우선
results = db.search_vector(query_emb.embedding, limit=20)
results_sorted = sorted(
    results,
    key=lambda r: (r.score, r.recent_papers_count),
    reverse=True
)

# GPU 장비가 많은 연구실 우선
results_sorted = sorted(
    results,
    key=lambda r: (r.score, r.equipment_gpu),
    reverse=True
)
```

### Constraints (필터링)

모집 조건으로 필터링:

```sql
-- 주말 가능한 연구실만
SELECT * FROM search_vector_with_constraints(
    query_embedding := %s::vector,
    weekend_required := TRUE,
    max_hours := 10
);
```

### Provenance (추천 이유)

왜 이 연구실이 추천되었는지 표시:

```python
for result in results:
    print(f"[{result.lab_name}]")
    print(f"추천 이유: {result.matched_snippet}")
    print(f"점수: {result.score:.3f}")
```

## 🌐 REST API 사용 (고급)

### API 서버 시작

```bash
cd src
uvicorn search_api:app --reload --port 8000
```

### 엔드포인트

#### 1. 벡터 검색

```bash
# GET /search
curl "http://localhost:8000/search?q=컴퓨터 비전&limit=5"
```

**응답:**
```json
{
  "query": "컴퓨터 비전",
  "results": [
    {
      "lab_name": "AI 연구실",
      "professor": "홍길동",
      "section": "research",
      "text": "우리는 컴퓨터 비전을...",
      "score": 0.856,
      "quality_score": 0.85
    }
  ],
  "count": 5
}
```

#### 2. 하이브리드 검색

```bash
# GET /search/hybrid
curl "http://localhost:8000/search/hybrid?q=딥러닝&limit=5&vector_weight=0.7&keyword_weight=0.3"
```

#### 3. 통계

```bash
# GET /stats
curl "http://localhost:8000/stats"
```

**응답:**
```json
{
  "total_labs": 5,
  "total_docs": 23,
  "avg_quality_score": 0.78,
  "section_distribution": {
    "about": 5,
    "research": 8,
    "publication": 6
  }
}
```

### Python으로 API 호출

```python
import requests

# 검색
response = requests.get(
    "http://localhost:8000/search",
    params={"q": "컴퓨터 비전", "limit": 5}
)
results = response.json()

for r in results['results']:
    print(f"{r['lab_name']}: {r['score']:.3f}")
```

### JavaScript로 API 호출

```javascript
fetch('http://localhost:8000/search?q=컴퓨터 비전&limit=5')
  .then(res => res.json())
  .then(data => {
    data.results.forEach(r => {
      console.log(`${r.lab_name}: ${r.score}`);
    });
  });
```

## 📊 검색 결과 분석

### 결과 저장

```python
import pandas as pd

# 검색 결과를 DataFrame으로 변환
df = pd.DataFrame([
    {
        'lab_name': r.lab_name,
        'professor': r.professor,
        'section': r.section,
        'score': r.score,
        'quality': r.quality_score
    }
    for r in results
])

# CSV로 저장
df.to_csv('search_results.csv', index=False, encoding='utf-8-sig')

# Excel로 저장
df.to_excel('search_results.xlsx', index=False)
```

### 시각화

```python
import matplotlib.pyplot as plt

# 점수 분포
df['score'].hist(bins=20)
plt.xlabel('Similarity Score')
plt.ylabel('Count')
plt.title('Search Result Score Distribution')
plt.show()

# 섹션별 결과
df['section'].value_counts().plot(kind='bar')
plt.xlabel('Section')
plt.ylabel('Count')
plt.title('Results by Section')
plt.show()
```

## 🐛 문제 해결

### 문제 1: "검색 결과가 없음"

**원인:**
- 데이터가 크롤링되지 않음
- 검색어가 너무 구체적

**해결:**
```bash
# 데이터 확인
python search_local.py --mode stats

# 결과가 0이면 크롤링 필요
cd src
python main_pipeline.py
```

### 문제 2: "검색이 느림"

**원인:**
- 로컬 모드는 문서가 많으면 느림
- 임베딩 계산 시간

**해결:**
```python
# PostgreSQL 모드 사용 (HNSW 인덱스로 빠름)
USE_LOCAL = False

# 또는 결과 개수 줄이기
limit = 5  # 50에서 줄임
```

### 문제 3: "검색 결과가 이상함"

**원인:**
- 임베딩 모델 문제
- 품질 낮은 문서

**해결:**
```python
# 품질 필터 적용
results = store.search_vector(
    query_emb.embedding,
    min_quality=0.7
)

# 다른 임베딩 모델 시도
pipeline = EmbeddingPipeline(
    model_name='multilingual-e5-large'
)
```

### 문제 4: "API 서버 오류"

**원인:**
- 포트 충돌
- 의존성 미설치

**해결:**
```bash
# FastAPI 설치 확인
pip install fastapi uvicorn

# 다른 포트 사용
uvicorn search_api:app --port 8001
```

## 💡 고급 검색 기법

### 1. 다중 쿼리 검색

여러 검색어의 평균 벡터로 검색:

```python
queries = ["컴퓨터 비전", "딥러닝", "이미지 인식"]

# 각 쿼리의 벡터 계산
query_embeddings = [pipeline.embed(q).embedding for q in queries]

# 평균 벡터
avg_embedding = np.mean(query_embeddings, axis=0)

# 검색
results = store.search_vector(avg_embedding, limit=10)
```

### 2. 부정 검색

특정 주제를 제외:

```python
# "AI 연구"는 원하지만 "로봇"은 제외
positive = pipeline.embed("AI 연구").embedding
negative = pipeline.embed("로봇").embedding

# 가중 벡터
query_emb = positive - 0.3 * negative

results = store.search_vector(query_emb, limit=10)
```

### 3. 섹션별 가중치

```python
# research 섹션에 가중치
results_research = store.search_vector(
    query_emb.embedding,
    section_filter='research'
)

# about 섹션에 가중치
results_about = store.search_vector(
    query_emb.embedding,
    section_filter='about'
)

# 결합 (research 70%, about 30%)
combined = (
    [(r, r.score * 0.7) for r in results_research] +
    [(r, r.score * 0.3) for r in results_about]
)
combined_sorted = sorted(combined, key=lambda x: x[1], reverse=True)
```

## 📈 검색 로그 분석 (PostgreSQL)

### 검색 이력 조회

```sql
-- 인기 검색어
SELECT 
    query,
    COUNT(*) as search_count,
    AVG(avg_score) as avg_score
FROM search_log
GROUP BY query
ORDER BY search_count DESC
LIMIT 20;

-- 검색 성능
SELECT 
    query,
    AVG(result_count) as avg_results,
    AVG(avg_score) as avg_score
FROM search_log
WHERE searched_at >= NOW() - INTERVAL '7 days'
GROUP BY query;
```

## ✅ 검색 체크리스트

- [ ] 크롤링 완료 (crawling.md)
- [ ] 검색 스크립트 실행 확인
- [ ] 검색어 작성 방법 이해
- [ ] 필터링 옵션 활용
- [ ] (선택) API 서버 설정
- [ ] (선택) 검색 결과 분석

## 🎯 다음 단계

검색 사용법을 익혔다면:

1. **[architecture.md](architecture.md)** - 시스템 구조 이해
2. **커스텀 검색** - 자신만의 검색 로직 개발
3. **웹 인터페이스** - 검색 UI 개발

검색을 마스터하셨습니다! 🎉
