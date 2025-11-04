# 시스템 구조 (Architecture)

## 🏗️ 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        사용자                                │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┴───────────
    ▼                         ▼
┌─────────┐            ┌──────────────┐
│크롤링    │            │검색           │
│ 실행     │            │(로컬/API)     │
└────┬────┘            └──────┬───────┘
     │                        │
     │  ┌─────────────────────┘
     │  │
     ▼  ▼
┌──────────────────────────────────────┐
│         핵심 파이프라인               │
│  ┌────────────────────────────────┐ │
│  │ 1. 크롤링 관리자 (Playwright)   │ │
│  │    - JavaScript 완전 실행       │ │
│  │    - 네트워크 완료 대기         │ │
│  │    - 속도 제어 & 재시도        │ │
│  │    - 캐싱                      │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 2. 콘텐츠 추출                  │ │
│  │    - HTML 파싱                 │ │
│  │    - 본문 추출 (네비/푸터 제거) │ │
│  │    - PDF/표 추출               │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 3. 텍스트 처리                  │ │
│  │    - 청킹 (200-400자)          │ │
│  │    - 정규화 (언어 감지, 정리)   │ │
│  │    - 품질 점수 계산            │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 4. 임베딩 생성                  │ │
│  │    - 텍스트 → 768차원 벡터      │ │
│  │    - 배치 처리 & 캐싱          │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 5. 저장                        │ │
│  │    - 로컬 JSON                 │ │
│  │    - PostgreSQL + pgvector     │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│         데이터 저장소                 │
│                                      │
│  ┌──────────────┐  ┌──────────────┐ │
│  │ 로컬 JSON    │  │ PostgreSQL   │ │
│  │              │  │ + pgvector   │ │
│  │ crawl_data/  │  │              │ │
│  │ ├─ labs.json │  │ ├─ lab       │ │
│  │ └─ docs.json │  │ ├─ lab_docs  │ │
│  │              │  │ ├─ lab_tag   │ │
│  │              │  │ └─ lab_link  │ │
│  └──────────────┘  └──────────────┘ │
└──────────────────────────────────────┘
```

## 📁 디렉토리 구조

```
code/
├── src/                      # 소스 코드
│   ├── main_pipeline.py      # 🎯 메인 파이프라인 (크롤링 실행)
│   ├── crawl_manager.py      # 🕷️ 크롤링 관리자
│   ├── quality_guard.py      # 🛡️ 품질 관리 & 가드레일
│   ├── advanced_extractors.py # 📄 PDF/표/OCR 추출
│   ├── chunking.py           # ✂️ 텍스트 청킹 & 본문 추출
│   ├── text_normalization.py # 🧹 텍스트 정규화
│   ├── embedding.py          # 🧠 임베딩 생성
│   ├── vector_db.py          # 🗄️ PostgreSQL 벡터 DB
│   ├── local_storage.py      # 💾 로컬 JSON 저장소
│   ├── search_api.py         # 🌐 REST API 서버
│   └── search_local.py       # 🔍 로컬 검색 스크립트
│
├── crawl_data/               # 최종 결과 (프로덕션)
│   ├── labs.json
│   ├── documents.json
│   └── stats.json
│
├── temp/                     # 임시/테스트 데이터
│   ├── test_embedding_data/
│   └── test_local_data/
│
├── data/                     # 버전 관리용 데이터
│   ├── v1.0/
│   └── latest/
│
├── docs/                     # 문서
│   ├── README.md
│   ├── installation.md
│   ├── crawling.md
│   ├── search.md
│   └── architecture.md (이 파일)
│
├── schema.sql                # PostgreSQL 기본 스키마
├── schema_enhanced.sql       # PostgreSQL 고급 스키마
├── requirements.txt          # Python 패키지
└── .gitignore               # Git 제외 설정
```

## 🔄 데이터 흐름

### 크롤링 → 저장

```
[웹페이지 HTML]
    ↓
[CrawlManager] robots.txt 확인, 속도 제어, 재시도
    ↓
