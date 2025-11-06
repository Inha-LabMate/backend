# 후보군 생성 시스템 (Candidate Generation)

## 📌 개요
학생의 **희망 연구 분야**를 기반으로 수백 개의 연구실 중에서 관련성 있는 10~20개의 후보 연구실을 추출하는 1단계 시스템입니다.

## 🎯 목표
- **정확성(Precision)**: 키워드가 정확히 일치하는 연구실 찾기
- **발견(Recall)**: 의미적으로 유사한 연구실도 놓치지 않기

## 🔧 주요 기술

### 1. 키워드 매칭 (BM25)
- **역할**: 정확성 담당
- **방식**: 학생의 희망 연구 분야 키워드가 연구실 정보에 직접 포함되는지 확인
- **장점**: "AI", "머신러닝" 같은 명확한 키워드 매칭에 강함

### 2. 의미 검색 (E5-small Embedding)
- **역할**: 발견 담당  
- **방식**: E5-small 모델로 텍스트를 벡터로 변환 후 코사인 유사도 계산
- **장점**: "인공지능"과 "머신러닝"처럼 의미적으로 유사한 표현도 탐지

### 3. 하이브리드 접근
```
[키워드 검색] → Top 10개
[벡터 검색]   → Top 10개
[합집합]      → 10~15개 (중복 제거)
```

## 📦 설치

```bash
pip install -r requirements.txt
```

필수 패키지:
- `rank-bm25`: BM25 키워드 검색
- `sentence-transformers`: E5-small 임베딩
- `numpy`, `torch`: 벡터 연산

## 🚀 사용법

### 기본 사용
```python
from candidate_generator import CandidateGenerator, Lab, Student

# 1. 연구실 데이터 준비
labs = [
    Lab(
        id="lab_001",
        name="Computer Vision Lab",
        professor="김교수",
        about="컴퓨터 비전 연구",
        research="이미지 인식, 객체 검출"
    ),
    # ... 더 많은 연구실
]

# 2. 생성기 초기화 (임베딩 사전 계산)
generator = CandidateGenerator(labs)

# 3. 학생 정보
student = Student(
    research_interests="컴퓨터 비전과 딥러닝을 활용한 자율주행"
)

# 4. 후보군 생성
candidates = generator.generate_candidates(student)
print(f"후보 연구실: {candidates}")
```

### 점수와 함께 결과 받기
```python
results = generator.get_candidates_with_scores(student)

for lab_id, scores in results.items():
    print(f"{lab_id}:")
    print(f"  키워드 점수: {scores['keyword_score']}")
    print(f"  의미 점수: {scores['semantic_score']}")
    print(f"  출처: {scores['sources']}")  # ['keyword'], ['semantic'], 또는 ['keyword', 'semantic']
```

### 테스트 실행
```bash
cd src/similarity
python example_usage.py
```

## 📊 데이터 구조

### Lab (연구실)
```python
@dataclass
class Lab:
    id: str              # 고유 ID
    name: str            # 연구실 이름
    professor: str       # 교수명
    about: str          # 연구실 소개
    research: str       # 연구 분야
    methods: str        # 연구 방법론 (선택)
    projects: str       # 프로젝트 (선택)
    vision: str         # 비전/목표 (선택)
```

### Student (학생)
```python
@dataclass
class Student:
    research_interests: str  # 희망 연구 분야 (핵심!)
```

## 🔍 작동 원리

### 1. 초기화 단계
```python
generator = CandidateGenerator(labs)
```
- BM25 인덱스 생성: 모든 연구실 텍스트 토크나이징
- E5 임베딩 사전 계산: 모든 연구실을 벡터로 변환 (시간 절약)

### 2. 검색 단계
```python
candidates = generator.generate_candidates(student)
```

**키워드 검색 흐름:**
1. 학생의 희망 연구 분야를 토큰화
2. BM25 알고리즘으로 각 연구실과 점수 계산
3. 상위 10개 추출

