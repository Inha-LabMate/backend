# 연구실 검색 시스템 (Lab Search System)

인하대학교 전기컴퓨터공학과 연구실 정보를 크롤링하고, AI 기반 의미 검색을 지원하는 시스템입니다.

## 🎯 프로젝트 개요

**이 시스템이 하는 일:**
1. 연구실 웹사이트에서 텍스트 자동 수집 (크롤링)
2. 텍스트를 AI 벡터로 변환 (임베딩)
3. 의미 기반 검색 제공 (벡터 검색)

**간단히 말하면:**
- "컴퓨터 비전"으로 검색하면 "영상처리", "이미지 인식" 등 관련 연구실도 자동으로 찾아줍니다
- 단순 키워드 매칭이 아닌 의미를 이해하는 검색입니다

## ✨ 주요 기능

### 🛡️ 품질 관리 & 가드레일
- **품질 점수 자동 계산** (0.0-1.0): 섹션 일치도, 길이, 언어 일관성, 중복 여부
- **PII 감지**: 개인정보/로그인 페이지 자동 차단
- **검수 대상 자동 표시**: 품질 점수 0.5 미만 문서

### 🚀 스마트 크롤링
- **robots.txt 준수**: 법적 문제 예방
- **속도 제어**: 0.5-1.0 req/sec (서버 부담 최소화)
- **자동 재시도**: 일시적 오류 자동 복구 (지수 백오프)
- **HTTP 캐싱**: ETag/Last-Modified 지원

### 📊 업데이트 전략
- **재크롤 주기 관리**: 2-4주 자동 재크롤
- **소프트 삭제**: 히스토리 보존
- **감사 로그**: 모든 크롤링 요청 기록
- **변경 이력 추적**: 추가/수정/삭제 기록

### 📄 고급 추출
- **PDF 텍스트 추출**: PyPDF2/pdfplumber 지원
- **표 구조 보존**: venue/year 자동 매핑, lab_tag 생성
- **이미지 OCR** (선택): pytesseract 지원

### 🔍 검색 메타데이터
- **Signals**: 논문 수, 수상 이력, 장비 정보 (재랭킹용)
- **Constraints**: 최소 시간, 주말 가능, 모집 유형
- **Provenance**: 추천 이유 표시용 스니펫 캐시

## 📁 프로젝트 구조

```
code/
├── src/                    # 로직 코드
│   ├── main_pipeline.py    # 메인 파이프라인
│   ├── crawl_manager.py    # 크롤링 관리자
│   ├── quality_guard.py    # 품질 관리
│   ├── advanced_extractors.py  # PDF/표 추출
│   ├── embedding.py        # 임베딩 처리
│   ├── vector_db.py        # 벡터 DB
│   ├── local_storage.py    # 로컬 저장소
│   ├── chunking.py         # 텍스트 청킹
│   ├── text_normalization.py  # 텍스트 정규화
│   ├── search_api.py       # REST API
│   └── search_local.py     # 로컬 검색
│
├── crawl_data/             # 최종 결과 (프로덕션)
├── temp/                   # 임시/테스트 데이터
├── data/                   # 버전 관리용 데이터
│
├── docs/                   # 문서
│   ├── README.md           # 프로젝트 소개 (이 파일)
│   ├── installation.md     # 설치 가이드
│   ├── crawling.md         # 크롤링 사용법
│   ├── search.md           # 검색 사용법
│   └── architecture.md     # 시스템 구조
│
├── schema.sql              # PostgreSQL 스키마 (기본)
├── schema_enhanced.sql     # PostgreSQL 스키마 (고급)
├── requirements.txt        # Python 패키지
└── .gitignore             # Git 제외 설정
```

## 🚀 빠른 시작

### 1. 설치
```bash
# 가상환경 생성
python -m venv venv
.\venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

자세한 설치 방법은 [installation.md](installation.md)를 참고하세요.

### 2. 크롤링
```bash
cd src
python main_pipeline.py
```

자세한 크롤링 방법은 [crawling.md](crawling.md)를 참고하세요.

### 3. 검색
```bash
cd src
python search_local.py
```

자세한 검색 방법은 [search.md](search.md)를 참고하세요.

## 📚 문서 가이드

- **[installation.md](installation.md)** - 설치 및 환경 설정
- **[crawling.md](crawling.md)** - 크롤링 및 데이터 수집
- **[search.md](search.md)** - 검색 및 API 사용
- **[architecture.md](architecture.md)** - 시스템 구조 및 기술 세부사항

## 🎓 초보자를 위한 안내

### 임베딩(Embedding)이란?
텍스트를 AI가 이해할 수 있는 숫자 리스트로 변환하는 것입니다.

```
"인공지능 연구" → [0.123, -0.456, 0.789, ..., 0.234]
                   └──────── 768개의 숫자 ────────┘
```

### 벡터 검색이란?
키워드가 정확히 일치하지 않아도 의미가 비슷하면 찾아주는 검색입니다.

```
검색: "AI"
결과: "AI", "인공지능", "머신러닝", "딥러닝" 모두 찾음
```

## 💡 사용 시나리오

### 학부생/대학원생
- 관심 분야 연구실 찾기
- 교수님 연구 주제 파악
- 논문 실적 확인

### 연구실 관리자
- 연구실 정보 최신화
- 홈페이지 품질 점검

### 개발자
- 커스텀 검색 로직 추가
- 다른 학과/학교로 확장

## 🔧 기술 스택

- **언어**: Python 3.8+
- **임베딩**: sentence-transformers (multilingual-mpnet)
- **벡터 검색**: PostgreSQL + pgvector (선택) 또는 로컬 JSON
- **크롤링**: requests, BeautifulSoup4
- **API**: FastAPI (선택)

## 📊 데이터 저장 방식

### 로컬 모드 (기본)
- JSON 파일로 저장
- PostgreSQL 불필요
- 소규모 데이터에 적합

### PostgreSQL 모드 (선택)
- 벡터 데이터베이스 사용
- 대규모 데이터 처리
- 고급 검색 기능

## 🤝 기여

Issues와 Pull Requests를 환영합니다!

## 📞 문의

문제가 있거나 질문이 있으시면 Issue를 열어주세요.

## 📄 라이선스

MIT License
