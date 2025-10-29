# 연구실 검색 시스템 v2.0 (고급 기능 포함)

인하대학교 전기컴퓨터공학과 연구실 정보를 크롤링하고, 임베딩하여 벡터 검색을 지원하는 시스템입니다.

## ✨ v2.0 주요 업데이트

### 🛡️ 품질 관리 & 가드레일
- **품질 점수 자동 계산** (0.0-1.0): 섹션 일치도, 길이, 언어 일관성, 중복 여부
- **PII 감지**: 개인정보/로그인 페이지 자동 차단
- **검수 대상 자동 표시**: 품질 점수 0.5 미만 문서

### 🚀 크롤링 매니저
- **robots.txt 준수**: 법적 문제 예방
- **속도 제어**: 0.5-1.0 req/sec (서버 부담 최소화)
- **지수 백오프 재시도**: 일시적 오류 자동 복구
- **HTTP 캐싱**: ETag/Last-Modified 지원

### 📊 업데이트 전략
- **재크롤 주기 관리**: 2-4주 자동 재크롤
- **소프트 삭제**: 히스토리 보존
- **감사 로그**: 모든 크롤링 요청 기록
- **변경 이력 추적**: 추가/수정/삭제 기록

### 📄 고급 추출기
- **PDF 텍스트 추출**: PyPDF2/pdfplumber 지원
- **표 구조 보존**: venue/year 자동 매핑, lab_tag 생성
- **이미지 OCR** (선택): pytesseract 지원

### 🔍 검색/추천 메타데이터
- **Signals**: 논문 수, 수상 이력, 장비 정보 (재랭킹용)
- **Constraints**: 최소 시간, 주말 가능, 모집 유형
- **Provenance**: 추천 이유 표시용 스니펫 캐시

## 🎯 이 시스템이 하는 일

**간단 요약:**
1. 연구실 웹사이트에서 텍스트 수집 (크롤링)
2. 텍스트를 숫자 벡터로 변환 (임베딩)
3. 검색어와 유사한 문서 찾기 (벡터 검색)

**자세한 설명:**
- 연구실 홈페이지를 자동으로 방문해서 내용을 수집합니다
- 수집한 텍스트를 AI 모델로 "의미"를 이해할 수 있는 숫자로 변환합니다
- "컴퓨터 비전"으로 검색하면 관련 연구실을 자동으로 찾아줍니다
- 단순 키워드 매칭이 아니라 의미를 이해하는 검색입니다

## 📁 파일 구조 설명

### 핵심 파이프라인
```
파일 이름              역할
─────────────────────────────────────────────────────────────
chunking.py          → 웹페이지에서 본문 추출, 적절한 크기로 분할
text_normalization.py → 텍스트 정리 (언어 감지, 연락처 추출)
embedding.py         → 텍스트를 숫자 벡터로 변환 (768개 숫자)
local_storage.py     → JSON 파일로 저장/검색 (DB 불필요)
vector_db.py         → PostgreSQL로 저장/검색 (대용량용)
main_pipeline.py     → 위 모듈들을 통합하여 실행
search_local.py      → 로컬 검색 테스트 도구
```

### 🆕 고급 기능 (v2.0)
```
파일 이름              역할
─────────────────────────────────────────────────────────────
quality_guard.py     → 품질 점수 계산, PII 감지, URL 차단
crawl_manager.py     → 속도 제어, 재시도, robots.txt, 캐싱
advanced_extractors.py → PDF, 표, 이미지 OCR 처리
schema_enhanced.sql  → 향상된 DB 스키마 (품질, 감사, 메타데이터)
test_advanced_features.py → 고급 기능 종합 테스트
ADVANCED_FEATURES.md → 고급 기능 상세 문서
```

## 🚀 빠른 시작

### 기본 설치
```bash
# 가상환경 생성
python -m venv venv
.\venv\Scripts\activate  # Windows

# 기본 패키지 설치
pip install -r requirements.txt
```

### 고급 기능 테스트
```bash
# 품질 점수, PII 감지, 크롤링 매니저, 표 추출 테스트
python test_advanced_features.py
```

## 📚 상세 문서

- **[ADVANCED_FEATURES.md](ADVANCED_FEATURES.md)** - 고급 기능 상세 가이드
  - 품질 점수 계산 방법
  - 가드레일 설정
  - 크롤링 매니저 사용법
  - PDF/표 추출
  - 검색 메타데이터 활용

- **[코드설명.md](코드설명.md)** - 초보자용 코드 설명 (한글)

## 🔧 시스템 구성