[ContentExtractor] 본문 추출 (BeautifulSoup)
    ↓
[TextChunker] 200-400자로 분할
    ↓
[QualityScorer] 품질 점수 계산 (0-1)
    ↓
[GuardRail] PII/비공개 차단
    ↓
[TextNormalizer]
    ├─ 언어 감지 (ko/en/mixed)
    ├─ 연락처 추출
    └─ 텍스트 정리
    ↓
[EmbeddingPipeline] 텍스트 → 768차원 벡터
    ↓
[LocalVectorStore 또는 VectorDatabase]
    ├─ MD5 해시로 중복 체크
    └─ 저장
```

### 검색

```
[검색어 "컴퓨터 비전"]
    ↓
[EmbeddingPipeline] 검색어 → 768차원 벡터
    ↓
[LocalVectorStore 또는 VectorDatabase]
    ├─ 코사인 유사도 계산
    ├─ 유사도 순 정렬
    └─ 상위 N개 반환
    ↓
[검색 결과]
```

## 🧩 핵심 모듈 상세

### 1. main_pipeline.py

**역할:** 전체 크롤링 프로세스 총괄

**주요 클래스:**

#### `LabCrawler`
```python
class LabCrawler:
    """연구실 목록 크롤링"""
    
    def crawl_lab_list(url: str) -> List[Dict]:
        """연구실 목록 페이지 파싱"""
        # https://inhaece.co.kr/page/labs05
        # → 연구실 이름, 교수, 홈페이지, 위치, 연락처
```

#### `CrawlOrchestrator`
```python
class CrawlOrchestrator:
    """크롤링 총괄 관리자"""
    
    def __init__(
        self,
        db_config=None,
        embedding_model='multilingual-mpnet',
        device='cpu',
        local_data_dir='./crawl_data'
    )
    
    def crawl_from_url(url: str) -> DataFrame:
        """전체 크롤링 실행"""
        # 1. 연구실 목록 크롤링
        # 2. 각 연구실 홈페이지 크롤링
        # 3. 텍스트 처리 & 임베딩
        # 4. 저장
        # → DataFrame 반환
```

### 2. crawl_manager.py

**역할:** Playwright 기반 JavaScript 렌더링 크롤링

**주요 클래스:**

#### `CrawlManager`
```python
class CrawlManager:
    """Playwright 기반 크롤링 관리자"""
    
    def __init__(
        self,
        delay=1.0,                 # 요청 간 대기 시간 (초)
        max_retries=3,             # 최대 재시도 횟수
        timeout=30000,             # 페이지 로딩 타임아웃 (밀리초)
        headless=True,             # 브라우저 창 안 띄움
        wait_for_network_idle=True, # 네트워크 완료까지 대기
        cache_dir='./crawl_cache'
    )
    
    def fetch_url(url: str) -> CrawlResult:
        """URL 가져오기 (Playwright로 JavaScript 실행)"""
        # 1. 캐시 확인
        # 2. 속도 제어 (마지막 요청 후 delay 대기)
        # 3. Playwright로 브라우저 실행
        # 4. JavaScript 실행 완료까지 대기
        # 5. 최종 HTML 추출
        # 6. 실패 시 재시도 (지수 백오프)
        # 7. 캐싱
```

**Playwright 크롤링 과정:**
```python
with sync_playwright() as p:
    # 1. Chromium 브라우저 실행 (headless)
    browser = p.chromium.launch(headless=True)
    
    # 2. 새 페이지 열기
    context = browser.new_context(user_agent=...)
    page = context.new_page()
    
    # 3. URL 접속 + JavaScript 실행
    page.goto(url, wait_until='networkidle')  # 네트워크 완료까지 대기
    
    # 4. 추가 대기 (동적 콘텐츠)
    page.wait_for_timeout(1000)  # 1초
    
    # 5. 최종 HTML 추출
    html = page.content()
    
    # 6. 브라우저 종료
    browser.close()
