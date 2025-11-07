# API 문서

연구실 추천 시스템의 REST API 문서입니다.

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일 내용:
```bash
# PostgreSQL 데이터베이스 설정
DB_HOST=your_host_here
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 2. 필수 패키지 설치

```bash
pip install fastapi uvicorn psycopg2-binary python-dotenv
```

### 3. 데이터베이스 테이블 생성

```sql
CREATE TABLE IF NOT EXISTS student_profiles (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) UNIQUE,
    
    -- 1단계: 후보군 생성용
    research_interests TEXT NOT NULL,
    
    -- 2단계: 재랭킹용 문장형 데이터
    intro1 TEXT,
    intro2 TEXT,
    intro3 TEXT,
    portfolio TEXT,
    
    -- 학력 및 자격
    major VARCHAR(100),
    certifications TEXT,
    awards TEXT,
    tech_stack TEXT,
    
    -- 어학 능력
    toeic_score INTEGER,
    english_proficiency VARCHAR(20),
    
    -- 학업 성적
    gpa DECIMAL(3, 2),
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 서버 실행

```bash
# 방법 1: Python으로 직접 실행
python api/main.py

# 방법 2: uvicorn으로 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. API 문서 확인

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📋 API 엔드포인트

### 1. 이력서 관리 API (`/api/resume`)

#### 1.1 전체 조회
```http
GET /api/resume?student_id={학번}
```

**응답 예시:**
```json
{
  "id": 1,
  "student_id": "20231234",
  "research_interests": "컴퓨터 비전, 딥러닝",
  "intro1": "컴퓨터 비전과 딥러닝...",
  "intro2": "Python, PyTorch...",
  "intro3": "Vision Transformer...",
  "portfolio": "[프로젝트 1] YOLO...",
  "major": "컴퓨터공학",
  "certifications": "정보처리기사, 빅데이터분석기사",
  "awards": "AI 해커톤 우수상",
  "tech_stack": "Python, PyTorch, TensorFlow",
  "toeic_score": 850,
  "english_proficiency": "중상",
  "gpa": 4.0,
  "created_at": "2025-11-07T10:00:00",
  "updated_at": "2025-11-07T10:00:00"
}
```

#### 1.2 기본 정보 수정
```http
PUT /api/resume/basic-info
Content-Type: application/json

{
  "student_id": "20231234",
  "research_interests": "컴퓨터 비전, 딥러닝",
  "major": "컴퓨터공학",
  "gpa": 4.0
}
```

#### 1.3 언어 능력 추가
```http
POST /api/resume/language
Content-Type: application/json

{
  "student_id": "20231234",
  "toeic_score": 850,
  "english_proficiency": "중상"
}
```

#### 1.4 언어 능력 삭제
```http
DELETE /api/resume/language/{student_id}
```

#### 1.5 자격증 추가
```http
POST /api/resume/certificate
Content-Type: application/json

{
  "student_id": "20231234",
  "certificate": "정보처리기사"
}
```

#### 1.6 자격증 삭제
```http
DELETE /api/resume/certificate/{student_id}?certificate=정보처리기사
```

#### 1.7 수상경력 추가
```http
POST /api/resume/award
Content-Type: application/json

{
  "student_id": "20231234",
  "award": "AI 해커톤 대회 우수상"
}
```

#### 1.8 수상경력 삭제
```http
DELETE /api/resume/award/{student_id}?award=AI 해커톤 대회 우수상
```

#### 1.9 포트폴리오 추가
```http
POST /api/resume/portfolio
Content-Type: application/json

{
  "student_id": "20231234",
  "portfolio_item": "[프로젝트 1] YOLO v5 기반 실시간 객체 탐지 시스템"
}
```

#### 1.10 포트폴리오 삭제
```http
DELETE /api/resume/portfolio/{student_id}?portfolio_item=[프로젝트 1]...
```

#### 1.11 자기소개서 저장
```http
PUT /api/resume/cover-letter
Content-Type: application/json

