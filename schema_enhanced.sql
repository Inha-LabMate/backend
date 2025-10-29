-- ============================================================================
-- 향상된 데이터베이스 스키마
-- ============================================================================
-- 
-- 추가 기능:
--   1. 품질 점수 및 검수 필드
--   2. 소프트 삭제 (is_active)
--   3. 크롤링 감사 로그
--   4. 업데이트 이력 추적
--   5. 검색/추천용 메타데이터
-- ============================================================================

-- pgvector 확장 활성화 (벡터 검색용)
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================================
-- 1. 연구실 정보 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS labs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,           -- 연구실 이름
    url TEXT NOT NULL UNIQUE,             -- 연구실 URL (고유)
    description TEXT,                     -- 간단한 설명
    professor VARCHAR(200),               -- 교수 이름
    department VARCHAR(200),              -- 소속 학과
    
    -- 검색/추천용 메타데이터
    recent_papers_count INT DEFAULT 0,    -- 최근 3년 논문 수
    has_awards BOOLEAN DEFAULT FALSE,     -- 수상 이력 여부
    equipment_gpu INT DEFAULT 0,          -- GPU 장비 수
    equipment_robot BOOLEAN DEFAULT FALSE, -- 로봇 장비 여부
    
    -- 모집 정보
    min_hours INT,                        -- 최소 참여 시간 (시간/주)
    weekend_ok BOOLEAN,                   -- 주말 가능 여부
    join_type VARCHAR(100),               -- 모집 유형: 학부연구생/대학원/인턴
    
    -- 관리 필드
    is_active BOOLEAN DEFAULT TRUE,       -- 활성화 여부 (소프트 삭제용)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_crawled_at TIMESTAMP,            -- 마지막 크롤링 시간
    
    -- 인덱스
    INDEX idx_labs_active (is_active),
    INDEX idx_labs_department (department)
);


-- ============================================================================
-- 2. 문서 테이블 (청크)
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    lab_id INT NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    
    -- 콘텐츠
    text TEXT NOT NULL,                   -- 청크 텍스트
    title VARCHAR(500),                   -- 제목
    section VARCHAR(50),                  -- 섹션 종류 (about, research, etc.)
    parent_heading VARCHAR(500),          -- 상위 헤딩
    
    -- 메타데이터
    char_count INT,                       -- 문자 수
    token_count INT,                      -- 토큰 수
    language VARCHAR(10),                 -- 언어 (ko, en, mixed)
    source_type VARCHAR(20) DEFAULT 'html', -- html, pdf, table
    source_url TEXT,                      -- 출처 URL
    crawl_depth INT DEFAULT 0,            -- 크롤링 깊이
    
    -- 품질 관리
    quality_score FLOAT DEFAULT 0.0,      -- 품질 점수 (0.0-1.0)
    needs_review BOOLEAN DEFAULT FALSE,   -- 검수 필요 여부
    review_reason TEXT,                   -- 검수 필요 이유
    has_pii BOOLEAN DEFAULT FALSE,        -- 개인정보 포함 여부
    is_duplicate BOOLEAN DEFAULT FALSE,   -- 중복 여부
    
    -- 벡터 임베딩
    embedding vector(768),                -- 768차원 벡터
    
    -- 검색 최적화
    matched_snippet TEXT,                 -- 추천 이유용 매칭 문장 (캐시)
    
    -- 관리 필드
    is_active BOOLEAN DEFAULT TRUE,       -- 활성화 여부 (소프트 삭제)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 인덱스
    INDEX idx_documents_lab (lab_id),
    INDEX idx_documents_section (section),
    INDEX idx_documents_quality (quality_score),
    INDEX idx_documents_review (needs_review),
    INDEX idx_documents_active (is_active)
);

-- 벡터 검색용 HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_documents_embedding 
ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);


-- ============================================================================
-- 3. 크롤링 감사 로그
-- ============================================================================

CREATE TABLE IF NOT EXISTS crawl_log (
    id SERIAL PRIMARY KEY,
    lab_id INT REFERENCES labs(id) ON DELETE SET NULL,
    url TEXT NOT NULL,                    -- 크롤링한 URL
    
    -- 요청 정보
    request_time TIMESTAMP DEFAULT NOW(),
    status_code INT,                      -- HTTP 상태 코드
    success BOOLEAN,                      -- 성공 여부
    
    -- 응답 정보
    response_size INT,                    -- 응답 크기 (바이트)
    response_time_ms INT,                 -- 응답 시간 (밀리초)
    
    -- 에러 정보
    error_message TEXT,                   -- 에러 메시지
    error_type VARCHAR(100),              -- 에러 타입 (timeout, 404, etc.)
    
    -- 결과 정보
    chunks_created INT DEFAULT 0,         -- 생성된 청크 수
    chunks_excluded INT DEFAULT 0,        -- 제외된 청크 수 (PII, 품질 등)
    
    -- 캐시 정보
    used_cache BOOLEAN DEFAULT FALSE,     -- 캐시 사용 여부
    etag TEXT,                            -- ETag
    last_modified TEXT,                   -- Last-Modified
    
    -- 인덱스
    INDEX idx_crawl_log_lab (lab_id),
    INDEX idx_crawl_log_time (request_time),
    INDEX idx_crawl_log_success (success)
);


