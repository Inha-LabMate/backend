# 고급 기능 구현 가이드

## 📋 구현된 기능 목록

### ✅ 1. 품질/가드레일 시스템

**파일:** `quality_guard.py`

#### 1.1 품질 점수 (QualityScorer)
- **quality_score**: 0.0-1.0 점수 계산
  - 섹션 일치도 (30%)
  - 길이 적절성 (25%) 
  - 언어 일관성 (25%)
  - 중복 여부 (20%)
- **needs_review**: 0.5 미만이면 검수 대상으로 표시
- **review_reason**: 낮은 점수의 이유 자동 생성

#### 1.2 PII/비공개 차단 (GuardRail)
- 포털/로그인/개인정보 페이지 감지
- URL 패턴 매칭: `/login`, `/admin`, `/portal` 등
- 텍스트 키워드 감지: '비밀번호', 'password' 등
- HTML 폼 분석: password/email 입력 필드 감지

```python
from quality_guard import GuardRail, QualityScorer

# 가드레일 사용
guard = GuardRail()
should_exclude, reason = guard.should_exclude_url(url)
has_pii, keywords = guard.detect_pii_in_text(text)

# 품질 점수 계산
scorer = QualityScorer()
report = scorer.calculate_quality(chunk, all_chunks)
if report.needs_review:
    print(f"검수 필요: {report.reason}")
```

---

### ✅ 2. 크롤링 매니저 (CrawlManager)

**파일:** `crawl_manager.py`

#### 2.1 robots.txt 준수
- 도메인별 robots.txt 자동 로드
- User-Agent별 허용 여부 확인
- 캐싱으로 반복 요청 방지

#### 2.2 속도 제어
- `delay` 파라미터로 요청 간 대기 시간 설정
- 기본값: 1.0초 (권장: 0.5-1.0 req/sec)
- 마지막 요청 시간 추적

#### 2.3 실패 재시도 (지수 백오프)
- 최대 재시도 횟수: 3회 (설정 가능)
- 대기 시간: 1초 → 2초 → 4초 → 8초...
- 타임아웃, 연결 오류 자동 처리

#### 2.4 ETag/Last-Modified 캐싱
- HTTP 캐시 헤더 자동 저장
- 304 Not Modified 응답 처리
- 캐시 유효 기간: 7일
- 디스크 캐시 (`./crawl_cache/`)

#### 2.5 통계 및 로깅
- 총 요청 수, 성공/실패 수
- 캐시 사용 횟수
- 재시도 횟수
- 성공률 계산

```python
from crawl_manager import CrawlManager

# 기본 사용
manager = CrawlManager(
    delay=1.0,              # 1초 딜레이
    max_retries=3,          # 최대 3회 재시도
    user_agent="YourBot/1.0"
)

result = manager.fetch_url(url)
if result.success:
    html = result.html
    print(f"캐시 사용: {result.cached}")

# 통계 확인
manager.print_stats()
```

---

### ✅ 3. 업데이트 전략

**파일:** `schema_enhanced.sql`

#### 3.1 재크롤 주기 관리
- `last_crawled_at` 필드로 마지막 크롤링 시간 추적
- 2-4주 주기 권장
- ETag/Last-Modified로 변경 감지

#### 3.2 소프트 삭제
- `is_active` 필드 (기본값: TRUE)
- 원문에서 사라진 문서 → `is_active=false`
- 히스토리 보존 (완전 삭제 안 함)
- `soft_delete_document(doc_id)` 함수 제공

```sql
-- 문서 소프트 삭제
SELECT soft_delete_document(123);

-- 활성 문서만 조회
SELECT * FROM documents WHERE is_active = TRUE;

-- 삭제된 문서 복구
UPDATE documents SET is_active = TRUE WHERE id = 123;
```

#### 3.3 감사 가능성 (crawl_log 테이블)
- 모든 크롤링 요청 로그 저장
- 상태 코드, 응답 시간, 에러 사유
- 생성/제외된 청크 수
- 캐시 사용 여부

**crawl_log 테이블 컬럼:**
- `url`, `status_code`, `success`
- `response_time_ms`, `response_size`
- `error_message`, `error_type`
- `chunks_created`, `chunks_excluded`
- `used_cache`, `etag`, `last_modified`

