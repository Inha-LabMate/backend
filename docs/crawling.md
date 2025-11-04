# 크롤링 가이드 (Crawling Guide)

## 🎯 크롤링이란?

웹사이트를 자동으로 방문하여 데이터를 수집하는 과정입니다.

**이 시스템의 크롤링 과정:**
```
연구실 목록 페이지 방문
    ↓
각 연구실 홈페이지 방문
    ↓
텍스트 추출 및 정리
    ↓
200-400자로 분할 (청킹)
    ↓
AI 벡터로 변환 (임베딩)
    ↓
저장 (JSON 또는 PostgreSQL)
```

## 🚀 빠른 시작

### 기본 크롤링 실행

```bash
# src 폴더로 이동
cd src

# 크롤링 실행
python main_pipeline.py
```

**결과:**
- `crawl_data/labs.json` - 연구실 정보
- `crawl_data/documents.json` - 문서 + 임베딩 벡터
- `crawl_data/stats.json` - 통계 정보
- `crawl_results.csv` - 크롤링 요약

**예상 소요 시간:**
- 첫 실행: 10-15분 (모델 다운로드 포함)
- 이후 실행: 3-5분 (연구실 5개 기준)

## 📝 크롤링 설정

### 모드 선택 (로컬 vs PostgreSQL)

`src/main_pipeline.py` 파일의 18번째 줄:

```python
USE_LOCAL = True   # True: JSON 파일, False: PostgreSQL
```

### 크롤링 옵션 수정

`src/main_pipeline.py`의 `main()` 함수에서 설정:

```python
# 크롤링할 연구실 목록 URL
url = "https://inhaece.co.kr/page/labs05"

# 임베딩 모델 선택
embedding_model = 'multilingual-mpnet'  # 기본값 (768차원)
# 또는
# embedding_model = 'multilingual-e5-large'  # 고품질 (1024차원)
# embedding_model = 'ko-sbert-multitask'     # 한국어 특화

# CPU/GPU 선택
device = 'cpu'  # 또는 'cuda' (GPU)

# 데이터 저장 경로 (로컬 모드)
local_data_dir = './crawl_data'
```

## 🔧 고급 크롤링 기능

### 1. 품질 관리

시스템이 자동으로 다음을 수행합니다:

#### 품질 점수 계산 (0.0-1.0)
- **섹션 일치도** (30%): 텍스트와 분류된 섹션의 일치 여부
- **길이 적절성** (25%): 200-400자가 최적
- **언어 일관성** (25%): 한 언어로 통일되었는가
- **중복 여부** (20%): MD5 해시로 중복 감지

```python
# 품질 점수 0.5 미만이면 검수 필요로 표시됨
if chunk.quality_score < 0.5:
    chunk.needs_review = True
    chunk.review_reason = "길이 부적절, 섹션 불일치"
```

#### PII/개인정보 차단
- 로그인 페이지: `/login`, `/admin`, `/portal`
- 개인정보 키워드: "비밀번호", "password"
- HTML 폼 필드: password, email

### 2. 속도 제어 & robots.txt

#### 예의바른 크롤링
```python
from crawl_manager import CrawlManager

manager = CrawlManager(
    delay=1.0,           # 1초 딜레이 (서버 부담 최소화)
    max_retries=3,       # 최대 3회 재시도
    respect_robots=True  # robots.txt 준수
)
```

#### 재시도 전략 (지수 백오프)
```
1차 시도 → 실패
    ↓ 1초 대기
2차 시도 → 실패
    ↓ 2초 대기
3차 시도 → 실패
    ↓ 4초 대기
4차 시도 → 성공 또는 포기
```

### 3. HTTP 캐싱

시스템이 자동으로 캐시를 관리합니다:

```python
# 첫 방문: 전체 다운로드
result = manager.fetch_url(url)
# ETag: "abc123", Last-Modified: "2024-01-01" 저장

# 재방문: 변경 확인
result = manager.fetch_url(url)
if result.cached:
    print("변경 없음 (304 Not Modified)")
else:
    print("새 콘텐츠 다운로드")
```

**캐시 저장 위치:** `./crawl_cache/`
**캐시 유효 기간:** 7일

## 📊 크롤링 프로세스 상세

### 1. 연구실 목록 크롤링

```python
# LabCrawler가 연구실 목록 페이지 파싱
crawler = LabCrawler()
labs = crawler.crawl_lab_list(url)

# 결과 예시
[
    {
        'name': 'AI 연구실',
        'professor': '홍길동',
        'homepage': 'http://ailab.com',
        'location': '7호관 701호',
        'contact': 'ai@lab.com'
    },
    ...
]
```

### 2. 각 연구실 홈페이지 크롤링

```python
for lab in labs:
    # 홈페이지 방문
    result = manager.fetch_url(lab['homepage'])
    
    # HTML 파싱
    soup = BeautifulSoup(result.html)
    
    # 본문 추출 (네비/푸터 제거)
    text = extractor.clean_html(soup)
    
    # 200-400자로 분할
    chunks = chunker.chunk_text(text)
```

