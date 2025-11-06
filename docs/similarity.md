# 연구실 추천 시스템 상세 문서

## 📌 개요

학생의 프로필을 기반으로 최적의 연구실을 추천하는 **2단계 하이브리드 추천 시스템**입니다.

## 🏗️ 시스템 구조

```
                     학생 프로필 입력
                          ↓
    ┌─────────────────────────────────────────┐
    │  1단계: 후보군 생성 (Candidate Gen)      │
    │  - BM25 키워드 검색                      │
    │  - E5-small 의미 검색                    │
    │  - 하이브리드 점수 계산                  │
    │  → 86개 → 10~20개 후보                  │
    └─────────────────┬───────────────────────┘
                      ↓
    ┌─────────────────────────────────────────┐
    │  2단계: 정밀 재랭킹 (Re-ranking)         │
    │  ┌───────────────────────────────────┐ │
    │  │ 문장형 (60%)                      │ │
    │  │ - E5-large 임베딩                 │ │
    │  │ - Cosine Similarity              │ │
    │  └───────────────────────────────────┘ │
    │  ┌───────────────────────────────────┐ │
    │  │ 키워드형 (30%)                    │ │
    │  │ - Jaccard, TF-IDF                │ │
    │  │ - Rule-based                     │ │
    │  └───────────────────────────────────┘ │
    │  ┌───────────────────────────────────┐ │
    │  │ 정량형 (10%)                      │ │
    │  │ - Min-Max 정규화                  │ │
    │  │ - Ordinal Similarity             │ │
    │  └───────────────────────────────────┘ │
    │  → 10~20개 → Top 5~10               │
    └─────────────────┬───────────────────────┘
                      ↓
                 최종 추천 결과
```

## 1️⃣ 1단계: 후보군 생성

### 목표
- **Precision (정확성)**: 키워드가 정확히 일치하는 연구실
- **Recall (재현율)**: 의미적으로 유사한 연구실도 탐지

### 알고리즘

#### BM25 키워드 검색
```python
from rank_bm25 import BM25Okapi

# 모든 연구실 텍스트 토큰화
tokenized_docs = [doc.split() for doc in lab_texts]

# BM25 인덱스 생성
bm25 = BM25Okapi(tokenized_docs)

# 검색어 점수 계산
query_tokens = "컴퓨터 비전 딥러닝".split()
scores = bm25.get_scores(query_tokens)
```

**특징:**
- TF (Term Frequency): 단어가 문서에 자주 등장할수록 높은 점수
- IDF (Inverse Document Frequency): 희귀한 단어일수록 높은 점수
- 문서 길이 정규화

#### E5-small 의미 검색
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('intfloat/e5-small-v2')

# 연구실 벡터 사전 계산
lab_embeddings = model.encode(lab_texts, normalize_embeddings=True)

# 검색어 벡터
query = "query: 컴퓨터 비전 딥러닝"  # E5는 prefix 필요
query_emb = model.encode(query, normalize_embeddings=True)

# 코사인 유사도
scores = np.dot(lab_embeddings, query_emb)
```

**특징:**
- 의미적 유사도: "AI"와 "인공지능" 동일하게 인식
- 384차원 벡터 (빠르고 효율적)
- 다국어 지원

#### 하이브리드 결합
```python
# 각 검색 결과 상위 10개
keyword_top10 = bm25_results[:10]
semantic_top10 = vector_results[:10]