**의미 검색 흐름:**
1. 학생의 희망 연구 분야를 "query: {텍스트}" 형태로 변환
2. E5-small 모델로 쿼리 벡터 생성
3. 사전 계산된 연구실 벡터들과 코사인 유사도 계산
4. 상위 10개 추출

**합치기:**
- 두 리스트를 합침 (set을 사용해 중복 제거)
- 최종 10~15개 후보 반환

## ⚙️ 설정 파라미터

### `generate_candidates()` 파라미터
- `keyword_top_k`: 키워드 검색 상위 k개 (기본값: 10)
- `semantic_top_k`: 의미 검색 상위 k개 (기본값: 10)

**조정 가이드:**
- 후보가 너무 적을 때: 각각 15~20으로 증가
- 후보가 너무 많을 때: 각각 5~8로 감소
- 키워드 정확도 중시: `keyword_top_k`를 크게
- 의미 유사도 중시: `semantic_top_k`를 크게

## 📈 성능 고려사항

### 임베딩 모델 선택
- **E5-small-v2** (기본): 빠르고 효율적 (33M 파라미터)
- **E5-base-v2**: 더 정확하지만 느림 (110M 파라미터)
- **E5-large-v2**: 최고 성능, 많은 리소스 필요 (335M 파라미터)

### 대용량 데이터 최적화
연구실이 1000개 이상일 경우:
```python
# FAISS 벡터 DB 사용 (옵션)
import faiss

# 인덱스 생성
dimension = 384  # E5-small의 차원
index = faiss.IndexFlatIP(dimension)  # 내적 (코사인 유사도)
index.add(lab_embeddings)

# 검색
distances, indices = index.search(query_embedding, k=10)
```

## 🎯 2단계: 정밀 재랭킹 (Re-ranking)

1단계에서 선정된 10~20개 후보 연구실에 대해 **모든 학생 프로필 항목**을 활용하여 정밀한 최종 점수를 계산합니다.

### 📊 재랭킹 점수 구성 (기본 설정)

```
최종 점수 = 문장형(60%) + 키워드형(30%) + 정량형(10%)
```

#### 1️⃣ 문장형 유사도 (60%)
**자유 서술형 텍스트의 의미적 유사도**

| 항목 | 가중치 | 모델 | 설명 |
|-----|--------|------|------|
| 자기소개1 (관심 연구) | 30% | E5-large + Cosine | 연구 관심사 vs 연구실 연구 분야 |
| 자기소개2 (기술 경험) | 25% | E5 + Keyword Overlap | 기술 경험 vs 연구실 방법론/프로젝트 |
| 자기소개3 (연구 목표) | 20% | E5-large + Cosine | 연구 목표 vs 연구실 비전 |
| 포트폴리오 | 25% | E5 Mean-pooling | 전체 경력 vs 연구실 전체 정보 |

**알고리즘:**
- **E5/SBERT**: 문장 임베딩 (1024차원 벡터)
- **Cosine Similarity**: 벡터 간 유사도 계산
- **Keyword Overlap**: 핵심 키워드 중복도 (자기소개2 전용)

**구현 파일:**
- `sentence_similarity.py`
  - `SentenceSimilarity`: 기본 E5 코사인 유사도
  - `SentenceSimilarityWithKeyword`: 키워드 오버랩 결합
  - `PortfolioSimilarity`: Mean-pooling 코사인

#### 2️⃣ 키워드형 유사도 (30%)
**라벨/카테고리 데이터의 정확한 매칭**

| 항목 | 가중치 | 알고리즘 | 설명 |
|-----|--------|---------|------|
| 전공 | 35% | Rule-based | 동일=1.0, 유사=0.8, 관련=0.5 |
| 자격증 | 25% | Weighted Jaccard | 기사>산업기사>민간자격 |
| 수상경력 | 20% | TF-IDF Cosine / Jaccard | 수상 내용 유사도 |
| 기술 스택 | 20% | Jaccard + E5-small | 기술 키워드 + 임베딩 하이브리드 |