### 3. 텍스트 정규화

```python
for chunk in chunks:
    # 언어 감지
    chunk.lang = normalizer.detect_language(chunk.text)
    # → 'ko', 'en', 'mixed'
    
    # 연락처 추출
    chunk.emails = normalizer.extract_emails(chunk.text)
    chunk.phones = normalizer.extract_phones(chunk.text)
    
    # 텍스트 정리
    chunk.text = normalizer.clean_text(chunk.text)
```

### 4. 섹션 분류

시스템이 자동으로 텍스트를 섹션으로 분류합니다:

- **about**: 연구실 소개
- **research**: 연구 분야
- **publication**: 논문
- **project**: 프로젝트
- **join**: 모집 안내
- **people**: 구성원

```python
# 키워드 기반 분류
if "소개" in chunk.text or "about" in chunk.text:
    chunk.section = "about"
elif "논문" in chunk.text or "publication" in chunk.text:
    chunk.section = "publication"
```

### 5. 임베딩 생성

```python
# 텍스트를 768차원 벡터로 변환
embedding_result = pipeline.embed(chunk.text)

chunk.embedding = embedding_result.embedding  # numpy array (768,)
chunk.emb_model = "multilingual-mpnet"
chunk.emb_ver = 1
```

### 6. 저장

#### 로컬 모드 (JSON)
```python
# 연구실 정보 저장
lab_id = store.insert_lab(lab_data)

# 문서 저장 (임베딩 포함)
doc_id = store.insert_document(
    lab_id=lab_id,
    doc_data={
        'text': chunk.text,
        'embedding': chunk.embedding.tolist(),
        'section': chunk.section,
        'quality_score': chunk.quality_score
    }
)
```

#### PostgreSQL 모드
```python
# 벡터 DB에 저장
db.insert_document(
    lab_id=lab_id,
    section=chunk.section,
    text=chunk.text,
    embedding=chunk.embedding,
    quality_score=chunk.quality_score
)
```

## 🆕 고급 추출 기능

### 1. PDF 텍스트 추출

```python
from advanced_extractors import PDFExtractor

extractor = PDFExtractor(backend='pypdf2')

# PDF 파일에서 텍스트 추출
text = extractor.extract_text("research_paper.pdf")

# 메타데이터 추출
metadata = extractor.extract_metadata("research_paper.pdf")
print(f"제목: {metadata['title']}")
print(f"페이지: {metadata['pages']}")
```

### 2. 표 구조 보존

HTML 표를 자동으로 파싱하고 구조를 보존합니다:

```python
from advanced_extractors import TableExtractor

extractor = TableExtractor()
tables = extractor.extract_tables(html)

for table in tables:
    # 논문 테이블 예시
    # Year | Venue | Title | Author
    # 2024 | CVPR  | ...   | ...
    
    # lab_tag 자동 생성
    if 'lab_tags' in table.metadata:
        tags = table.metadata['lab_tags']
        # ['CVPR2024', 'ICCV2023', ...]
        
        # lab_tag 테이블에 저장
        for tag in tags:
            store.insert_tag(lab_id, 'venue', tag)
```

### 3. 이미지 OCR (선택적)

```python
from advanced_extractors import ImageOCR

ocr = ImageOCR()

# 이미지에서 텍스트 추출
text = ocr.extract_text("diagram.png", lang='kor+eng')
```

**주의:** OCR은 정확도가 낮아 권장하지 않습니다.

## 📈 진행 상황 모니터링

### 실시간 로그

크롤링 중 다음과 같은 로그가 출력됩니다:

```
[1/5] AI 연구실 크롤링 중...
  ✓ 홈페이지 접속 성공
  ✓ 본문 추출: 1,234자
  ✓ 청킹: 5개 청크 생성
  ✓ 임베딩: 5개 벡터 생성
  ✓ 저장 완료

[2/5] 비전 연구실 크롤링 중...
  ✗ 접속 실패 (404 Not Found)
  → 재시도 중... (1/3)
  ✓ 재시도 성공

...

크롤링 완료!
총 연구실: 5개
총 문서: 23개
평균 품질 점수: 0.78
```

### 통계 확인

크롤링 완료 후:

```bash
cd src
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

## 🔄 재크롤링 (업데이트)

### 언제 재크롤링이 필요한가?

- 연구실 정보가 업데이트됨
- 새 논문이 추가됨
- 2-4주가 지남 (권장 주기)

### 재크롤링 실행

```bash
# 전체 재크롤링
cd src
python main_pipeline.py
```

시스템이 자동으로:
1. ETag/Last-Modified로 변경 확인
2. 변경된 페이지만 다시 다운로드
3. 기존 문서와 비교하여 업데이트

### 변경 이력 추적 (PostgreSQL 모드)

```sql
-- 최근 변경 이력 조회
SELECT * FROM update_history 
WHERE lab_id = 1 
ORDER BY detected_at DESC 
LIMIT 10;

