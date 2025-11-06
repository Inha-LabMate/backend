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

## 🔜 다음 단계

이 후보군은 **2단계: 순위 재조정(Re-ranking)**으로 전달됩니다.

2단계에서는:
- 자기소개서 (3가지)
- 포트폴리오
- 전공/복수전공
- 자격증, 수상경력
- 기술 스택
- 어학 점수, 학점

등 **모든 항목을 동원**하여 정밀한 최종 점수를 계산합니다.

## 📝 참고사항

- E5 모델은 첫 실행 시 Hugging Face에서 다운로드됩니다 (~150MB)
- GPU가 있으면 자동으로 활용됩니다
- 임베딩 벡터는 메모리에 캐시되어 빠른 검색이 가능합니다