```

**왜 Playwright?**
- ✅ Google Sites: JavaScript로 콘텐츠 생성 → Playwright 필수
- ✅ Wix: 동적 렌더링 → Playwright 필수
- ✅ React/Vue SPA: 초기 HTML 비어있음 → Playwright 필수
- ❌ requests: 정적 HTML만 가져옴 → 최신 사이트 대부분 실패

**재시도 전략 (지수 백오프):**
```python
def exponential_backoff(attempt: int) -> float:
    """재시도 대기 시간 계산"""
    return min(2 ** attempt, 60)  # 1초 → 2초 → 4초 → ... (최대 60초)
```

### 3. quality_guard.py

**역할:** 품질 관리 & 안전장치

**주요 클래스:**

#### `QualityScorer`
```python
class QualityScorer:
    """품질 점수 계산"""
    
    def calculate_quality(
        chunk: Chunk,
        all_chunks: List[Chunk]
    ) -> QualityReport:
        """품질 점수 계산 (0-1)"""
        # 1. 섹션 일치도 (30%)
        # 2. 길이 적절성 (25%)
        # 3. 언어 일관성 (25%)
        # 4. 중복 여부 (20%)
        # → overall_score, needs_review, reason
```

**점수 계산 로직:**
```python
# 섹션 일치도
section_keywords = {
    'about': ['소개', '연구실', 'about', 'introduction'],
    'research': ['연구', '분야', 'research', 'interests'],
    ...
}
section_score = count_keywords(chunk.text, section_keywords[chunk.section])

# 길이 적절성
optimal_length = 300  # 200-400자 최적
length_score = 1.0 - abs(chunk.char_count - optimal_length) / optimal_length

# 언어 일관성
if chunk.lang == 'mixed':
    lang_score = 0.5
else:
    lang_score = 1.0

# 중복 여부
if chunk.md5 in existing_hashes:
    duplicate_score = 0.0
else:
    duplicate_score = 1.0

# 최종 점수
overall_score = (
    section_score * 0.3 +
    length_score * 0.25 +
    lang_score * 0.25 +
    duplicate_score * 0.2
)
```

#### `GuardRail`
```python
class GuardRail:
    """PII/비공개 차단"""
    
    def should_exclude_url(url: str) -> Tuple[bool, str]:
        """URL 차단 여부 확인"""
        # /login, /admin, /portal 등
    
    def detect_pii_in_text(text: str) -> Tuple[bool, List[str]]:
        """개인정보 감지"""
        # '비밀번호', 'password', '개인정보' 등
    
    def detect_pii_in_html(html: str) -> Tuple[bool, List[str]]:
        """HTML 폼 필드 감지"""
        # <input type="password">, <input type="email">
```

### 4. chunking.py

**역할:** 텍스트 분할 & 본문 추출

**주요 클래스:**

#### `Chunk`
```python
@dataclass
class Chunk:
    text: str               # 본문
    section: str            # about, research, publication, ...
    char_count: int         # 글자 수
    token_count: int        # 토큰 수 (추정)
    md5: str                # 중복 감지용 해시
    source_url: str         # 출처 URL
    crawl_depth: int        # 크롤링 깊이
    quality_score: float    # 품질 점수 (0-1)
    needs_review: bool      # 검수 필요 여부
```

#### `ContentExtractor`
```python
class ContentExtractor:
    """본문 추출"""
    
    def clean_html(html: str, url: str) -> str:
        """HTML → 깨끗한 텍스트"""
        # 1. BeautifulSoup으로 파싱
        # 2. 불필요한 태그 제거 (nav, footer, script, style)
        # 3. 본문만 추출 (Readability 계열 알고리즘)
        # 4. 공백 정리
```

#### `TextChunker`
```python
class TextChunker:
    """텍스트 분할"""
    
    def chunk_text(
        text: str,
        min_chars=200,
        max_chars=400
    ) -> List[Chunk]:
        """문단 기준 청킹"""
        # 1. 문단 분리 (\n\n)
        # 2. 200-400자 범위 유지
        # 3. 너무 짧으면 병합
        # 4. 너무 길면 분할