{
  "student_id": "20231234",
  "intro1": "컴퓨터 비전과 딥러닝을 활용한...",
  "intro2": "Python, PyTorch를 사용하여...",
  "intro3": "Vision Transformer를 연구하여..."
}
```

---

### 2. 진단 결과 API (`/api/diagnosis`)

#### 2.1 연구실 추천 결과 조회
```http
GET /api/diagnosis/results?student_id={학번}&config_type={설정타입}&top_k={개수}
```

**파라미터:**
- `student_id` (필수): 학생 ID
- `config_type` (선택, 기본값: default): 추천 설정
  - `default`: 기본 (문장 60%, 키워드 30%, 정량 10%)
  - `research`: 연구 중심 (문장 80%, 키워드 15%, 정량 5%)
  - `skill`: 기술 중심 (문장 40%, 키워드 50%, 정량 10%)
  - `academic`: 학업 중심 (문장 40%, 키워드 30%, 정량 30%)
- `top_k` (선택, 기본값: 5): 추천 개수 (1~20)

**응답 예시:**
```json
{
  "status": "success",
  "student_id": "20231234",
  "config_type": "default",
  "total_candidates": 10,
  "top_results": [
    {
      "rank": 1,
      "lab_id": "lab_001",
      "lab_name": "컴퓨터 비전 연구실",
      "professor": "홍길동",
      "final_score": 0.8542,
      "sentence_score": 0.9123,
      "keyword_score": 0.7845,
      "numeric_score": 0.8234,
      "sentence_details": {
        "intro1": 0.95,
        "intro2": 0.88,
        "intro3": 0.92,
        "portfolio": 0.90
      },
      "keyword_details": {
        "major": 0.85,
        "certification": 0.75,
        "award": 0.80,
        "tech_stack": 0.73
      },
      "numeric_details": {
        "language": 0.90,
        "proficiency": 0.85,
        "gpa": 0.72
      }
    },
    {
      "rank": 2,
      "lab_id": "lab_002",
      "lab_name": "딥러닝 연구실",
      "professor": "김철수",
      "final_score": 0.8234,
      "sentence_score": 0.8845,
      "keyword_score": 0.7623,
      "numeric_score": 0.8012,
      "sentence_details": {
        "intro1": 0.92,
        "intro2": 0.85,
        "intro3": 0.89,
        "portfolio": 0.88
      },
      "keyword_details": {
        "major": 0.82,
        "certification": 0.73,
        "award": 0.78,
        "tech_stack": 0.71
      },
      "numeric_details": {
        "language": 0.88,
        "proficiency": 0.82,
        "gpa": 0.70
      }
    }
  ]
}
```

**동작 방식:**
1. DB에서 `student_id`로 학생 프로필 조회
2. **1단계 (후보군 생성)**: `research_interests`로 BM25 + E5-small 하이브리드 검색하여 10개 연구실 추출
3. **2단계 (재랭킹)**: 상세 프로필(intro1~3, portfolio, 자격증, 수상경력 등)로 정밀 점수 계산
4. 상위 `top_k`개 결과 반환

---

## 🧪 테스트

### DB 연결 테스트
```bash
python api/test_db_connection.py
```

**출력 예시:**
```
🔌 PostgreSQL 연결 테스트
⏳ 연결 시도 중...
✅ 연결 성공!

📦 PostgreSQL 버전:
   PostgreSQL 18.0 (Ubuntu 18.0-1.pgdg22.04+3)...

✅ student_profiles 테이블 존재
📊 테이블 구조 (16개 컬럼)
📈 저장된 데이터: 0개

✅ 테스트 완료!
```

### API 테스트 (Swagger UI 사용)
1. 서버 실행: `python api/main.py`
2. 브라우저에서 http://localhost:8000/docs 접속
3. "Try it out" 버튼으로 각 API 테스트

---

## 🔧 문제 해결

### PostgreSQL 연결 실패
1. **서버가 실행 중인지 확인**
   ```bash
   sudo systemctl status postgresql
   sudo systemctl start postgresql
   ```

2. **원격 접속 허용 설정**
   
   `postgresql.conf`:
   ```conf
   listen_addresses = '*'
   ```
   
   `pg_hba.conf`:
   ```conf
   host    all             all             0.0.0.0/0               md5
   ```
   
   ```bash
   sudo systemctl restart postgresql
   ```

3. **방화벽 포트 확인**
   ```bash
   sudo ufw allow 5432/tcp
   sudo netstat -tulpn | grep 5432
   ```

### Import 오류
```bash
# src 경로가 Python path에 없을 때
export PYTHONPATH="${PYTHONPATH}:/path/to/code"
```

---

## 📚 관련 문서

- [전체 시스템 문서](../docs/README.md)
- [추천 알고리즘 문서](../src/similarity/README.md)
- [유사도 계산 상세](../docs/similarity.md)
