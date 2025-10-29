# 프로젝트 구조

```
lab-search-system/
│
├── schema.sql                    # PostgreSQL + pgvector 스키마
│   ├── 테이블 정의 (lab, lab_docs, lab_tag, lab_link)
│   ├── HNSW 벡터 인덱스
│   ├── 검색 함수 (search_by_vector, hybrid_search)
│   └── 통계 뷰
│
├── chunking.py                   # 청킹 & 본문 추출
│   ├── ContentExtractor          # 본문 추출 (네비/푸터 제거)
│   ├── TextChunker              # 200-400자 청킹
│   └── DocumentProcessor        # 통합 처리
│
├── text_normalization.py        # 텍스트 정규화
│   ├── LanguageDetector         # 언어 감지 (ko/en/mixed)
│   ├── ContactExtractor         # URL/이메일/전화 추출
│   ├── TextCleaner              # 공백/저작권 제거
│   └── TextNormalizer           # 통합 정규화
│
├── embedding.py                 # 임베딩 생성
│   ├── EmbeddingModel           # 모델 래퍼
│   ├── EmbeddingCache           # 중복 계산 방지
│   └── EmbeddingPipeline        # 배치 처리
│
├── vector_db.py                 # 벡터 DB 관리
│   ├── VectorDatabase           # PostgreSQL 연동
│   ├── search_vector()          # 벡터 검색
│   ├── search_hybrid()          # 하이브리드 검색
│   └── 로그/통계 관리
│
├── main_pipeline.py             # 통합 파이프라인
│   ├── LabCrawler              # 연구실 크롤러
│   └── CrawlOrchestrator       # 전체 프로세스 관리
│
├── search_api.py                # REST API (FastAPI)
│   ├── GET /search             # 벡터 검색
│   ├── GET /search/hybrid      # 하이브리드 검색
│   └── GET /stats              # 통계
│
├── test_system.py               # 통합 테스트
├── install.sh                   # 설치 스크립트
├── requirements.txt             # Python 패키지
└── README.md                    # 문서
```

## 데이터 흐름

```
[웹페이지]
    ↓
[크롤링] main_pipeline.py
    ↓
[HTML 파싱] BeautifulSoup
    ↓
[본문 추출] ContentExtractor
    ↓
[청킹] TextChunker (200-400자)
    ↓
[정규화] TextNormalizer
    ├─ 언어 감지 (ko/en/mixed)
    ├─ 연락처 추출
    └─ 클린업
    ↓
[임베딩] EmbeddingPipeline
    ├─ 모델: multilingual-mpnet (768d)
    ├─ L2 정규화
    └─ 캐싱
    ↓
[저장] VectorDatabase
    ├─ MD5 중복 체크
    └─ PostgreSQL + pgvector
    ↓
[검색] search_api.py
    ├─ 벡터 검색 (HNSW)
    └─ 하이브리드 (벡터 + 키워드)
```

## 주요 기능별 파일

### 1. 크롤링 & 데이터 수집
- `main_pipeline.py`: 전체 크롤링 프로세스
- `chunking.py`: HTML → 청크 변환

### 2. 텍스트 처리
- `text_normalization.py`: 정규화, 언어 감지
- `chunking.py`: 청킹 규칙

### 3. 임베딩
- `embedding.py`: 모델 관리, 배치 처리

### 4. 데이터베이스
- `schema.sql`: 스키마 정의
- `vector_db.py`: CRUD 및 검색

### 5. API
- `search_api.py`: REST API 서버

### 6. 유틸리티
- `install.sh`: 자동 설치
- `test_system.py`: 통합 테스트

## 핵심 클래스

### DocumentProcessor (chunking.py)
```python
processor = DocumentProcessor()
chunks = processor.process_html(html, url)
# → List[Chunk]
```

### TextNormalizer (text_normalization.py)
```python
normalizer = TextNormalizer()
result = normalizer.normalize(text)
# → NormalizedText (언어, 토큰, 연락처)
```

### EmbeddingPipeline (embedding.py)
```python
pipeline = EmbeddingPipeline(model_name='multilingual-mpnet')
embedding = pipeline.embed(text)
# → EmbeddingResult (768d vector)
```

### VectorDatabase (vector_db.py)
```python
db = VectorDatabase(config)
results = db.search_vector(query_embedding, limit=10)
# → List[SearchResult]
```

### CrawlOrchestrator (main_pipeline.py)
```python
orchestrator = CrawlOrchestrator(db_config)
df = orchestrator.crawl_from_url(url)
# → pandas DataFrame
```

## 설정 파일

### .env (환경 변수)
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=labsearch
DB_USER=postgres
DB_PASSWORD=your_password

EMBEDDING_MODEL=multilingual-mpnet
DEVICE=cpu

MAX_PAGES=5
TIMEOUT=10
```

## 실행 순서

1. **설치**
   ```bash
   bash install.sh
   ```

2. **DB 초기화**
   ```bash
   psql -U postgres < schema.sql
   ```

3. **크롤링**
   ```bash
   python main_pipeline.py
   ```

4. **API 서버**
   ```bash
   uvicorn search_api:app --reload
   ```

5. **테스트**
   ```bash
   python test_system.py
   ```

## 확장 포인트

### 새로운 섹션 추가
`chunking.py`의 `identify_section()` 함수 수정

### 새로운 임베딩 모델
`embedding.py`의 `SUPPORTED_MODELS`에 추가

### 커스텀 검색 알고리즘
`vector_db.py`에 새로운 검색 함수 추가

### API 엔드포인트 추가
`search_api.py`에 새로운 경로 추가