#### 3.4 업데이트 이력 추적
- `update_history` 테이블
- 변경 타입: added, modified, deleted
- 이전 값 vs 새 값 저장
- 변경 감지 시간, 크롤 로그 연결

```sql
-- 최근 변경 이력 조회
SELECT * FROM update_history 
WHERE lab_id = 1 
ORDER BY detected_at DESC 
LIMIT 10;
```

---

### ✅ 4. PDF/표/이미지 대응

**파일:** `advanced_extractors.py`

#### 4.1 PDF 텍스트 추출 (PDFExtractor)
- PyPDF2 또는 pdfplumber 지원
- 페이지별 텍스트 추출
- 메타데이터 추출 (제목, 저자, 페이지 수)
- `source_type='pdf'`로 표기

```python
from advanced_extractors import PDFExtractor

extractor = PDFExtractor(backend='pypdf2')
text = extractor.extract_text("paper.pdf")
metadata = extractor.extract_metadata("paper.pdf")

print(f"제목: {metadata['title']}")
print(f"페이지: {metadata['pages']}")
```

#### 4.2 표 구조 보존 (TableExtractor)
- HTML 표 자동 추출
- 헤더 인식 (venue, year, title, author)
- 컬럼 매핑 자동 생성
- **lab_tag** 자동 생성 (venue + year)
- 텍스트/딕셔너리 변환 지원

```python
from advanced_extractors import TableExtractor

extractor = TableExtractor()
tables = extractor.extract_tables(html)

for table in tables:
    # 텍스트 형식
    print(table.to_text())
    
    # 딕셔너리 리스트 (JSON 친화적)
    for row_dict in table.to_dict_list():
        print(row_dict)
    
    # 메타데이터 확인
    if 'lab_tags' in table.metadata:
        print(f"논문 태그: {table.metadata['lab_tags']}")
```

#### 4.3 이미지 OCR (ImageOCR) - 선택적
- pytesseract + Pillow 사용
- 한글/영문 동시 인식
- **비권장·후순위** (정확도 낮음)

```python
from advanced_extractors import ImageOCR

ocr = ImageOCR()
text = ocr.extract_text("image.png", lang='kor+eng')
```

**의존성 설치:**
```bash
pip install PyPDF2 pdfplumber pytesseract pillow
```

---

### ✅ 5. 검색/추천 메타데이터

**파일:** `schema_enhanced.sql`

#### 5.1 Signals (재랭킹 가점)
- `recent_papers_count`: 최근 3년 논문 수
- `has_awards`: 수상 이력 여부
- `equipment_gpu`: GPU 장비 수
- `equipment_robot`: 로봇 장비 여부

```sql
-- GPU 많은 연구실 우선
SELECT * FROM labs 
WHERE is_active = TRUE 
ORDER BY equipment_gpu DESC, recent_papers_count DESC;
```

#### 5.2 Constraints (모집 조건)
- `min_hours`: 최소 참여 시간 (시간/주)
- `weekend_ok`: 주말 가능 여부
- `join_type`: 학부연구생/대학원/인턴

```sql
-- 주말 가능한 연구실 검색
SELECT * FROM labs 
WHERE weekend_ok = TRUE AND is_active = TRUE;
```

#### 5.3 Provenance (추천 이유)
- `matched_snippet`: 매칭된 문장 캐시
- 검색 결과에 "왜 이 연구실이 추천되었는지" 표시용

```sql
UPDATE documents 
SET matched_snippet = '우리 연구실은 컴퓨터 비전을 연구합니다.'
WHERE id = 123;
```

---

## 🔧 통합 사용 예시

### 전체 파이프라인에 통합

