# 연구실 검색 시스템 (Lab Search System)

인하대학교 전기컴퓨터공학과 연구실 정보를 크롤링하고, AI 기반 의미 검색을 지원하는 시스템입니다.

## 🚀 빠른 시작

### 1. 설치
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# ⭐ Playwright 브라우저 설치 (중요!)
python -m playwright install chromium
```

### 2. 크롤링
```bash
python scripts/run_crawl.py
```

### 3. 검색
```bash
python scripts/run_search.py
```

## 📚 상세 문서

전체 문서는 `docs/` 폴더를 참고하세요:

- **[docs/README.md](docs/README.md)** - 📖 프로젝트 전체 소개
- **[docs/installation.md](docs/installation.md)** - ⚙️ 설치 및 환경 설정
- **[docs/crawling.md](docs/crawling.md)** - 🕷️ 크롤링 사용법
- **[docs/search.md](docs/search.md)** - 🔍 검색 사용법
- **[docs/architecture.md](docs/architecture.md)** - 🏗️ 시스템 구조
- **[docs/similarity.md](docs/similarity.md)** - 🎯 추천 시스템 알고리즘
- **[docs/api.md](docs/api.md)** - 🌐 REST API 문서 (NEW!)

## 📁 프로젝트 구조

```
code/
├── api/                   # FastAPI 백엔드 (NEW!)
│   ├── main.py           # FastAPI 앱 메인
│   ├── database.py       # PostgreSQL 연결
│   ├── resume.py         # 이력서 관리 API
│   ├── diagnosis.py      # 진단 결과 API
│   └── test_db_connection.py  # DB 연결 테스트
│
├── src/                   # 소스 코드
│   ├── core/             # 핵심 크롤링 & 임베딩
│   ├── processing/       # 텍스트 처리
│   ├── storage/          # 데이터 저장
│   ├── search/           # 검색 관련
│   ├── similarity/       # 추천 시스템
│   │   ├── candidate_generator.py  # 1단계: 후보군 생성
│   │   ├── scorer.py               # 2단계: 재랭킹
│   │   ├── sentence_similarity.py  # 문장형 유사도
│   │   ├── keyword_similarity.py   # 키워드형 유사도
│   │   ├── numeric_similarity.py   # 정량형 유사도
│   │   ├── config.py               # 설정 (기본/연구/기술/학업 중심)
│   │   ├── test_full_pipeline.py   # 전체 파이프라인 테스트
│   │   └── README.md               # 상세 문서
│   └── utils/            # 공통 유틸
│
├── data/                 # 데이터 저장소
│   ├── crawl_data/      # 크롤링 결과 (프로덕션)
│   ├── crawl_cache/     # 크롤링 캐시
│   ├── temp/            # 임시 데이터
│   └── backups/         # 백업
│
├── scripts/              # 실행 스크립트
│   ├── run_crawl.py     # 크롤링 실행
│   ├── run_search.py    # 검색 실행
│   └── run_similarity.py # 유사도 계산 (향후)
│
├── config/               # 설정 파일
│   ├── crawl_config.yaml
│   ├── embedding_config.yaml
│   └── similarity_config.yaml
│
├── tests/                # 테스트
├── docs/                 # 문서
├── .env                  # 환경 변수 (DB 설정 등)
├── .env.example          # 환경 변수 예시
└── requirements.txt
```

## ✨ 주요 기능

- 🛡️ **품질 관리**: 자동 품질 점수 계산 및 PII 차단
- 🚀 **스마트 크롤링 (Playwright)**: JavaScript 완전 실행, Google Sites/Wix 지원
- 📄 **고급 추출**: PDF, 표 구조 보존
- 🔍 **의미 기반 검색**: intfloat/multilingual-e5-large (1024차원 벡터)
- 🎯 **2단계 추천 시스템**:
  - 1단계: BM25 + E5-small 하이브리드 후보군 생성 (10~20개)
  - 2단계: 문장형(60%) + 키워드형(30%) + 정량형(10%) 정밀 재랭킹
- 🌐 **REST API**:
  - 이력서 관리 API (학생 프로필 CRUD)
  - 진단 결과 API (맞춤형 연구실 추천)
  - PostgreSQL 연동
  - Swagger UI 자동 생성

## 🌐 API 서버 실행

### FastAPI 서버 시작
```bash
# 필수 패키지 설치
pip install fastapi uvicorn psycopg2-binary python-dotenv

# .env 파일 설정 (DB 연결 정보)
cp .env.example .env
# .env 파일 편집하여 DB 정보 입력

# 서버 실행
python api/main.py
# 또는
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### API 문서 확인
서버 실행 후:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 주요 API 엔드포인트

#### 이력서 관리 API
- `GET /api/resume?student_id={id}` - 전체 조회
- `PUT /api/resume/basic-info` - 기본 정보 수정
- `POST /api/resume/language` - 언어 능력 추가
- `DELETE /api/resume/language/{student_id}` - 언어 능력 삭제
- `POST /api/resume/certificate` - 자격증 추가
- `DELETE /api/resume/certificate/{student_id}` - 자격증 삭제
- `POST /api/resume/award` - 수상경력 추가
- `DELETE /api/resume/award/{student_id}` - 수상경력 삭제
- `POST /api/resume/portfolio` - 포트폴리오 추가
- `DELETE /api/resume/portfolio/{student_id}` - 포트폴리오 삭제
- `PUT /api/resume/cover-letter` - 자기소개서 저장

#### 진단 결과 API
- `GET /api/diagnosis/results?student_id={id}&config_type={type}&top_k={n}` - 연구실 추천
  - `config_type`: default, research, skill, academic
  - `top_k`: 추천 개수 (1~20)

## 🎯 사용 시나리오

- **학생**: 관심 분야 연구실 찾기 + 맞춤형 추천
- **관리자**: 연구실 정보 최신화
- **개발자**: 커스텀 검색/추천 로직 추가

## 📄 라이선스

MIT License