# 합집합 (중복 제거)
candidates = set(keyword_top10) | set(semantic_top10)  # 10~15개
```

### 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `keyword_weight` | 0.5 | 키워드 검색 가중치 |
| `semantic_weight` | 0.5 | 의미 검색 가중치 |
| `final_top_k` | 15 | 최종 후보 수 |

## 2️⃣ 2단계: 정밀 재랭킹

### 점수 구성 (기본 설정)

```
최종 점수 = 문장형(60%) + 키워드형(30%) + 정량형(10%)
```

### 문장형 유사도 (60%)

**자유 서술형 텍스트의 의미적 유사도**

#### 세부 가중치
```python
문장형 = (
    자기소개1 * 0.30 +  # 관심 연구 분야
    자기소개2 * 0.25 +  # 기술 경험
    자기소개3 * 0.20 +  # 연구 목표
    포트폴리오 * 0.25    # 전체 경력
)
```

#### 알고리즘

**1. 기본 코사인 유사도 (자기소개1, 3)**
```python
# E5-large 임베딩 (1024차원)
model = SentenceTransformer('intfloat/multilingual-e5-large')

# 학생 텍스트
student_emb = model.encode("query: " + intro1, normalize_embeddings=True)

# 연구실 텍스트
lab_emb = model.encode("passage: " + lab_research, normalize_embeddings=True)

# 코사인 유사도
similarity = np.dot(student_emb, lab_emb)  # 0~1
```

**2. 키워드 오버랩 결합 (자기소개2)**
```python
# 문장 유사도
sentence_sim = cosine_similarity(intro2, lab_methods)

# 키워드 오버랩
keywords_student = set(intro2.lower().split())
keywords_lab = set(lab_methods.lower().split())
keyword_overlap = len(keywords_student & keywords_lab) / len(keywords_student | keywords_lab)

# 가중 평균
final = sentence_sim * 0.7 + keyword_overlap * 0.3
```

**3. Mean-pooling (포트폴리오)**
```python
# 긴 텍스트를 청크로 분할
chunks = split_text(portfolio, chunk_size=512)

# 각 청크 임베딩
chunk_embeddings = model.encode(chunks, normalize_embeddings=True)

# 평균 임베딩
mean_embedding = np.mean(chunk_embeddings, axis=0)
mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

# 유사도 계산
similarity = np.dot(mean_embedding, lab_emb)
```

### 키워드형 유사도 (30%)

**라벨/카테고리의 정확한 매칭**

#### 세부 가중치
```python
키워드형 = (
    전공 * 0.35 +
    자격증 * 0.25 +
    수상경력 * 0.20 +
    기술스택 * 0.20
)
```

#### 알고리즘

**1. 전공 Rule-based**
```python
def major_similarity(student_major, lab_department):
    # 완전 일치
    if student_major == lab_department:
        return 1.0
    
    # 같은 계열
    if same_group(student_major, lab_department):
        return 0.8
    
    # 부분 매칭
    if student_major in lab_department or lab_department in student_major:
        return 0.6
    
    # 관련 공학
    if both_engineering(student_major, lab_department):
        return 0.5
    
    return 0.0
```

**2. 자격증 Weighted Jaccard**
```python
# 자격증 가중치
weights = {"기사": 1.0, "산업기사": 0.7, "기능사": 0.5, "민간": 0.3}

# 가중 매칭 점수
for cert_student in student_certs:
    best_match = 0
    for cert_lab in lab_certs:
        # 문자열 유사도
        if cert_student == cert_lab:
            match = 1.0
        elif cert_student in cert_lab:
            match = 0.7
        else:
            match = jaccard(cert_student.split(), cert_lab.split())
        
        # 가중치 적용
        weight = get_weight(cert_student)
        best_match = max(best_match, match * weight)
    
    scores.append(best_match)

final = np.mean(scores)
```

**3. 수상경력 TF-IDF / Jaccard**
```python
# 긴 텍스트: TF-IDF
if len(text) > 20:
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([student_award, lab_award])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
# 짧은 텍스트: Jaccard
else:
    words1 = set(student_award.split())
    words2 = set(lab_award.split())
    similarity = len(words1 & words2) / len(words1 | words2)
```

**4. 기술 스택 Jaccard + E5**
```python
# Jaccard
techs_student = set(["python", "pytorch", "tensorflow"])
techs_lab = set(["python", "pytorch", "keras"])
jaccard = len(techs_student & techs_lab) / len(techs_student | techs_lab)