**알고리즘:**
- **Rule-based**: 사전 정의된 규칙 (전공 계열 매칭)
- **Jaccard**: 집합 교집합/합집합 비율
- **TF-IDF**: 문서 중요도 기반 키워드 추출
- **Weighted Jaccard**: 항목별 가중치 부여

**구현 파일:**
- `keyword_similarity.py`
  - `MajorSimilarity`: 전공 Rule-based
  - `CertificationSimilarity`: 자격증 Weighted Jaccard
  - `AwardSimilarity`: 수상경력 TF-IDF/Jaccard
  - `TechStackSimilarity`: 기술 Jaccard + E5

#### 3️⃣ 정량형 유사도 (10%)
**수치/범주 데이터의 거리 기반 유사도**

| 항목 | 가중치 | 알고리즘 | 설명 |
|-----|--------|---------|------|
| 어학 점수 (TOEIC/OPIc) | 30% | Min-Max + Threshold | 기준 이상=1.0, 선형 감소 |
| 구사능력 (상/중/하) | 30% | Ordinal Similarity | 레벨 차이에 따른 점수 |
| 학점 (GPA) | 40% | Distance-based | 기대 학점 대비 거리 |

**알고리즘:**
- **Min-Max 정규화**: (값 - 최소) / (최대 - 최소)
- **Threshold Rule**: 기준 이상 만점, 이하 선형 감소
- **Ordinal Similarity**: 순서형 데이터 레벨 차이 계산
- **Distance-based**: 기대값 대비 거리 (학점 gap)

**구현 파일:**
- `numeric_similarity.py`
  - `LanguageScoreSimilarity`: TOEIC/OPIc Min-Max
  - `LanguageProficiencySimilarity`: 구사능력 Ordinal
  - `GPASimilarity`: 학점 거리 기반

### ⚙️ 설정 프로파일

**1. 기본 설정 (Default)**
```python
문장형: 60% (균형)
키워드형: 30%
정량형: 10%
```
- 가장 균형잡힌 설정
- 연구 적합도와 실무 능력 모두 고려

**2. 연구 중심 (Research-focused)**
```python
문장형: 50% (연구 관심 40% ↑)
키워드형: 30%
정량형: 20%
```
- 자기소개1 (관심 연구 분야) 가중치 증가
- 학업 성취도 중시

**3. 기술 중심 (Skill-focused)**
```python
문장형: 30%
키워드형: 45% (기술 스택 35% ↑)
정량형: 25%
```
- 기술 스택 매칭 강화
- 실무 프로젝트 경험 중시

**4. 학업 중심 (Academic-focused)**
```python
문장형: 30%
키워드형: 30%
정량형: 40% (학점 50% ↑)
```
- 학점, 어학 점수 중시
- 정량적 성취 강조

### 📦 파일 구조

```
src/similarity/
├── base.py                    # 추상 클래스 & 공통 인터페이스
├── config.py                  # 설정 및 가중치 관리 (4개 프로파일)
│
├── sentence_similarity.py     # 문장형 유사도 (E5, SBERT, Cosine)
├── keyword_similarity.py      # 키워드형 유사도 (Jaccard, TF-IDF, Rule)
├── numeric_similarity.py      # 정량형 유사도 (Min-Max, Ordinal)
│
├── candidate_generator.py     # 1단계: 후보군 생성 (BM25 + E5-small)
├── scorer.py                  # 2단계: 통합 재랭킹 스코어러
├── utils.py                   # 공통 유틸리티
│
├── __init__.py               # 모듈 패키지
├── README.md                  # 이 파일
└── test_full_pipeline.py     # 통합 테스트
```

### 🚀 사용법