```python
# main_pipeline.py에 추가

from quality_guard import GuardRail, QualityScorer
from crawl_manager import CrawlManager
from advanced_extractors import PDFExtractor, TableExtractor

class EnhancedCrawlOrchestrator:
    def __init__(self):
        # 기존 컴포넌트
        self.extractor = ContentExtractor()
        self.chunker = TextChunker()
        self.normalizer = TextNormalizer()
        self.embedder = EmbeddingPipeline()
        
        # 새로운 컴포넌트
        self.guard = GuardRail()
        self.scorer = QualityScorer()
        self.crawl_manager = CrawlManager(delay=1.0, max_retries=3)
        self.pdf_extractor = PDFExtractor()
        self.table_extractor = TableExtractor()
    
    def crawl_with_quality_check(self, url: str):
        # 1. URL 차단 확인
        should_exclude, reason = self.guard.should_exclude_url(url)
        if should_exclude:
            print(f"차단: {reason}")
            return None
        
        # 2. 크롤링 (속도 제한, 재시도 포함)
        result = self.crawl_manager.fetch_url(url)
        if not result.success:
            print(f"실패: {result.error}")
            return None
        
        html = result.html
        
        # 3. PII 감지
        has_pii, keywords = self.guard.detect_pii_in_html(html)
        if has_pii:
            print(f"PII 발견: {keywords}")
            return None
        
        # 4. 표 추출 (있으면)
        tables = self.table_extractor.extract_tables(html)
        for table in tables:
            if 'lab_tags' in table.metadata:
                print(f"논문 태그: {table.metadata['lab_tags']}")
        
        # 5. 콘텐츠 추출 및 청킹
        text = self.extractor.clean_html(html, url)
        chunks = self.chunker.chunk_text(text, source_url=url)
        
        # 6. 품질 점수 계산
        quality_checked_chunks = []
        for chunk in chunks:
            report = self.scorer.calculate_quality(chunk, chunks)
            
            chunk.quality_score = report.overall_score
            chunk.needs_review = report.needs_review
            
            if report.needs_review:
                print(f"검수 필요: {report.reason}")
            
            quality_checked_chunks.append(chunk)
        
        # 7. 나머지 처리 (정규화, 임베딩, 저장)
        # ...
        
        return quality_checked_chunks
```

---

## 📊 데이터베이스 스키마 활용

### 품질 점수로 검수 대상 찾기

```sql
-- 검수가 필요한 문서
SELECT d.id, d.text, d.quality_score, d.review_reason
FROM documents d
WHERE d.needs_review = TRUE
ORDER BY d.quality_score ASC
LIMIT 20;
```

### 크롤링 통계 보기

```sql
-- 일별 크롤링 통계
SELECT * FROM crawl_statistics 
ORDER BY crawl_date DESC 
LIMIT 7;

-- 최근 에러 로그
SELECT url, error_message, error_type, request_time
FROM crawl_log
WHERE success = FALSE
ORDER BY request_time DESC
LIMIT 10;
```

### 활성 연구실 요약

```sql
-- 연구실별 문서 품질 요약
SELECT * FROM active_labs_summary
ORDER BY avg_quality DESC;
```

---

## 📦 의존성 설치

모든 고급 기능을 사용하려면:

```bash
# 기본 (필수)
pip install beautifulsoup4 requests

# PDF 지원
pip install PyPDF2
# 또는 (더 정확)
pip install pdfplumber

# OCR 지원 (선택)
pip install pytesseract pillow
# + Tesseract OCR 엔진 설치 (시스템 레벨)
```

---

## ⚙️ 설정 예시

### config.py (설정 파일)

```python
# 크롤링 설정
CRAWL_DELAY = 1.0  # 초
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# 품질 점수 임계값
QUALITY_THRESHOLD = 0.5  # 이하면 검수 필요

# 캐시 설정
CACHE_DIR = './crawl_cache'
CACHE_EXPIRY_DAYS = 7

# 재크롤 주기
RECRAWL_INTERVAL_DAYS = 21  # 3주

# User-Agent
USER_AGENT = "INHA-LabSearch-Bot/1.0 (Educational; Contact: your-email@inha.ac.kr)"
```

---

## 🎯 다음 단계

1. **품질 모니터링**: `quality_guard.py` 테스트
2. **크롤링 속도 조절**: `crawl_manager.py`로 예의바른 크롤링
3. **데이터베이스 마이그레이션**: `schema_enhanced.sql` 적용
4. **PDF 지원 추가**: 논문 페이지 크롤링 시 활용
5. **표 데이터 활용**: 논문 목록을 구조화된 형태로 저장

---

## 📚 참고 문서

- `quality_guard.py` - 품질 점수 및 PII 감지
- `crawl_manager.py` - 크롤링 매니저 (속도, 재시도, 캐싱)
- `advanced_extractors.py` - PDF, 표, OCR 처리
- `schema_enhanced.sql` - 향상된 데이터베이스 스키마

모든 파일에는 사용 예시가 포함되어 있습니다!