# E5-small 임베딩
student_emb = model.encode(list(techs_student), normalize_embeddings=True)
lab_emb = model.encode(list(techs_lab), normalize_embeddings=True)
embedding_sim = np.dot(np.mean(student_emb, axis=0), np.mean(lab_emb, axis=0))

# 하이브리드
final = jaccard * 0.6 + embedding_sim * 0.4
```

### 정량형 유사도 (10%)

**수치/범주 데이터의 거리 기반 유사도**

#### 세부 가중치
```python
정량형 = (
    어학점수 * 0.30 +
    구사능력 * 0.30 +
    학점 * 0.40
)
```

#### 알고리즘

**1. 어학 점수 (TOEIC) Min-Max + Threshold**
```python
def toeic_similarity(student_score, required_score):
    # 기준 이상: 만점
    if student_score >= required_score:
        return 1.0
    
    # 기준 미달: 선형 감소
    ratio = student_score / required_score
    
    # 70% 미만: 0점
    if ratio < 0.7:
        return 0.0
    
    # 70~100%: 선형 매핑
    return (ratio - 0.7) / 0.3  # 0.7→0, 1.0→1.0
```

**2. 구사능력 Ordinal Similarity**
```python
# 레벨 정의
levels = {"상": 1.0, "중상": 0.85, "중": 0.7, "중하": 0.55, "하": 0.4}

student_level = levels[student_proficiency]
required_level = levels[required_proficiency]

# 레벨 이상: 만점
if student_level >= required_level:
    return 1.0

# 레벨 차이에 따른 점수
gap = required_level - student_level
if gap <= 0.15:  # 거의 비슷
    return 0.9
elif gap <= 0.30:  # 1단계 차이
    return 0.7
elif gap <= 0.45:  # 2단계 차이
    return 0.4
else:  # 3단계 이상
    return 0.0
```

**3. 학점 Distance-based**
```python
def gpa_similarity(student_gpa, expected_gpa=3.5):
    # 기대 이상: 만점
    if student_gpa >= expected_gpa:
        return 1.0
    
    # 기대 미달: 거리 기반
    gap = expected_gpa - student_gpa
    max_gap = 0.5  # 최대 허용 격차
    
    if gap > max_gap:
        return 0.0
    
    # 선형 감소
    return 1.0 - (gap / max_gap)
```

## ⚙️ 설정 관리

### 기본 설정 (DEFAULT_CONFIG)
```python
@dataclass
class ScorerConfig:
    sentence_weight: float = 0.6   # 60%
    keyword_weight: float = 0.3    # 30%
    numeric_weight: float = 0.1    # 10%
    
    sentence: SentenceSimilarityConfig = ...
    keyword: KeywordSimilarityConfig = ...
    numeric: NumericSimilarityConfig = ...
```

### 프로파일별 가중치

#### 1. 기본 설정 (Default)
```
문장형: 60% (균형)
  ├─ intro1: 30%
  ├─ intro2: 25%
  ├─ intro3: 20%
  └─ portfolio: 25%
키워드형: 30%
  ├─ major: 35%
  ├─ certification: 25%
  ├─ award: 20%
  └─ tech_stack: 20%
정량형: 10%
  ├─ language: 30%
  ├─ proficiency: 30%
  └─ gpa: 40%
```

#### 2. 연구 중심 (Research-focused)
```
문장형: 50% (연구 관심 ↑)
  ├─ intro1: 40% ← 증가
  ├─ intro2: 20%
  ├─ intro3: 20%
  └─ portfolio: 20%
키워드형: 30%
정량형: 20% (학점 중시)
```

#### 3. 기술 중심 (Skill-focused)
```
문장형: 30%
키워드형: 45% (기술 스택 ↑)
  ├─ major: 25%
  ├─ certification: 25%
  ├─ award: 15%
  └─ tech_stack: 35% ← 증가
