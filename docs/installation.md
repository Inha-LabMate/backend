# 설치 가이드 (Installation Guide)

## 📋 요구사항

### 필수 요구사항
- **Python**: 3.8 이상
- **운영체제**: Windows, macOS, Linux
- **메모리**: 최소 4GB RAM (임베딩 모델 로드용)
- **디스크**: 약 2GB (모델 캐시 포함)

### 선택 사항
- **PostgreSQL**: 14 이상 (대규모 데이터용)
- **pgvector**: PostgreSQL 벡터 확장 (PostgreSQL 모드 사용 시)
- **GPU**: CUDA 지원 GPU (빠른 임베딩용)

## 🚀 빠른 설치 (로컬 모드)

PostgreSQL 없이 JSON 파일만으로 사용하는 방법입니다.

### 1. Python 가상환경 생성

#### Windows (PowerShell)
```powershell
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.\.venv\Scripts\activate
```

#### macOS/Linux (Bash)
```bash
# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate
```

### 2. 패키지 설치

```bash
# 기본 패키지 설치
pip install -r requirements.txt

# ⭐ Playwright 브라우저 설치 (중요!)
python -m playwright install chromium
```

**Playwright 브라우저 설치:**
- 약 150MB 다운로드
- Chromium 브라우저 설치
- JavaScript 렌더링을 위해 필수!

### 3. 설치 확인

```bash
# src 폴더로 이동
cd src

# 임베딩 테스트
python -c "from embedding import EmbeddingPipeline; print('✅ 임베딩 설치 성공!')"

# Playwright 테스트
python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright 설치 성공!')"
```

첫 실행 시 임베딩 모델(약 1.1GB)이 자동으로 다운로드됩니다.

## 🗄️ PostgreSQL 설치 (선택 - 대규모 데이터용)

대용량 데이터 처리나 고급 검색 기능이 필요한 경우에만 설치하세요.

### Ubuntu/Debian

```bash
# PostgreSQL 14+ 설치
sudo apt update
sudo apt install postgresql postgresql-contrib

# pgvector 확장 설치
sudo apt install postgresql-14-pgvector

# PostgreSQL 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS (Homebrew)

```bash
# PostgreSQL 설치
brew install postgresql@14

# pgvector 설치
brew install pgvector

# PostgreSQL 시작
brew services start postgresql@14
```

### Windows

1. **PostgreSQL 다운로드**
   - https://www.postgresql.org/download/windows/
   - PostgreSQL 14 이상 설치

2. **pgvector 컴파일** (고급 사용자)
   - Visual Studio Build Tools 필요
   - 또는 Docker 사용 권장 (아래 참조)

### Docker (모든 OS)

가장 쉬운 방법입니다.

```bash
# pgvector 포함 PostgreSQL 컨테이너 실행
docker run -d \
  --name labsearch-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=labsearch \
  -p 5432:5432 \
  ankane/pgvector

# 컨테이너 시작/중지
docker start labsearch-db
docker stop labsearch-db
```

### 데이터베이스 초기화

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE labsearch;
\c labsearch

# 기본 스키마 적용
\i schema.sql

# 또는 고급 스키마 (품질 관리, 감사 로그 포함)
\i schema_enhanced.sql
```

## 📦 의존성 패키지 상세

### 필수 패키지

```txt
# 웹 크롤링 - Playwright (JavaScript 렌더링)
playwright>=1.40.0          # ⭐ 핵심: Google Sites, Wix 등 JavaScript 사이트 크롤링
beautifulsoup4>=4.12.0      # HTML 파싱
lxml>=4.9.0                 # XML/HTML 파서

# 임베딩
sentence-transformers>=2.2.0  # 텍스트 임베딩
torch>=2.0.0                  # PyTorch

# 데이터 처리
numpy>=1.24.0
pandas>=2.0.0

# 유틸리티
tqdm>=4.65.0
python-dotenv>=1.0.0
```

### Playwright 추가 설치

**중요:** pip install만으로는 부족합니다!

```bash
# 1단계: Python 패키지 설치
pip install playwright

# 2단계: 브라우저 설치 (필수!)
python -m playwright install chromium

# 또는 전체 브라우저 설치 (선택)
python -m playwright install  # chromium, firefox, webkit 모두
```

**왜 브라우저를 별도로 설치하나요?**
- Playwright는 실제 브라우저를 제어
- JavaScript를 실행하려면 브라우저 필요
- 약 150MB 크기
- 한 번만 설치하면 됨

### 선택 패키지

```bash
# PostgreSQL 지원
pip install psycopg2-binary

# PDF 지원
pip install PyPDF2 pdfplumber

# OCR 지원 (이미지에서 텍스트 추출)
pip install pytesseract Pillow

# API 서버
pip install fastapi uvicorn
```

### 전체 설치

```bash
# 모든 기능 포함
pip install -r requirements.txt

# 또는 개별 설치
pip install requests beautifulsoup4 lxml
pip install sentence-transformers torch
pip install numpy pandas tqdm python-dotenv

# 선택 사항
pip install psycopg2-binary PyPDF2 pdfplumber
pip install fastapi uvicorn
```

## 🔧 환경 설정

### 1. 로컬 모드 설정 (기본)

`src/main_pipeline.py` 파일 확인:

```python
# 18번째 줄
USE_LOCAL = True   # ← True로 설정 (기본값)
```

데이터는 `crawl_data/` 폴더에 JSON으로 저장됩니다.

### 2. PostgreSQL 모드 설정 (선택)

`.env` 파일 생성 (프로젝트 루트):