-- 결과
-- change_type | field_name | old_value | new_value | detected_at
-- modified    | text       | "..."     | "..."     | 2024-01-15
-- added       | document   | NULL      | "..."     | 2024-01-10
```

## 🛡️ 안전한 크롤링

### 법적 준수

시스템이 자동으로 다음을 준수합니다:

1. **robots.txt 확인**
   ```
   User-agent: *
   Disallow: /admin/
   Disallow: /private/
   ```

2. **User-Agent 명시**
   ```
   INHA-LabSearch-Bot/1.0 (Educational; Contact: your-email@inha.ac.kr)
   ```

3. **속도 제한**
   - 최소 1초 딜레이
   - 서버 부담 최소화

### 개인정보 보호

자동으로 다음을 차단합니다:

- 로그인 페이지
- 개인정보 입력 폼
- 관리자 페이지
- 포털 페이지

## 🐛 문제 해결

### 문제 1: "크롤링이 너무 느림"

**원인:** 
- 네트워크 속도
- 임베딩 계산 시간

**해결:**
```python
# GPU 사용 (10배 빠름)
device = 'cuda'

# 배치 크기 증가 (메모리 여유 시)
batch_size = 64
```

### 문제 2: "일부 연구실 크롤링 실패"

**원인:**
- 404 오류 (페이지 없음)
- 타임아웃
- robots.txt 차단

**해결:**
```python
# 타임아웃 증가
timeout = 30  # 기본값 10초

# 재시도 횟수 증가
max_retries = 5  # 기본값 3회
```

로그에서 실패 원인 확인:
```
✗ 접속 실패 (404 Not Found)
✗ 타임아웃 (10초 초과)
✗ robots.txt 차단
```

### 문제 3: "품질 점수가 너무 낮음"

**원인:**
- 텍스트가 너무 짧음
- 의미 없는 텍스트 (메뉴, 푸터 등)

**해결:**
1. `crawl_data/documents.json`에서 `needs_review=true`인 문서 확인
2. 수동으로 검수 및 수정
3. 또는 품질 점수 임계값 조정:
   ```python
   min_quality = 0.3  # 0.5에서 낮춤
   ```

### 문제 4: "중복 문서 발견"

**원인:**
- 여러 페이지에 같은 내용

**해결:**
시스템이 자동으로 MD5 해시로 중복 감지:
```python
if chunk.md5 in existing_hashes:
    print("중복 스킵")
    continue
```

### 문제 5: "캐시 문제"

**원인:**
- 오래된 캐시
- 캐시 손상

**해결:**
```bash
# 캐시 폴더 삭제
rm -rf crawl_cache/  # Linux/Mac
Remove-Item -Recurse -Force crawl_cache  # Windows
```

## 💡 최적화 팁

### 1. 임베딩 모델 선택

```python
# 빠른 처리 (768차원)
model = 'multilingual-mpnet'

# 고품질 (1024차원, 느림)
model = 'multilingual-e5-large'

# 한국어 특화 (768차원)
model = 'ko-sbert-multitask'
```

### 2. 배치 처리

```python
# 메모리가 충분하면 배치 크기 증가
batch_size = 64  # 기본값 32

# 메모리가 부족하면 감소
batch_size = 8
```

### 3. 병렬 처리 (고급)

여러 연구실을 동시에 크롤링:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    results = executor.map(crawl_lab, labs)
```

**주의:** 서버 부담을 고려하여 max_workers는 3 이하 권장

## 📊 크롤링 결과 분석

### CSV 파일 확인

`crawl_results.csv` 파일:

```csv
lab_name,professor,homepage,docs_count,avg_quality,sections
AI 연구실,홍길동,http://...,5,0.85,"about,research,publication"
비전 연구실,김철수,http://...,8,0.72,"about,research,project"
```

### Python으로 분석

```python
import pandas as pd

df = pd.read_csv('crawl_results.csv')

# 품질 점수 분포
print(df['avg_quality'].describe())

# 문서 수가 많은 연구실
print(df.nlargest(5, 'docs_count'))

# 품질 점수가 낮은 연구실
print(df[df['avg_quality'] < 0.5])
```

## 🎯 다음 단계

크롤링이 완료되었다면:

1. **[search.md](search.md)** - 검색 사용법
2. **데이터 검수** - `needs_review=true` 문서 확인
3. **정기 재크롤링** - 2-4주 주기

## ✅ 크롤링 체크리스트

- [ ] 설치 완료 (installation.md)
- [ ] 모드 선택 (로컬/PostgreSQL)
- [ ] 크롤링 실행
- [ ] 결과 파일 확인
- [ ] 통계 확인
- [ ] 품질 점수 검토
- [ ] (선택) 재크롤링 주기 설정

모든 항목을 완료했다면 [search.md](search.md)로 이동하세요! 🚀