정량형: 25%
```

#### 4. 학업 중심 (Academic-focused)
```
문장형: 30%
키워드형: 30%
정량형: 40% (학점 ↑)
  ├─ language: 25%
  ├─ proficiency: 25%
  └─ gpa: 50% ← 증가
```

## 📊 성능 지표

### 정확도 측정

```python
# 학생 프로필
student = {...}

# 후보 생성 (1단계)
candidates = generator.get_candidates_with_scores(student)

# 재랭킹 (2단계)
results = scorer.rerank_candidates(student, candidates)

# 상위 5개 결과
for i, result in enumerate(results[:5], 1):
    print(f"{i}위. {result.lab_name} - {result.final_score:.4f}")
```

### 예상 점수 범위

| 점수 | 의미 | 설명 |
|-----|------|------|
| 0.9~1.0 | 매우 적합 | 거의 모든 항목 매칭 |
| 0.7~0.9 | 적합 | 대부분 항목 매칭 |
| 0.5~0.7 | 보통 | 일부 항목 매칭 |
| 0.3~0.5 | 부적합 | 최소 요건 미달 |
| 0.0~0.3 | 매우 부적합 | 거의 매칭 안 됨 (필터링) |

## 🔧 커스터마이징

### 가중치 조정
```python
from similarity.config import ScorerConfig

# 커스텀 설정
custom_config = ScorerConfig()
custom_config.sentence_weight = 0.7  # 문장형 강화
custom_config.keyword_weight = 0.2
custom_config.numeric_weight = 0.1

# 세부 가중치
custom_config.sentence.intro1_weight = 0.5  # 관심 연구 중시
custom_config.sentence.intro2_weight = 0.2
custom_config.sentence.intro3_weight = 0.15
custom_config.sentence.portfolio_weight = 0.15

# 검증 및 적용
custom_config.validate()
scorer = RerankingScorer(custom_config)
```

### 필터링 조건 추가
```python
# 최소 점수 임계값
config.min_score_threshold = 0.4  # 0.4 미만은 제외

# 섹션별 가중치
config.section_weights = {
    "research": 0.4,    # 연구 분야 중시
    "about": 0.2,
    "methods": 0.2,
    "projects": 0.15,
    "publications": 0.05
}
```

## 🚀 최적화 팁

### 1. 임베딩 캐싱
```python
# 연구실 임베딩은 한 번만 계산
lab_embeddings = model.encode(lab_texts)  # 사전 계산
# → 검색할 때마다 재사용
```

### 2. 배치 처리
```python
# 여러 학생 동시 처리
student_embeddings = model.encode(student_texts, batch_size=32)
```

### 3. GPU 활용
```python
model = SentenceTransformer('intfloat/multilingual-e5-large', device='cuda')
# CPU: ~2초/텍스트
# GPU: ~0.2초/텍스트 (10배 빠름)
```

## 📚 참고 자료

### 논문
- **BM25**: Robertson & Zaragoza (2009) - "The Probabilistic Relevance Framework: BM25 and Beyond"
- **E5**: Wang et al. (2022) - "Text Embeddings by Weakly-Supervised Contrastive Pre-training"
- **SBERT**: Reimers & Gurevych (2019) - "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"

### 모델
- **E5-large**: intfloat/multilingual-e5-large (1024차원)
- **E5-small**: intfloat/e5-small-v2 (384차원)
- **BM25**: rank-bm25 라이브러리

### 알고리즘
- **Cosine Similarity**: 벡터 간 각도 기반 유사도
- **Jaccard**: 집합 유사도 (교집합/합집합)
- **TF-IDF**: 단어 중요도 기반 문서 표현
- **Min-Max**: 선형 정규화
- **Ordinal**: 순서형 데이터 유사도

## ✅ 체크리스트

- [ ] 1단계 후보군 생성 이해
- [ ] 2단계 재랭킹 3가지 유사도 이해
- [ ] 설정 프로파일 4가지 파악
- [ ] 가중치 커스터마이징 방법 확인
- [ ] 실제 사용 예제 테스트