```bash
# PostgreSQL 연결 정보
DB_HOST=localhost
DB_PORT=5432
DB_NAME=labsearch
DB_USER=postgres
DB_PASSWORD=your_password

# 임베딩 설정
EMBEDDING_MODEL=multilingual-mpnet
DEVICE=cpu  # 또는 cuda (GPU 사용 시)

# 크롤링 설정
MAX_PAGES=5
TIMEOUT=10
DELAY=1.0
```

`src/main_pipeline.py` 파일 수정:

```python
# 18번째 줄
USE_LOCAL = False   # ← False로 변경
```

## 🧪 설치 확인

### 1. Python 환경 확인

```bash
# Python 버전
python --version  # 3.8 이상

# 가상환경 활성화 확인
which python  # Linux/Mac
where python  # Windows
# → venv 경로가 표시되어야 함
```

### 2. 패키지 확인

```bash
cd src
python -c "
import requests
import bs4
import sentence_transformers
import torch
import numpy as np
print('✅ 모든 패키지 정상')
"
```

### 3. 임베딩 모델 다운로드 확인

```bash
cd src
python -c "
from embedding import EmbeddingPipeline
pipeline = EmbeddingPipeline()
result = pipeline.embed('테스트')
print(f'✅ 임베딩 성공: {result.embedding.shape}')
"
```

첫 실행 시 모델 다운로드로 5-10분 소요될 수 있습니다.

### 4. PostgreSQL 연결 확인 (PostgreSQL 모드만)

```bash
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='labsearch',
    user='postgres',
    password='your_password'
)
print('✅ PostgreSQL 연결 성공')
conn.close()
"
```

## 🐛 문제 해결

### 문제 1: "ModuleNotFoundError: No module named 'playwright'"

**원인:** Playwright 미설치 또는 가상환경 미활성화

**해결:**
```bash
# 가상환경 활성화 확인
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Playwright 설치
pip install playwright
python -m playwright install chromium
```

### 문제 2: "Executable doesn't exist at ..." (Playwright)

**원인:** 브라우저 설치 누락

**해결:**
```bash
# 브라우저 재설치
python -m playwright install chromium

# 또는 전체 재설치
python -m playwright install --force
```

### 문제 3: "playwright install 명령어가 안됨"

**원인:** Python 모듈로 실행해야 함

**잘못된 방법:**
```bash
playwright install chromium  # ❌ 작동 안함
```

**올바른 방법:**
```bash
python -m playwright install chromium  # ✅ 이렇게!
```

### 문제 4: "torch가 설치되지 않음"

**원인:** PyTorch 설치 실패

**해결:**
```bash
# CPU 버전 (가볍고 안정적)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# GPU 버전 (CUDA 11.8)
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 문제 3: "임베딩 모델 다운로드 느림"

**원인:** 네트워크 속도

**해결:**
- 첫 실행 시만 다운로드 (1.1GB)
- 이후에는 캐시 사용
- 캐시 위치: `~/.cache/torch/sentence_transformers/`

**수동 다운로드:**
```bash
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
print('다운로드 완료')
"
```

### 문제 4: "psycopg2 설치 오류" (PostgreSQL)

**원인:** PostgreSQL 개발 헤더 미설치

**해결 (Ubuntu):**
```bash
sudo apt install libpq-dev python3-dev
pip install psycopg2
```

**해결 (Mac):**
```bash
brew install postgresql
pip install psycopg2
```

**해결 (Windows/모든 OS):**
```bash
# 바이너리 버전 사용
pip install psycopg2-binary
```

### 문제 5: "pgvector extension not found"

**원인:** pgvector 확장 미설치

**해결:**
```bash
# Ubuntu
sudo apt install postgresql-14-pgvector

# Mac
brew install pgvector

# Docker (추천)
docker run -d --name labsearch-db -p 5432:5432 ankane/pgvector
```

### 문제 6: "메모리 부족"

**원인:** 임베딩 모델이 RAM을 많이 사용

**해결:**
```python
# src/main_pipeline.py에서 배치 크기 줄이기
pipeline = EmbeddingPipeline(
    model_name='multilingual-mpnet',
    device='cpu',
    batch_size=8  # 기본값 32에서 줄임
)
```

### 문제 7: "CUDA out of memory" (GPU)

**원인:** GPU 메모리 부족

**해결:**
```python
# CPU 사용으로 전환
device='cpu'

# 또는 배치 크기 줄이기
batch_size=4
```

## 🎯 다음 단계

설치가 완료되었다면:

1. **[crawling.md](crawling.md)** - 크롤링 시작하기
2. **[search.md](search.md)** - 검색 사용법
3. **[architecture.md](architecture.md)** - 시스템 구조 이해하기

## 💡 권장 사항

### 초보자
- ✅ 로컬 모드 사용
- ✅ CPU 버전 사용
- ❌ PostgreSQL 설치하지 않음

### 중급자
- ✅ PostgreSQL 모드 (Docker)
- ✅ 선택 패키지 설치
- ✅ API 서버 실행

### 고급 사용자
- ✅ GPU 사용
- ✅ 커스텀 임베딩 모델
- ✅ 대규모 크롤링

## ✅ 설치 완료 체크리스트

- [ ] Python 3.8+ 설치
- [ ] 가상환경 생성 및 활성화
- [ ] requirements.txt 패키지 설치
- [ ] 임베딩 모델 다운로드 확인
- [ ] (선택) PostgreSQL + pgvector 설치
- [ ] (선택) .env 파일 설정
- [ ] 테스트 실행 성공

모든 항목을 완료했다면 [crawling.md](crawling.md)로 이동하세요! 🚀