### 1. 청킹 & 본문 추출 (`chunking.py`)
- **청킹 규칙**: 문단 기준 200-400자 (150-300토큰)
- **본문 추출**: Readability 계열 방식으로 네비/푸터/사이드바 제거
- **섹션 분류**: about, research, publication, project, join, people
- **중복 감지**: MD5 해시로 동일 청크 재처리 방지

### 2. 텍스트 정규화 (`text_normalization.py`)
- **언어 감지**: ko (한글), en (영문), mixed (혼합)
- **클린업**: 공백, 저작권 블록, 내비게이션 텍스트 제거
- **연락처 추출**: URL, 이메일, 전화번호 별도 메타데이터로 분리
- **토큰 계산**: 한글/영문 혼합 텍스트 토큰 수 추정

### 3. 임베딩 생성 (`embedding.py`)
- **모델**: 멀티링궐 지원
  - `multilingual-mpnet` (기본, 768차원)
  - `multilingual-e5-large` (1024차원)
  - `ko-sbert-multitask` (한국어 특화)
- **정규화**: L2 정규화로 코사인 유사도 최적화
- **캐싱**: 중복 임베딩 계산 방지
- **배치 처리**: 효율적인 대량 처리

### 4. 벡터 DB (`vector_db.py`)
- **PostgreSQL + pgvector**: 벡터 검색 지원
- **HNSW 인덱스**: 
  - M=32 (연결 수)
  - ef_construction=128 (인덱스 빌드 품질)
  - ef_search=64 (검색 품질)
- **하이브리드 검색**: 벡터(70%) + 키워드(30%) 가중합
- **중복 방지**: MD5 해시로 동일 문서 스킵

### 5. 통합 파이프라인 (`main_pipeline.py`)
- 전체 프로세스 자동화
- 크롤링 → 청킹 → 정규화 → 임베딩 → DB 저장
- 진행 상황 실시간 출력
- 오류 처리 및 재시도

## 데이터베이스 스키마

### 핵심 테이블

#### `lab` - 연구실 기본 정보
```sql
- lab_id (PK)
- kor_name, eng_name
- professor
- homepage, location
- contact_email, contact_phone
- quality_score
- last_crawled
```

#### `lab_docs` - 문서 청크 (벡터 검색)
```sql
- doc_id (PK)
- lab_id (FK)
- section (about|research|publication|project|join|people)
- title, text
- lang (ko|en|mixed)
- tokens
- source_url, crawl_depth
- md5 (중복 감지)
- embedding (vector(768)) ← pgvector
- emb_model, emb_ver
- quality_score
- text_tsv (하이브리드 검색용 tsvector)
```

#### `lab_tag` - 연구실 태그
```sql
- lab_id (FK)
- tag_type (topic|method|equipment|venue|keyword)
- value
- confidence
- source (extraction|manual|llm)
```

#### `lab_link` - 연구실 링크
```sql
- lab_id (FK)
- kind (research|publication|people|join)
- url, title
```

## 설치 방법

### 1. Python 환경
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. PostgreSQL + pgvector 설치

#### Ubuntu/Debian
```bash
# PostgreSQL 14+ 설치
sudo apt install postgresql postgresql-contrib

# pgvector 설치
sudo apt install postgresql-14-pgvector
```

#### macOS
```bash
brew install postgresql@14
brew install pgvector
```

#### Docker
```bash
docker run -d \
  --name labsearch-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=labsearch \
  -p 5432:5432 \
  ankane/pgvector
```

### 3. 데이터베이스 초기화
```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE labsearch;
\c labsearch

# 스키마 생성
\i schema.sql
```

## 사용 방법

### 1. 기본 크롤링
```python
from main_pipeline import CrawlOrchestrator, DatabaseConfig

# DB 설정
db_config = DatabaseConfig(
    host='localhost',
    port=5432,
    database='labsearch',
    user='postgres',
    password='your_password'
)

# 오케스트레이터 초기화
orchestrator = CrawlOrchestrator(
    db_config=db_config,
    embedding_model='multilingual-mpnet',
    device='cpu'  # 또는 'cuda'
)

# 크롤링 실행
url = "https://inhaece.co.kr/page/labs05"
df_result = orchestrator.crawl_from_url(url)

# 결과 저장
df_result.to_csv('results.csv', index=False, encoding='utf-8-sig')
```