#### 1단계: 후보군 생성
```python
from similarity import CandidateGenerator, Student

# 학생 정보 (간단)
student = Student(
    research_interests="컴퓨터 비전, 딥러닝, 객체 탐지"
)

# 후보군 생성기 초기화
generator = CandidateGenerator()

# 후보군 생성 (10~20개)
results = generator.get_candidates_with_scores(student, final_top_k=15)
candidates = [info['lab'] for info in results.values()]
```

#### 2단계: 정밀 재랭킹
```python
from similarity import RerankingScorer, StudentProfile, DEFAULT_CONFIG

# 학생 상세 프로필
student_profile = StudentProfile(
    # 문장형
    intro1="컴퓨터 비전과 딥러닝을 활용한 이미지 인식 연구에 관심이 있습니다",
    intro2="Python, PyTorch를 사용한 객체 탐지 프로젝트 경험이 있습니다",
    intro3="Vision Transformer 연구를 통해 실시간 영상 분석 기술을 개발하고 싶습니다",
    portfolio="YOLO v5 객체 탐지, GAN 이미지 생성, Transformer 연구 등 3년 경험",
    
    # 키워드형
    major="컴퓨터공학",
    certifications="정보처리기사, 빅데이터분석기사",
    awards="AI 해커톤 우수상",
    tech_stack="Python, PyTorch, TensorFlow, OpenCV",
    
    # 정량형
    toeic_score="850",
    english_proficiency="중상",
    gpa="4.0"
)

# 스코어러 초기화 (기본 설정)
scorer = RerankingScorer(DEFAULT_CONFIG)

# 재랭킹 수행
final_results = scorer.rerank_candidates(student_profile, candidates, top_k=5)

# 결과 확인
for i, result in enumerate(final_results, 1):
    print(f"{i}위. {result.lab_name}")
    print(f"   최종 점수: {result.final_score:.4f}")
    print(f"   - 문장형: {result.sentence_score:.4f}")
    print(f"   - 키워드형: {result.keyword_score:.4f}")
    print(f"   - 정량형: {result.numeric_score:.4f}")
```

#### 설정 변경
```python
from similarity import RESEARCH_CONFIG, SKILL_CONFIG

# 연구 중심 설정
scorer_research = RerankingScorer(RESEARCH_CONFIG)
results = scorer_research.rerank_candidates(student_profile, candidates)

# 기술 중심 설정
scorer_skill = RerankingScorer(SKILL_CONFIG)
results = scorer_skill.rerank_candidates(student_profile, candidates)
```

### 🧪 테스트

```bash
# 전체 파이프라인 테스트
cd code
python test_full_pipeline.py

# 개별 모듈 테스트
python test_scorer.py

# Scorer 모듈만 테스트
cd src/similarity
python -m pytest test_*.py  # pytest 사용시
```

### 📊 결과 예시

```json
{
  "lab_id": "73",
  "lab_name": "생성 컴퓨팅 연구실",
  "final_score": 0.8215,
  "sentence_score": 0.8318,
  "keyword_score": 0.6822,
  "numeric_score": 1.0000,
  "details": {
    "sentence": {
      "intro1": 0.8808,  // 관심 연구 매칭 우수
      "intro2": 0.6405,
      "intro3": 0.9159,  // 연구 목표 매칭 우수
      "portfolio": 0.8969
    },
    "keyword": {
      "major": 1.0000,   // 전공 정확히 일치
      "certification": 0.5000,
      "award": 0.5000,
      "tech_stack": 0.5358
    },
    "numeric": {
      "language": 1.0000,    // TOEIC 기준 이상
      "proficiency": 1.0000,  // 구사능력 충족
      "gpa": 1.0000          // 학점 우수
    }
  }
}
```

## 📝 참고사항

- E5 모델은 첫 실행 시 Hugging Face에서 다운로드됩니다 (~150MB)
- GPU가 있으면 자동으로 활용됩니다
- 임베딩 벡터는 메모리에 캐시되어 빠른 검색이 가능합니다