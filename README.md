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

## 📁 프로젝트 구조

```
code/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 크롤링 & 임베딩
│   ├── processing/        # 텍스트 처리
│   ├── storage/           # 데이터 저장
│   ├── search/            # 검색 관련
│   └── utils/             # 공통 유틸
│
├── data/                  # 데이터 저장소
│   ├── crawl_data/       # 크롤링 결과 (프로덕션)
│   ├── crawl_cache/      # 크롤링 캐시
│   ├── temp/             # 임시 데이터
│   └── backups/          # 백업
│
├── scripts/               # 실행 스크립트
│   ├── run_crawl.py      # 크롤링 실행
│   ├── run_search.py     # 검색 실행
│   └── run_similarity.py # 유사도 계산 (향후)
│
├── config/                # 설정 파일
│   ├── crawl_config.yaml
│   ├── embedding_config.yaml
│   └── similarity_config.yaml
│
├── tests/                 # 테스트
├── docs/                  # 문서
└── requirements.txt
```

## ✨ 주요 기능

- 🛡️ **품질 관리**: 자동 품질 점수 계산 및 PII 차단
- 🚀 **스마트 크롤링 (Playwright)**: JavaScript 완전 실행, Google Sites/Wix 지원
- 📄 **고급 추출**: PDF, 표 구조 보존
- 🔍 **의미 기반 검색**: intfloat/multilingual-e5-large (1024차원 벡터)

## 🎯 사용 시나리오

- **학생**: 관심 분야 연구실 찾기
- **관리자**: 연구실 정보 최신화
- **개발자**: 커스텀 검색 로직 추가

## 📄 라이선스

MIT License