### 2. 벡터 검색
```python
from vector_db import VectorDatabase, DatabaseConfig
from embedding import EmbeddingPipeline

# DB 연결
db_config = DatabaseConfig(...)
db = VectorDatabase(db_config)

# 임베딩 파이프라인
pipeline = EmbeddingPipeline(model_name='multilingual-mpnet')

# 쿼리 임베딩
query = "딥러닝과 컴퓨터 비전 연구"
query_emb = pipeline.embed(query)

# 벡터 검색
results = db.search_vector(
    query_embedding=query_emb.embedding,
    limit=10,
    min_quality=50
)

for r in results:
    print(f"[{r.lab_name}] {r.title}")
    print(f"  점수: {r.score:.3f}")
    print(f"  텍스트: {r.text[:100]}...")
    print()
```

### 3. 하이브리드 검색
```python
# 벡터 + 키워드 검색
results = db.search_hybrid(
    query_text="컴퓨터 비전",
    query_embedding=query_emb.embedding,
    limit=10,
    vector_weight=0.7,
    keyword_weight=0.3
)

for r in results:
    print(f"{r.lab_name}: hybrid={r.score:.3f} (v={r.vector_score:.3f}, k={r.keyword_score:.3f})")
```

## 성능 최적화

### 1. 임베딩 모델 선택
```python
# 빠른 처리 (768차원)
model='multilingual-mpnet'

# 고품질 (1024차원, 느림)
model='multilingual-e5-large'

# 한국어 특화 (768차원)
model='ko-sbert-multitask'
```

### 2. HNSW 인덱스 튜닝
```sql
-- 더 정확한 검색 (느림)
CREATE INDEX idx_docs_embedding ON lab_docs 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 64, ef_construction = 256);

-- 더 빠른 검색 (정확도 낮음)
CREATE INDEX idx_docs_embedding ON lab_docs 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 검색 시 정확도 조정
SET hnsw.ef_search = 128;  -- 기본값 64
```

### 3. 배치 처리
```python
# 대량 임베딩
results = pipeline.embed(
    texts=text_list,
    batch_size=64,  # GPU 메모리에 따라 조정
    use_cache=True
)
```

## 품질 관리

### 청크 품질 점수 (0-100)
- **80+**: 우수 (긴 본문, 명확한 언어, 제목 포함)
- **60-79**: 양호
- **40-59**: 보통 (짧은 본문, 혼합 언어)
- **<40**: 불량 (매우 짧은 본문, 의미 없는 텍스트)

### 필터링
```python
# 고품질 문서만 검색
results = db.search_vector(
    query_embedding=emb,
    min_quality=70
)
```

## 모니터링

### 통계 확인
```python
stats = db.get_stats()
print(f"총 문서: {stats['total_docs']}")
print(f"평균 품질: {stats['avg_quality_score']}")
print(f"섹션 분포: {stats['section_distribution']}")
print(f"언어 분포: {stats['language_distribution']}")
```

### 검색 로그 분석
```sql
SELECT 
    query,
    search_type,
    AVG(avg_score) as avg_score,
    COUNT(*) as search_count
FROM search_log
GROUP BY query, search_type
ORDER BY search_count DESC
LIMIT 20;
```

## 버전 관리

### 임베딩 모델 업데이트
```sql
-- 새 버전 추가
INSERT INTO embedding_version (version_number, model_name, dimension, is_active)
VALUES (2, 'intfloat/multilingual-e5-large', 1024, FALSE);

-- 기존 버전 비활성화
UPDATE embedding_version SET is_active = FALSE WHERE version_number = 1;

-- 새 버전 활성화
UPDATE embedding_version SET is_active = TRUE WHERE version_number = 2;
```

### 재임베딩
```python
# 특정 버전의 문서만 재임베딩
old_docs = db.execute_raw(
    "SELECT * FROM lab_docs WHERE emb_ver = 1"
)

for doc in old_docs:
    new_emb = pipeline.embed(doc['text'])
    db.execute_raw(
        "UPDATE lab_docs SET embedding = %s, emb_ver = 2 WHERE doc_id = %s",
        (new_emb.embedding.tolist(), doc['doc_id'])
    )
```

## 트러블슈팅

### 1. pgvector 설치 오류
```bash
# Ubuntu
sudo apt install postgresql-server-dev-14
sudo apt install build-essential

# 소스 컴파일
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2. 임베딩 모델 다운로드 느림
```python
# 캐시 디렉토리 지정
import os
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/path/to/cache'
```

### 3. 메모리 부족
```python
# 배치 크기 줄이기
results = pipeline.embed(texts, batch_size=8)

# 또는 CPU 사용
orchestrator = CrawlOrchestrator(device='cpu')
```

## 라이선스

MIT License

## 기여

Issues와 Pull Requests를 환영합니다!

## 문의

문제가 있거나 질문이 있으시면 Issue를 열어주세요.