```

### 5. text_normalization.py

**역할:** 텍스트 정규화

**주요 클래스:**

#### `LanguageDetector`
```python
class LanguageDetector:
    """언어 감지"""
    
    def detect_language(text: str) -> str:
        """ko, en, mixed"""
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if korean_chars > english_chars * 2:
            return 'ko'
        elif english_chars > korean_chars * 2:
            return 'en'
        else:
            return 'mixed'
```

#### `ContactExtractor`
```python
class ContactExtractor:
    """연락처 추출"""
    
    def extract_emails(text: str) -> List[str]:
        """이메일 정규식"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    def extract_phones(text: str) -> List[str]:
        """전화번호 정규식"""
        pattern = r'\d{2,3}-\d{3,4}-\d{4}'
    
    def extract_urls(text: str) -> List[str]:
        """URL 정규식"""
        pattern = r'https?://[^\s]+'
```

#### `TextCleaner`
```python
class TextCleaner:
    """텍스트 정리"""
    
    def clean_text(text: str) -> str:
        """정리"""
        # 1. 연속 공백 → 하나로
        # 2. 저작권 문구 제거 (© Copyright ...)
        # 3. 내비게이션 텍스트 제거 (Home > About > ...)
        # 4. 특수문자 정리
```

### 6. embedding.py

**역할:** 텍스트 → 벡터 변환

**주요 클래스:**

#### `EmbeddingPipeline`
```python
class EmbeddingPipeline:
    """임베딩 파이프라인"""
    
    def __init__(
        self,
        model_name='multilingual-mpnet',
        device='cpu',
        cache_enabled=True
    )
    
    def embed(
        texts: Union[str, List[str]],
        batch_size=32
    ) -> Union[EmbeddingResult, List[EmbeddingResult]]:
        """임베딩 생성"""
        # 1. 캐시 확인
        # 2. 모델 로드
        # 3. 배치 처리
        # 4. L2 정규화
        # 5. 캐시 저장
```

**지원 모델:**
```python
SUPPORTED_MODELS = {
    'multilingual-mpnet': {
        'name': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
        'dimension': 768,
        'description': '다국어 지원, 빠름'
    },
    'multilingual-e5-large': {
        'name': 'intfloat/multilingual-e5-large',
        'dimension': 1024,
        'description': '고품질, 느림'
    },
    'ko-sbert-multitask': {
        'name': 'jhgan/ko-sbert-multitask',
        'dimension': 768,
        'description': '한국어 특화'
    }
}
```

### 7. local_storage.py

**역할:** 로컬 JSON 저장소

**주요 클래스:**

#### `LocalVectorStore`
```python
class LocalVectorStore:
    """로컬 JSON 벡터 저장소"""
    
    def __init__(self, data_dir='./crawl_data')
    
    def insert_lab(lab_data: Dict) -> int:
        """연구실 추가"""
        # labs.json에 추가
    
    def insert_document(lab_id: int, doc_data: Dict) -> int:
        """문서 추가"""
        # documents.json에 추가
        # embedding은 리스트로 저장
    
    def search_vector(
        query_embedding: np.ndarray,
        limit=5,
        section_filter=None,
        min_quality=0.0
    ) -> List[SearchResult]:
        """벡터 검색"""
        # 1. 모든 문서와 코사인 유사도 계산
        # 2. 필터 적용
        # 3. 유사도 순 정렬
        # 4. 상위 N개 반환
```

**파일 구조:**

`crawl_data/labs.json`:
```json
{
  "1": {
    "lab_id": 1,
    "kor_name": "AI 연구실",
    "eng_name": "AI Lab",
    "professor": "홍길동",
    "homepage": "http://ailab.com",
    "location": "7호관 701호",
    "contact_email": "ai@lab.com"
  }
}
```

`crawl_data/documents.json`:
```json
{
  "1": {
    "doc_id": 1,
    "lab_id": 1,
    "section": "research",
    "text": "우리 연구실은 AI를 연구합니다...",
    "lang": "ko",
    "tokens": 150,
    "embedding": [0.123, -0.456, ..., 0.789],
    "quality_score": 0.85,
    "source_url": "http://ailab.com",
    "md5": "abc123..."
  }
}
```

### 8. vector_db.py

**역할:** PostgreSQL 벡터 DB

**주요 클래스:**

#### `VectorDatabase`
```python
class VectorDatabase:
    """PostgreSQL + pgvector"""
    
    def __init__(self, db_config: DatabaseConfig)
    
    def insert_document(
        lab_id: int,
        section: str,
        text: str,
        embedding: np.ndarray,
        **kwargs
    ) -> int:
        """문서 삽입"""
        # 1. MD5 중복 체크
        # 2. INSERT INTO lab_docs
    
    def search_vector(
        query_embedding: np.ndarray,
        limit=10,
        min_quality=0
    ) -> List[SearchResult]:
        """벡터 검색 (HNSW 인덱스)"""
        # SELECT ... ORDER BY embedding <=> %s LIMIT %s
    
    def search_hybrid(
        query_text: str,
        query_embedding: np.ndarray,
        vector_weight=0.7,
        keyword_weight=0.3
    ) -> List[SearchResult]:
        """하이브리드 검색 (벡터 + 키워드)"""
        # 벡터 점수 * 0.7 + 키워드 점수 * 0.3
```

## 🗄️ 데이터베이스 스키마

### 기본 스키마 (schema.sql)

#### `lab` - 연구실
```sql
CREATE TABLE lab (
    lab_id SERIAL PRIMARY KEY,
    kor_name TEXT,
    eng_name TEXT,
    professor TEXT,
    homepage TEXT,
    location TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `lab_docs` - 문서 (벡터)
```sql
CREATE TABLE lab_docs (
    doc_id SERIAL PRIMARY KEY,
    lab_id INTEGER REFERENCES lab(lab_id),
    section TEXT,  -- about, research, publication, ...
    title TEXT,
    text TEXT,
    lang TEXT,     -- ko, en, mixed
    tokens INTEGER,
    source_url TEXT,
    crawl_depth INTEGER,
    md5 TEXT UNIQUE,
    embedding vector(768),  -- pgvector
    emb_model TEXT,
    emb_ver INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW 인덱스
CREATE INDEX idx_docs_embedding ON lab_docs 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);
```

#### `lab_tag` - 태그
```sql
CREATE TABLE lab_tag (
    tag_id SERIAL PRIMARY KEY,
    lab_id INTEGER REFERENCES lab(lab_id),
    tag_type TEXT,  -- topic, method, equipment, venue, keyword
    value TEXT,
    confidence REAL,
    source TEXT     -- extraction, manual, llm
);
```

### 고급 스키마 (schema_enhanced.sql)

추가 테이블:

#### `crawl_log` - 크롤링 감사 로그
```sql
CREATE TABLE crawl_log (
    log_id SERIAL PRIMARY KEY,
    url TEXT,
    status_code INTEGER,
    success BOOLEAN,
    response_time_ms INTEGER,
    error_message TEXT,
    error_type TEXT,
    chunks_created INTEGER,
    chunks_excluded INTEGER,
    used_cache BOOLEAN,
    etag TEXT,
    last_modified TEXT,
    request_time TIMESTAMP DEFAULT NOW()
);
```

#### `update_history` - 변경 이력
```sql
CREATE TABLE update_history (
    history_id SERIAL PRIMARY KEY,
    lab_id INTEGER,
    change_type TEXT,  -- added, modified, deleted
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP DEFAULT NOW(),
    crawl_log_id INTEGER REFERENCES crawl_log(log_id)
);
```

#### `documents` (enhanced)
```sql
-- 추가 필드
quality_score REAL,         -- 품질 점수 (0-1)
needs_review BOOLEAN,       -- 검수 필요 여부
review_reason TEXT,         -- 검수 이유
is_active BOOLEAN,          -- 소프트 삭제
matched_snippet TEXT,       -- 추천 이유 (Provenance)
last_crawled_at TIMESTAMP   -- 마지막 크롤링 시간
```

#### `labs` (enhanced)
```sql
-- Signals (재랭킹)
recent_papers_count INTEGER,  -- 최근 3년 논문 수
has_awards BOOLEAN,           -- 수상 이력
equipment_gpu INTEGER,        -- GPU 수
equipment_robot BOOLEAN,      -- 로봇 장비

-- Constraints (모집 조건)
min_hours INTEGER,            -- 최소 시간/주
weekend_ok BOOLEAN,           -- 주말 가능
join_type TEXT                -- 학부/대학원/인턴
```

## 🔍 검색 알고리즘

### 벡터 검색 (Cosine Similarity)

```python
def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """코사인 유사도 계산"""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)

# 또는 pgvector에서
# SELECT 1 - (embedding <=> query_vector) as similarity
```

### HNSW 인덱스 (Hierarchical Navigable Small World)

```sql
-- 인덱스 생성
CREATE INDEX idx_docs_embedding ON lab_docs 
USING hnsw (embedding vector_cosine_ops)
WITH (
    m = 32,              -- 연결 수 (높을수록 정확, 느림)
    ef_construction = 128 -- 빌드 품질 (높을수록 정확, 느림)
);

-- 검색 시 정확도 조정
SET hnsw.ef_search = 64;  -- 검색 품질 (높을수록 정확, 느림)
```

**HNSW 파라미터 가이드:**

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| m | 16 | 빠름, 덜 정확 |
| m | 32 | 균형 (권장) |
| m | 64 | 느림, 매우 정확 |
| ef_construction | 64 | 빠른 빌드 |
| ef_construction | 128 | 균형 (권장) |
| ef_construction | 256 | 느린 빌드, 고품질 |
| ef_search | 32 | 빠른 검색 |
| ef_search | 64 | 균형 (권장) |
| ef_search | 128 | 느린 검색, 고정확도 |

### 하이브리드 검색

벡터 검색 + 키워드 검색:

```sql
-- PostgreSQL 함수
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(768),
    vec_weight REAL DEFAULT 0.7,
    kw_weight REAL DEFAULT 0.3,
    result_limit INTEGER DEFAULT 10
)
RETURNS TABLE(
    doc_id INTEGER,
    lab_name TEXT,
    text TEXT,
    vector_score REAL,
    keyword_score REAL,
    hybrid_score REAL
)
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.doc_id,
        l.name,
        d.text,
        (1 - (d.embedding <=> query_embedding)) as vector_score,
        ts_rank(d.text_tsv, plainto_tsquery('korean', query_text)) as keyword_score,
        (
            (1 - (d.embedding <=> query_embedding)) * vec_weight +
            ts_rank(d.text_tsv, plainto_tsquery('korean', query_text)) * kw_weight
        ) as hybrid_score
    FROM lab_docs d
    JOIN lab l ON d.lab_id = l.lab_id
    WHERE d.is_active = TRUE
    ORDER BY hybrid_score DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;
```

## 🚀 성능 최적화

### 1. 임베딩 캐싱

```python
class EmbeddingCache:
    """임베딩 캐시"""
    
    def __init__(self):
        self.cache = {}  # {text_hash: embedding}
    
    def get(self, text: str) -> Optional[np.ndarray]:
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.cache.get(text_hash)
    
    def set(self, text: str, embedding: np.ndarray):
        text_hash = hashlib.md5(text.encode()).hexdigest()
        self.cache[text_hash] = embedding
```

### 2. 배치 처리

```python
# 단일 처리 (느림)
for text in texts:
    embedding = model.encode(text)

# 배치 처리 (빠름)
embeddings = model.encode(texts, batch_size=32)
```

### 3. GPU 사용

```python
# CPU (느림)
pipeline = EmbeddingPipeline(device='cpu')

# GPU (10배 빠름)
pipeline = EmbeddingPipeline(device='cuda')
```

### 4. 인덱스 최적화

```sql
-- 벡터 인덱스 (필수)
CREATE INDEX idx_docs_embedding ON lab_docs 
USING hnsw (embedding vector_cosine_ops);

-- 필터링용 인덱스
CREATE INDEX idx_docs_lab_section ON lab_docs(lab_id, section);
CREATE INDEX idx_docs_quality ON lab_docs(quality_score);
CREATE INDEX idx_docs_lang ON lab_docs(lang);

-- 텍스트 검색 인덱스 (하이브리드 검색용)
CREATE INDEX idx_docs_text_tsv ON lab_docs USING gin(text_tsv);
```

## 🔒 보안 및 법적 준수

### 1. robots.txt 준수

```python
from urllib.robotparser import RobotFileParser

def check_robots_txt(url: str, user_agent: str) -> bool:
    """robots.txt 확인"""
    rp = RobotFileParser()
    rp.set_url(f"{url}/robots.txt")
    rp.read()
    return rp.can_fetch(user_agent, url)
```

### 2. User-Agent 명시

```python
USER_AGENT = "INHA-LabSearch-Bot/1.0 (Educational; Contact: your-email@inha.ac.kr)"

headers = {
    'User-Agent': USER_AGENT
}
```

### 3. 속도 제한

```python
import time

class RateLimiter:
    """요청 속도 제한"""
    
    def __init__(self, delay=1.0):
        self.delay = delay
        self.last_request = 0
    
    def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()
```

### 4. PII 보호

```python
# 개인정보 차단
PII_PATTERNS = [
    r'비밀번호',
    r'password',
    r'개인정보',
    r'주민등록번호',
    r'카드번호'
]

# 차단 URL 패턴
BLOCKED_URLS = [
    r'/login',
    r'/admin',
    r'/portal',
    r'/private'
]
```

## 📊 모니터링 & 로깅

### 크롤링 통계

```python
@dataclass
class CrawlStats:
    total_requests: int
    successful_requests: int
    failed_requests: int
    cache_hits: int
    retry_count: int
    
    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests
```

### 검색 로그

```sql
CREATE TABLE search_log (
    log_id SERIAL PRIMARY KEY,
    query TEXT,
    search_type TEXT,  -- vector, hybrid
    result_count INTEGER,
    avg_score REAL,
    searched_at TIMESTAMP DEFAULT NOW()
);
```

## 🎯 확장 포인트

### 1. 새로운 임베딩 모델 추가

```python
# embedding.py에 추가
SUPPORTED_MODELS['custom-model'] = {
    'name': 'your-org/your-model',
    'dimension': 512,
    'description': '커스텀 모델'
}
```

### 2. 새로운 섹션 추가

```python
# chunking.py에 추가
SECTION_KEYWORDS = {
    'custom_section': ['키워드1', '키워드2', ...]
}
```

### 3. 커스텀 검색 함수

```python
def custom_search(query: str, filters: Dict) -> List[SearchResult]:
    """커스텀 검색 로직"""
    # 1. 쿼리 전처리
    # 2. 임베딩
    # 3. 검색
    # 4. 후처리 (재랭킹, 필터링)
    # 5. 반환
```

### 4. REST API 엔드포인트 추가

```python
# search_api.py에 추가
@app.get("/custom-endpoint")
def custom_endpoint(param: str):
    # 커스텀 로직
    return {"result": ...}
```

## 🔄 시스템 업그레이드 경로

### 소규모 → 중규모

```
로컬 JSON → PostgreSQL
- VectorDatabase로 전환
- HNSW 인덱스 활용
- 더 빠른 검색
```

### 중규모 → 대규모

```
PostgreSQL → 분산 시스템
- Elasticsearch (키워드 검색)
- Milvus/Qdrant (벡터 검색)
- Redis (캐싱)
- 마이크로서비스 아키텍처
```

## ✅ 아키텍처 체크리스트

- [ ] 전체 데이터 흐름 이해
- [ ] 핵심 모듈 역할 파악
- [ ] 데이터베이스 스키마 이해
- [ ] 검색 알고리즘 이해
- [ ] 성능 최적화 방법 파악
- [ ] 확장 포인트 확인

시스템 구조를 이해하셨습니다! 🎉
