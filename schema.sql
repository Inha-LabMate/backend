-- ============================================================================
-- 인하대 연구실 검색 시스템 - 데이터베이스 스키마
-- PostgreSQL 14+ with pgvector extension
-- ============================================================================

-- pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 텍스트 유사도 검색용

-- ============================================================================
-- 1. 연구실 기본 정보 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS lab (
    lab_id SERIAL PRIMARY KEY,
    kor_name VARCHAR(200) NOT NULL,
    eng_name VARCHAR(300),
    professor VARCHAR(100),
    homepage VARCHAR(500),
    location VARCHAR(200),
    contact_email VARCHAR(200),
    contact_phone VARCHAR(50),
    description TEXT,
    last_crawled TIMESTAMP,
    crawl_status VARCHAR(50),
    quality_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lab_kor_name ON lab(kor_name);
CREATE INDEX idx_lab_professor ON lab(professor);
CREATE INDEX idx_lab_quality ON lab(quality_score DESC);

-- ============================================================================
-- 2. 연구실 문서 청크 테이블 (벡터 검색 메인)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lab_docs (
    doc_id SERIAL PRIMARY KEY,
    lab_id INTEGER REFERENCES lab(lab_id) ON DELETE CASCADE,
    
    -- 섹션 정보
    section VARCHAR(50) NOT NULL,  -- about, research, publication, project, join, people
    title VARCHAR(500),
    text TEXT NOT NULL,
    
    -- 언어 & 토큰 정보
    lang VARCHAR(10) NOT NULL,  -- ko, en, mixed
    tokens INTEGER,  -- 토큰 수
    
    -- 출처 정보
    source_url VARCHAR(1000),
    parent_url VARCHAR(1000),
    crawl_depth INTEGER DEFAULT 0,
    source_type VARCHAR(20) DEFAULT 'html',  -- html, pdf, docx
    
    -- 중복 감지
    md5 CHAR(32) NOT NULL,  -- 텍스트 MD5 해시
    
    -- 임베딩
    embedding vector(768),  -- 768차원 벡터
    emb_model VARCHAR(100),  -- 모델명
    emb_ver INTEGER DEFAULT 1,  -- 임베딩 버전
    
    -- 검색용 tsvector (하이브리드 검색)
    text_tsv tsvector,
    
    -- 품질 정보
    quality_score INTEGER DEFAULT 0,
    
    -- 타임스탬프
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_docs_lab_id ON lab_docs(lab_id);
CREATE INDEX idx_docs_section ON lab_docs(section);
CREATE INDEX idx_docs_lang ON lab_docs(lang);
CREATE INDEX idx_docs_md5 ON lab_docs(md5);
CREATE INDEX idx_docs_quality ON lab_docs(quality_score DESC);

-- 벡터 검색용 HNSW 인덱스 (코사인 유사도)
-- M=32: 각 노드당 연결 수, ef_construction=128: 인덱스 생성 시 탐색 깊이
CREATE INDEX idx_docs_embedding ON lab_docs 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);

-- 하이브리드 검색용 GIN 인덱스
CREATE INDEX idx_docs_text_tsv ON lab_docs USING GIN(text_tsv);

-- tsvector 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_text_tsv() RETURNS trigger AS $$
BEGIN
    -- 한글/영문 혼합 텍스트 처리
    NEW.text_tsv := 
        setweight(to_tsvector('simple', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('simple', NEW.text), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_update_text_tsv 
BEFORE INSERT OR UPDATE ON lab_docs
FOR EACH ROW EXECUTE FUNCTION update_text_tsv();

-- ============================================================================
-- 3. 연구실 태그 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS lab_tag (
    tag_id SERIAL PRIMARY KEY,
    lab_id INTEGER REFERENCES lab(lab_id) ON DELETE CASCADE,
    tag_type VARCHAR(50) NOT NULL,  -- topic, method, equipment, venue, keyword
    value VARCHAR(200) NOT NULL,
    confidence FLOAT DEFAULT 1.0,  -- 태그 신뢰도
    source VARCHAR(50),  -- extraction, manual, llm
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tag_lab_id ON lab_tag(lab_id);
CREATE INDEX idx_tag_type ON lab_tag(tag_type);
CREATE INDEX idx_tag_value ON lab_tag(value);
CREATE INDEX idx_tag_composite ON lab_tag(tag_type, value);

-- ============================================================================
-- 4. 연구실 링크 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS lab_link (
    link_id SERIAL PRIMARY KEY,
    lab_id INTEGER REFERENCES lab(lab_id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL,  -- research, publication, people, join, github, youtube
    url VARCHAR(1000) NOT NULL,
    title VARCHAR(500),
    description TEXT,
    last_checked TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_link_lab_id ON lab_link(lab_id);
CREATE INDEX idx_link_kind ON lab_link(kind);
CREATE INDEX idx_link_active ON lab_link(is_active);

-- ============================================================================
-- 5. 크롤링 로그 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS crawl_log (
    log_id SERIAL PRIMARY KEY,
    lab_id INTEGER REFERENCES lab(lab_id) ON DELETE CASCADE,
    url VARCHAR(1000),
    status VARCHAR(50),  -- success, failed, timeout, robots_blocked
    pages_visited INTEGER DEFAULT 0,
    chunks_created INTEGER DEFAULT 0,
    duration_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crawl_lab_id ON crawl_log(lab_id);
CREATE INDEX idx_crawl_status ON crawl_log(status);
CREATE INDEX idx_crawl_created ON crawl_log(created_at DESC);

-- ============================================================================
-- 6. 검색 로그 테이블 (분석/최적화용)
-- ============================================================================
CREATE TABLE IF NOT EXISTS search_log (
    search_id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    search_type VARCHAR(20),  -- vector, keyword, hybrid
    results_count INTEGER,
    top_lab_ids INTEGER[],
    avg_score FLOAT,
    duration_ms INTEGER,
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_created ON search_log(created_at DESC);
CREATE INDEX idx_search_type ON search_log(search_type);

-- ============================================================================
-- 7. 임베딩 버전 관리 테이블
-- ============================================================================
CREATE TABLE IF NOT EXISTS embedding_version (
    version_id SERIAL PRIMARY KEY,
    version_number INTEGER UNIQUE NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    dimension INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 초기 버전 추가
INSERT INTO embedding_version (version_number, model_name, dimension, description, is_active)
VALUES (1, 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2', 768, 
        'Initial multilingual model for Korean/English support', TRUE)
ON CONFLICT (version_number) DO NOTHING;

-- ============================================================================
-- 8. 유용한 뷰 (View) 정의
-- ============================================================================

-- 연구실 통계 뷰
CREATE OR REPLACE VIEW lab_stats AS
SELECT 
    l.lab_id,
    l.kor_name,
    l.professor,
    COUNT(DISTINCT d.doc_id) as total_docs,
    COUNT(DISTINCT d.section) as sections_count,
    AVG(d.quality_score) as avg_doc_quality,
    COUNT(DISTINCT t.tag_id) as tags_count,
    COUNT(DISTINCT lk.link_id) as links_count,
    MAX(l.last_crawled) as last_crawled
FROM lab l
LEFT JOIN lab_docs d ON l.lab_id = d.lab_id
LEFT JOIN lab_tag t ON l.lab_id = t.lab_id
LEFT JOIN lab_link lk ON l.lab_id = lk.lab_id
GROUP BY l.lab_id, l.kor_name, l.professor;

-- 섹션별 문서 수 뷰
CREATE OR REPLACE VIEW section_distribution AS
SELECT 
    section,
    COUNT(*) as doc_count,
    AVG(tokens) as avg_tokens,
    AVG(quality_score) as avg_quality
FROM lab_docs
GROUP BY section
ORDER BY doc_count DESC;

-- ============================================================================
-- 9. 유용한 함수 정의
-- ============================================================================

-- 벡터 검색 함수 (순수 벡터)
CREATE OR REPLACE FUNCTION search_by_vector(
    query_embedding vector(768),
    result_limit INTEGER DEFAULT 10,
    min_quality INTEGER DEFAULT 0
)
RETURNS TABLE (
    doc_id INTEGER,
    lab_id INTEGER,
    lab_name VARCHAR,
    section VARCHAR,
    title VARCHAR,
    text TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.doc_id,
        d.lab_id,
        l.kor_name,
        d.section,
        d.title,
        d.text,
        1 - (d.embedding <=> query_embedding) as similarity
    FROM lab_docs d
    JOIN lab l ON d.lab_id = l.lab_id
    WHERE d.quality_score >= min_quality
    ORDER BY d.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- 하이브리드 검색 함수 (벡터 + 키워드)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(768),
    result_limit INTEGER DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    min_quality INTEGER DEFAULT 0
)
RETURNS TABLE (
    doc_id INTEGER,
    lab_id INTEGER,
    lab_name VARCHAR,
    section VARCHAR,
    title VARCHAR,
    text TEXT,
    hybrid_score FLOAT,
    vector_score FLOAT,
    keyword_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT 
            d.doc_id,
            1 - (d.embedding <=> query_embedding) as vscore
        FROM lab_docs d
        WHERE d.quality_score >= min_quality
    ),
    keyword_results AS (
        SELECT 
            d.doc_id,
            ts_rank_cd(d.text_tsv, plainto_tsquery('simple', query_text)) as kscore
        FROM lab_docs d
        WHERE d.quality_score >= min_quality
            AND d.text_tsv @@ plainto_tsquery('simple', query_text)
    )
    SELECT 
        d.doc_id,
        d.lab_id,
        l.kor_name,
        d.section,
        d.title,
        d.text,
        (COALESCE(v.vscore, 0) * vector_weight + COALESCE(k.kscore, 0) * keyword_weight) as hybrid_score,
        COALESCE(v.vscore, 0) as vector_score,
        COALESCE(k.kscore, 0) as keyword_score
    FROM lab_docs d
    JOIN lab l ON d.lab_id = l.lab_id
    LEFT JOIN vector_results v ON d.doc_id = v.doc_id
    LEFT JOIN keyword_results k ON d.doc_id = k.doc_id
    WHERE (v.vscore IS NOT NULL OR k.kscore IS NOT NULL)
        AND d.quality_score >= min_quality
    ORDER BY hybrid_score DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- 중복 청크 체크 함수
CREATE OR REPLACE FUNCTION check_duplicate_chunk(
    p_lab_id INTEGER,
    p_md5 CHAR(32)
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM lab_docs
        WHERE lab_id = p_lab_id AND md5 = p_md5
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 10. 권한 설정 (프로덕션 환경용)
-- ============================================================================

-- 읽기 전용 사용자 (검색 API용)
-- CREATE USER lab_search_ro WITH PASSWORD 'your_secure_password';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO lab_search_ro;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO lab_search_ro;

-- 읽기/쓰기 사용자 (크롤러용)
-- CREATE USER lab_crawler_rw WITH PASSWORD 'your_secure_password';
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO lab_crawler_rw;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lab_crawler_rw;

-- ============================================================================
-- 완료
-- ============================================================================
COMMENT ON TABLE lab IS '연구실 기본 정보';
COMMENT ON TABLE lab_docs IS '연구실 문서 청크 - 벡터 검색 메인 테이블';
COMMENT ON TABLE lab_tag IS '연구실 태그 (주제, 방법론, 장비 등)';
COMMENT ON TABLE lab_link IS '연구실 관련 링크';
COMMENT ON TABLE crawl_log IS '크롤링 로그';
COMMENT ON TABLE search_log IS '검색 로그 (분석용)';
COMMENT ON TABLE embedding_version IS '임베딩 모델 버전 관리';