-- ============================================================================
-- 4. 업데이트 이력 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS update_history (
    id SERIAL PRIMARY KEY,
    lab_id INT NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    
    -- 변경 내용
    change_type VARCHAR(50),              -- added, modified, deleted
    field_name VARCHAR(100),              -- 변경된 필드
    old_value TEXT,                       -- 이전 값
    new_value TEXT,                       -- 새 값
    
    -- 메타데이터
    detected_at TIMESTAMP DEFAULT NOW(),
    crawl_log_id INT REFERENCES crawl_log(id),
    
    -- 인덱스
    INDEX idx_update_history_lab (lab_id),
    INDEX idx_update_history_time (detected_at)
);


-- ============================================================================
-- 5. 연락처 정보 테이블 (PII 주의)
-- ============================================================================

CREATE TABLE IF NOT EXISTS contact_info (
    id SERIAL PRIMARY KEY,
    lab_id INT NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    
    -- 연락처 (민감 정보)
    email VARCHAR(255),
    phone VARCHAR(50),
    office_location VARCHAR(500),
    
    -- 공개 여부
    is_public BOOLEAN DEFAULT TRUE,       -- 공개 정보인지 확인
    
    -- 관리 필드
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 인덱스
    INDEX idx_contact_lab (lab_id),
    
    -- 제약: 중복 방지
    UNIQUE (lab_id, email)
);


-- ============================================================================
-- 6. 논문/프로젝트 메타데이터 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS publications (
    id SERIAL PRIMARY KEY,
    lab_id INT NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    
    -- 논문 정보
    title TEXT NOT NULL,
    authors TEXT,
    venue VARCHAR(200),                   -- 학회/저널 이름
    year INT,
    pdf_url TEXT,
    
    -- 태그
    lab_tag VARCHAR(100),                 -- venue/year 조합 (예: CVPR2024)
    
    -- 관리 필드
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 인덱스
    INDEX idx_publications_lab (lab_id),
    INDEX idx_publications_year (year),
    INDEX idx_publications_venue (venue)
);


-- ============================================================================
-- 7. 유용한 뷰 (View)
-- ============================================================================

-- 활성 연구실 요약
CREATE OR REPLACE VIEW active_labs_summary AS
SELECT 
    l.id,
    l.name,
    l.professor,
    l.department,
    l.recent_papers_count,
    l.last_crawled_at,
    COUNT(DISTINCT d.id) as total_documents,
    COUNT(DISTINCT CASE WHEN d.needs_review THEN d.id END) as docs_need_review,
    AVG(d.quality_score) as avg_quality
FROM labs l
LEFT JOIN documents d ON l.id = d.lab_id AND d.is_active = TRUE
WHERE l.is_active = TRUE
GROUP BY l.id;


-- 크롤링 성공률 통계
CREATE OR REPLACE VIEW crawl_statistics AS
SELECT 
    DATE(request_time) as crawl_date,
    COUNT(*) as total_requests,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN used_cache THEN 1 ELSE 0 END) as from_cache,
    AVG(response_time_ms) as avg_response_time_ms
FROM crawl_log
GROUP BY DATE(request_time)
ORDER BY crawl_date DESC;


-- ============================================================================
-- 8. 유용한 함수
-- ============================================================================

-- 소프트 삭제 함수
CREATE OR REPLACE FUNCTION soft_delete_document(doc_id INT)
RETURNS VOID AS $$
BEGIN
    UPDATE documents 
    SET is_active = FALSE, updated_at = NOW()
    WHERE id = doc_id;
END;
$$ LANGUAGE plpgsql;


-- 품질 점수 업데이트 트리거
CREATE OR REPLACE FUNCTION update_document_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_update
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_document_timestamp();


-- ============================================================================
-- 샘플 데이터 (테스트용)
-- ============================================================================

-- 샘플 연구실
INSERT INTO labs (name, url, professor, department, recent_papers_count, has_awards, equipment_gpu)
VALUES 
    ('Computer Vision Lab', 'https://example.com/cvlab', '김교수', '전자공학과', 15, TRUE, 8),
    ('NLP Research Lab', 'https://example.com/nlplab', '이교수', '컴퓨터공학과', 12, FALSE, 4)
ON CONFLICT (url) DO NOTHING;
