"""
벡터 인덱스 & DB 관리 모듈
- PostgreSQL + pgvector 연동
- HNSW 인덱스 관리
- 하이브리드 검색 (벡터 + 키워드)
- 중복 감지 (MD5)
"""

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from typing import List, Dict, Optional, Tuple
import numpy as np
from dataclasses import dataclass, asdict
import json
from datetime import datetime


@dataclass
class LabDocument:
    """연구실 문서 데이터"""
    lab_id: int
    section: str
    title: Optional[str]
    text: str
    lang: str
    tokens: int
    source_url: str
    parent_url: str
    crawl_depth: int
    source_type: str
    md5: str
    embedding: np.ndarray
    emb_model: str
    emb_ver: int
    quality_score: int = 0
    doc_id: Optional[int] = None


@dataclass
class SearchResult:
    """검색 결과"""
    doc_id: int
    lab_id: int
    lab_name: str
    section: str
    title: Optional[str]
    text: str
    score: float
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None


class DatabaseConfig:
    """데이터베이스 설정"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5432,
        database: str = 'labsearch',
        user: str = 'postgres',
        password: str = 'postgres'
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
    
    def get_connection_string(self) -> str:
        """연결 문자열 생성"""
        return f"host={self.host} port={self.port} dbname={self.database} user={self.user} password={self.password}"


class VectorDatabase:
    """벡터 데이터베이스 관리"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.conn = None
        self._connect()
    
    def _connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(self.config.get_connection_string())
            print(f"✅ DB 연결 성공: {self.config.database}")
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            raise
    
    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()
            print("DB 연결 종료")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ========================================================================
    # 연구실 (Lab) 관리
    # ========================================================================
    
    def insert_lab(self, lab_data: Dict) -> int:
        """연구실 정보 삽입"""
        query = """
        INSERT INTO lab (
            kor_name, eng_name, professor, homepage,
            location, contact_email, contact_phone, description
        )
        VALUES (%(kor_name)s, %(eng_name)s, %(professor)s, %(homepage)s,
                %(location)s, %(contact_email)s, %(contact_phone)s, %(description)s)
        ON CONFLICT DO NOTHING
        RETURNING lab_id
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, lab_data)
            result = cur.fetchone()
            self.conn.commit()
            
            if result:
                return result[0]
            else:
                # 이미 존재하는 경우 lab_id 조회
                cur.execute(
                    "SELECT lab_id FROM lab WHERE kor_name = %s",
                    (lab_data['kor_name'],)
                )
                return cur.fetchone()[0]
    
    def update_lab_crawl_status(
        self, 
        lab_id: int, 
        status: str, 
        quality_score: int = 0
    ):
        """크롤링 상태 업데이트"""
        query = """
        UPDATE lab
        SET last_crawled = CURRENT_TIMESTAMP,
            crawl_status = %s,
            quality_score = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE lab_id = %s
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (status, quality_score, lab_id))
            self.conn.commit()
    
    def get_lab_by_name(self, name: str) -> Optional[Dict]:
        """이름으로 연구실 조회"""
        query = "SELECT * FROM lab WHERE kor_name = %s OR eng_name = %s"
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (name, name))
            result = cur.fetchone()
            return dict(result) if result else None
    
    # ========================================================================
    # 문서 (Lab Docs) 관리
    # ========================================================================
    
    def check_duplicate(self, lab_id: int, md5: str) -> bool:
        """중복 문서 체크 (MD5)"""
        query = "SELECT check_duplicate_chunk(%s, %s)"
        
        with self.conn.cursor() as cur:
            cur.execute(query, (lab_id, md5))
            return cur.fetchone()[0]
    
    def insert_document(self, doc: LabDocument) -> int:
        """문서 삽입"""
        # 중복 체크
        if self.check_duplicate(doc.lab_id, doc.md5):
            print(f"  ⚠️  중복 문서 스킵 (MD5: {doc.md5[:8]}...)")
            return -1
        
        query = """
        INSERT INTO lab_docs (
            lab_id, section, title, text, lang, tokens,
            source_url, parent_url, crawl_depth, source_type,
            md5, embedding, emb_model, emb_ver, quality_score
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        RETURNING doc_id
        """
        
        # numpy 배열을 리스트로 변환
        embedding_list = doc.embedding.tolist()
        
        with self.conn.cursor() as cur:
            cur.execute(query, (
                doc.lab_id, doc.section, doc.title, doc.text, doc.lang, doc.tokens,
                doc.source_url, doc.parent_url, doc.crawl_depth, doc.source_type,
                doc.md5, embedding_list, doc.emb_model, doc.emb_ver, doc.quality_score
            ))
            doc_id = cur.fetchone()[0]
            self.conn.commit()
            return doc_id
    
    def insert_documents_batch(self, docs: List[LabDocument]) -> List[int]:
        """문서 배치 삽입"""
        doc_ids = []
        
        for doc in docs:
            doc_id = self.insert_document(doc)
            if doc_id > 0:
                doc_ids.append(doc_id)
        
        return doc_ids
    
    def get_document_count(self, lab_id: int) -> int:
        """연구실별 문서 수"""
        query = "SELECT COUNT(*) FROM lab_docs WHERE lab_id = %s"
        
        with self.conn.cursor() as cur:
            cur.execute(query, (lab_id,))
            return cur.fetchone()[0]
    
    # ========================================================================
    # 벡터 검색
    # ========================================================================
    
    def search_vector(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        min_quality: int = 0,
        section_filter: Optional[str] = None,
        lang_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """순수 벡터 검색"""
        query = """
        SELECT 
            d.doc_id,
            d.lab_id,
            l.kor_name as lab_name,
            d.section,
            d.title,
            d.text,
            1 - (d.embedding <=> %s::vector) as similarity
        FROM lab_docs d
        JOIN lab l ON d.lab_id = l.lab_id
        WHERE d.quality_score >= %s
        """
        
        params = [query_embedding.tolist(), min_quality]
        
        if section_filter:
            query += " AND d.section = %s"
            params.append(section_filter)
        
        if lang_filter:
            query += " AND d.lang = %s"
            params.append(lang_filter)
        
        query += """
        ORDER BY d.embedding <=> %s::vector
        LIMIT %s
        """
        params.extend([query_embedding.tolist(), limit])
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            
            return [
                SearchResult(
                    doc_id=r['doc_id'],
                    lab_id=r['lab_id'],
                    lab_name=r['lab_name'],
                    section=r['section'],
                    title=r['title'],
                    text=r['text'],
                    score=r['similarity'],
                    vector_score=r['similarity']
                )
                for r in results
            ]
    
    def search_hybrid(
        self,
        query_text: str,
        query_embedding: np.ndarray,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        min_quality: int = 0,
        section_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """하이브리드 검색 (벡터 + 키워드)"""
        query = """
        SELECT * FROM hybrid_search(
            %s, %s::vector, %s, %s, %s, %s
        )
        """
        
        params = [
            query_text,
            query_embedding.tolist(),
            limit,
            vector_weight,
            keyword_weight,
            min_quality
        ]
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            
            return [
                SearchResult(
                    doc_id=r['doc_id'],
                    lab_id=r['lab_id'],
                    lab_name=r['lab_name'],
                    section=r['section'],
                    title=r['title'],
                    text=r['text'],
                    score=r['hybrid_score'],
                    vector_score=r['vector_score'],
                    keyword_score=r['keyword_score']
                )
                for r in results
            ]
    
    # ========================================================================
    # 태그 관리
    # ========================================================================
    
    def insert_tag(
        self,
        lab_id: int,
        tag_type: str,
        value: str,
        confidence: float = 1.0,
        source: str = 'extraction'
    ):
        """태그 삽입"""
        query = """
        INSERT INTO lab_tag (lab_id, tag_type, value, confidence, source)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (lab_id, tag_type, value, confidence, source))
            self.conn.commit()
    
    def insert_tags_batch(
        self,
        lab_id: int,
        tags: List[Dict]
    ):
        """태그 배치 삽입"""
        query = """
        INSERT INTO lab_tag (lab_id, tag_type, value, confidence, source)
        VALUES %s
        ON CONFLICT DO NOTHING
        """
        
        values = [
            (lab_id, tag['type'], tag['value'], tag.get('confidence', 1.0), tag.get('source', 'extraction'))
            for tag in tags
        ]
        
        with self.conn.cursor() as cur:
            execute_values(cur, query, values)
            self.conn.commit()
    
    def get_lab_tags(self, lab_id: int) -> Dict[str, List[str]]:
        """연구실 태그 조회"""
        query = """
        SELECT tag_type, value
        FROM lab_tag
        WHERE lab_id = %s
        ORDER BY confidence DESC
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (lab_id,))
            results = cur.fetchall()
            
            tags = {}
            for tag_type, value in results:
                if tag_type not in tags:
                    tags[tag_type] = []
                tags[tag_type].append(value)
            
            return tags
    
    # ========================================================================
    # 링크 관리
    # ========================================================================
    
    def insert_link(
        self,
        lab_id: int,
        kind: str,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ):
        """링크 삽입"""
        query = """
        INSERT INTO lab_link (lab_id, kind, url, title, description)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (lab_id, kind, url, title, description))
            self.conn.commit()
    
    # ========================================================================
    # 로그
    # ========================================================================
    
    def log_crawl(
        self,
        lab_id: int,
        url: str,
        status: str,
        pages_visited: int = 0,
        chunks_created: int = 0,
        duration: float = 0,
        error_message: Optional[str] = None
    ):
        """크롤링 로그 기록"""
        query = """
        INSERT INTO crawl_log (
            lab_id, url, status, pages_visited, chunks_created,
            duration_seconds, error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (
                lab_id, url, status, pages_visited, chunks_created,
                duration, error_message
            ))
            self.conn.commit()
    
    def log_search(
        self,
        query: str,
        search_type: str,
        results_count: int,
        top_lab_ids: List[int],
        avg_score: float,
        duration_ms: int
    ):
        """검색 로그 기록"""
        query_sql = """
        INSERT INTO search_log (
            query, search_type, results_count, top_lab_ids,
            avg_score, duration_ms
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query_sql, (
                query, search_type, results_count, top_lab_ids,
                avg_score, duration_ms
            ))
            self.conn.commit()
    
    # ========================================================================
    # 통계 & 유틸
    # ========================================================================
    
    def get_stats(self) -> Dict:
        """전체 통계"""
        stats = {}
        
        with self.conn.cursor() as cur:
            # 연구실 수
            cur.execute("SELECT COUNT(*) FROM lab")
            stats['total_labs'] = cur.fetchone()[0]
            
            # 문서 수
            cur.execute("SELECT COUNT(*) FROM lab_docs")
            stats['total_docs'] = cur.fetchone()[0]
            
            # 섹션별 분포
            cur.execute("""
                SELECT section, COUNT(*) as count
                FROM lab_docs
                GROUP BY section
                ORDER BY count DESC
            """)
            stats['section_distribution'] = dict(cur.fetchall())
            
            # 언어별 분포
            cur.execute("""
                SELECT lang, COUNT(*) as count
                FROM lab_docs
                GROUP BY lang
                ORDER BY count DESC
            """)
            stats['language_distribution'] = dict(cur.fetchall())
            
            # 평균 품질 점수
            cur.execute("SELECT AVG(quality_score) FROM lab_docs")
            stats['avg_quality_score'] = round(cur.fetchone()[0] or 0, 2)
        
        return stats
    
    def execute_raw(self, query: str, params: Tuple = None):
        """원시 쿼리 실행"""
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            self.conn.commit()


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    # DB 설정
    config = DatabaseConfig(
        host='localhost',
        port=5432,
        database='labsearch',
        user='postgres',
        password='your_password'
    )
    
    # DB 연결
    with VectorDatabase(config) as db:
        # 통계 출력
        stats = db.get_stats()
        print("데이터베이스 통계:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
