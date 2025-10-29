# 로컬 모드 사용 가이드

## 🎯 개요

PostgreSQL 없이 **로컬 JSON 파일**만으로 크롤링, 임베딩, 검색을 모두 수행할 수 있습니다.

---

## ✅ 설정 완료 사항

### 1. **모드 전환 시스템**
`main_pipeline.py` 파일의 **18번째 줄**에서 모드 전환 가능:

```python
USE_LOCAL = True   # ← True: 로컬 모드, False: PostgreSQL 모드
```

### 2. **주요 파일**
- `local_storage.py` - 로컬 JSON 기반 벡터 저장소
- `main_pipeline.py` - 크롤링 파이프라인 (모드 전환 지원)
- `search_local.py` - 로컬 검색 스크립트

---

## 🚀 사용 방법

### 1️⃣ **크롤링 실행** (데이터 수집)

```powershell
.\venv\Scripts\python.exe main_pipeline.py
```

**결과:**
- `./crawl_data/` 폴더에 JSON 파일로 저장
  - `labs.json` - 연구실 정보
  - `documents.json` - 문서 + 임베딩 벡터
  - `stats.json` - 통계 정보
- `crawl_results.csv` - 크롤링 결과 요약

---

### 2️⃣ **검색 실행**

#### **대화형 검색** (추천)
```powershell
.\venv\Scripts\python.exe search_local.py
```

그러면 프롬프트가 나타나고 검색어를 입력할 수 있습니다:
```
🔍 검색어를 입력하세요: 컴퓨터 비전
```

#### **단일 검색**
```powershell
.\venv\Scripts\python.exe search_local.py --mode search --query "딥러닝" --limit 5
```

#### **통계 보기**
```powershell
.\venv\Scripts\python.exe search_local.py --mode stats
```

---

### 3️⃣ **Python 코드로 검색**

```python
from local_storage import LocalVectorStore
from embedding import EmbeddingPipeline

# 저장소 & 파이프라인 초기화
store = LocalVectorStore('./crawl_data')
pipeline = EmbeddingPipeline()

# 검색
query_emb = pipeline.embed("컴퓨터 비전과 딥러닝")
results = store.search_vector(query_emb.embedding, limit=5)

# 결과 출력
for i, result in enumerate(results):
    print(f"{i+1}. [{result.lab_name}] 점수: {result.score:.3f}")
    print(f"   {result.text[:100]}...")
```

---

## 🔄 PostgreSQL 모드로 전환하기

나중에 PostgreSQL을 사용하고 싶다면:

1. **`main_pipeline.py` 18번째 줄 수정:**
   ```python
   USE_LOCAL = False  # ← False로 변경
   ```

2. **주석 해제:**
   - `main_pipeline.py`의 주석처리된 PostgreSQL 코드 복원
   - 약 350-400줄 근처의 `db_config` 설정 주석 해제

3. **PostgreSQL 설치 및 설정:**
   ```bash
   # PostgreSQL 설치
   # pgvector 확장 설치
   # schema.sql 실행
   ```

---

## 📊 데이터 구조

### `crawl_data/labs.json`
```json
{
  "1": {
    "lab_id": 1,
    "kor_name": "AI 연구실",
    "eng_name": "AI Lab",
    "professor": "홍길동",
    ...
  }
}
```

### `crawl_data/documents.json`
```json
{
  "1": {
    "doc_id": 1,
    "lab_id": 1,
    "text": "우리 연구실은...",
    "embedding": [0.123, -0.456, ...],  // 768차원 벡터
    "quality_score": 85,
    ...
  }
}
```

---

## 💡 팁

1. **첫 실행 시**: 임베딩 모델(1.1GB) 다운로드로 시간이 걸릴 수 있습니다
2. **검색 속도**: 문서가 많아지면 느려질 수 있습니다 (수천 개까지는 괜찮음)
3. **백업**: `crawl_data/` 폴더를 복사하면 백업 완료
4. **초기화**: `crawl_data/` 폴더 삭제 후 다시 크롤링

---

## 🆘 문제 해결

### 문제: "모듈을 찾을 수 없습니다"
```powershell
# 가상환경 활성화 확인
.\venv\Scripts\python.exe -c "import local_storage; print('OK')"
```

### 문제: "crawl_data 폴더가 없습니다"
→ 먼저 `main_pipeline.py`를 실행하여 데이터를 크롤링하세요

### 문제: "검색 결과가 없습니다"
→ `search_local.py --mode stats`로 데이터가 있는지 확인

---

## ✨ 완료!

이제 PostgreSQL 없이 완전히 로컬에서 작동합니다! 🎉
