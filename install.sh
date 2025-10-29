#!/bin/bash
# 빠른 시작 스크립트

echo "=================================="
echo "연구실 검색 시스템 설치 스크립트"
echo "=================================="
echo

# 1. Python 버전 확인
echo "1. Python 버전 확인..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3가 설치되어 있지 않습니다."
    exit 1
fi

echo "✅ Python 확인 완료"
echo

# 2. 가상환경 생성
echo "2. 가상환경 생성..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
else
    echo "⚠️  가상환경이 이미 존재합니다."
fi

# 가상환경 활성화
source venv/bin/activate
echo

# 3. 패키지 설치
echo "3. Python 패키지 설치..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 패키지 설치 실패"
    exit 1
fi

echo "✅ 패키지 설치 완료"
echo

# 4. PostgreSQL 확인
echo "4. PostgreSQL 확인..."
psql --version

if [ $? -ne 0 ]; then
    echo "⚠️  PostgreSQL이 설치되어 있지 않습니다."
    echo "   Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "   macOS: brew install postgresql@14"
    echo "   Docker: docker run -d --name labsearch-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 ankane/pgvector"
else
    echo "✅ PostgreSQL 확인 완료"
fi
echo

# 5. 데이터베이스 생성 안내
echo "5. 데이터베이스 설정"
echo "   다음 명령어를 실행하세요:"
echo
echo "   psql -U postgres"
echo "   CREATE DATABASE labsearch;"
echo "   \\c labsearch"
echo "   \\i schema.sql"
echo "   \\q"
echo

# 6. 설정 파일 생성
echo "6. 환경 설정 파일 생성..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=labsearch
DB_USER=postgres
DB_PASSWORD=postgres

# 임베딩 모델
EMBEDDING_MODEL=multilingual-mpnet
DEVICE=cpu

# 크롤링 설정
MAX_PAGES=5
TIMEOUT=10
DELAY=1
EOF
    echo "✅ .env 파일 생성 완료"
else
    echo "⚠️  .env 파일이 이미 존재합니다."
fi
echo

# 7. 완료
echo "=================================="
echo "🎉 설치 완료!"
echo "=================================="
echo
echo "다음 단계:"
echo "1. PostgreSQL 데이터베이스 생성 (위 5번 참조)"
echo "2. .env 파일에서 DB 비밀번호 수정"
echo "3. 크롤링 실행: python main_pipeline.py"
echo "4. API 서버 실행: uvicorn search_api:app --reload"
echo
echo "테스트:"
echo "  python -c 'from chunking import DocumentProcessor; print(\"✅ Import OK\")'"
echo
