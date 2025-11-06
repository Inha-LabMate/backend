"""
검색 API 예시 (FastAPI)

실행:
uvicorn search_api:app --reload --port 8000

테스트:
curl "http://localhost:8000/search?query=컴퓨터+비전&limit=5"
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time

from storage.vector_db import VectorDatabase, DatabaseConfig, SearchResult
from core.embedding import EmbeddingPipeline

# FastAPI 앱
app = FastAPI(
    title="연구실 검색 API",
    description="인하대 전기컴퓨터공학과 연구실 벡터 검색 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
db = None
embedding_pipeline = None


# 응답 모델
class SearchResultModel(BaseModel):
    doc_id: int
    lab_id: int
    lab_name: str
    section: str
    title: Optional[str]
    text: str
    score: float
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    search_type: str
    results: List[SearchResultModel]
    total_results: int
    duration_ms: int


class StatsResponse(BaseModel):
    total_labs: int
    total_docs: int
    avg_quality_score: float
    section_distribution: dict
    language_distribution: dict


# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델 로드"""
    global db, embedding_pipeline
    
    print("🚀 API 서버 시작...")
    
    # DB 연결
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        database='labsearch',
        user='postgres',
        password='postgres'  # 환경변수로 관리 권장
    )
    
    db = VectorDatabase(db_config)
    print("✅ DB 연결 완료")
    
    # 임베딩 파이프라인 로드
    embedding_pipeline = EmbeddingPipeline(
        model_name='multilingual-mpnet',
        device='cpu',
        use_cache=True
    )
    print("✅ 임베딩 모델 로드 완료")
    print(f"   모델: {embedding_pipeline.get_info()['full_name']}")
    print()


# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 리소스 정리"""
    global db
    if db:
        db.close()
    print("👋 API 서버 종료")


# 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "연구실 검색 API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search",
            "search_hybrid": "/search/hybrid",
            "stats": "/stats"
        }
    }


@app.get("/search", response_model=SearchResponse)
async def search_vector(
    query: str = Query(..., description="검색 쿼리", min_length=1),
    limit: int = Query(10, ge=1, le=50, description="결과 수"),
    min_quality: int = Query(0, ge=0, le=100, description="최소 품질 점수"),
    section: Optional[str] = Query(None, description="섹션 필터"),
    lang: Optional[str] = Query(None, description="언어 필터 (ko/en/mixed)")
):
    """
    벡터 검색
    
    **Parameters:**
    - query: 검색어
    - limit: 최대 결과 수 (기본 10)
    - min_quality: 최소 품질 점수 (0-100)
    - section: 섹션 필터 (about/research/publication/project/join/people)
    - lang: 언어 필터 (ko/en/mixed)
    """
    start_time = time.time()
    
    try:
        # 쿼리 임베딩
        query_emb = embedding_pipeline.embed(query)
        
        # 검색
        results = db.search_vector(
            query_embedding=query_emb.embedding,
            limit=limit,
            min_quality=min_quality,
            section_filter=section,
            lang_filter=lang
        )
        
        # 응답 생성
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 검색 로그
        if results:
            db.log_search(
                query=query,
                search_type='vector',
                results_count=len(results),
                top_lab_ids=[r.lab_id for r in results[:5]],
                avg_score=sum(r.score for r in results) / len(results),
                duration_ms=duration_ms
            )
        
        return SearchResponse(
            query=query,
            search_type='vector',
            results=[
                SearchResultModel(
                    doc_id=r.doc_id,
                    lab_id=r.lab_id,
                    lab_name=r.lab_name,
                    section=r.section,
                    title=r.title,
                    text=r.text[:500],  # 텍스트 길이 제한
                    score=r.score,
                    vector_score=r.vector_score
                )
                for r in results
            ],
            total_results=len(results),
            duration_ms=duration_ms
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/hybrid", response_model=SearchResponse)
async def search_hybrid(
    query: str = Query(..., description="검색 쿼리", min_length=1),
    limit: int = Query(10, ge=1, le=50),
    vector_weight: float = Query(0.7, ge=0.0, le=1.0),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0),
    min_quality: int = Query(0, ge=0, le=100),
    section: Optional[str] = Query(None)
):
    """
    하이브리드 검색 (벡터 + 키워드)
    
    **Parameters:**
    - query: 검색어
    - limit: 최대 결과 수
    - vector_weight: 벡터 검색 가중치 (기본 0.7)
    - keyword_weight: 키워드 검색 가중치 (기본 0.3)
    - min_quality: 최소 품질 점수
    - section: 섹션 필터
    """
    start_time = time.time()
    
    try:
        # 쿼리 임베딩
        query_emb = embedding_pipeline.embed(query)
        
        # 하이브리드 검색
        results = db.search_hybrid(
            query_text=query,
            query_embedding=query_emb.embedding,
            limit=limit,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            min_quality=min_quality,
            section_filter=section
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 로그
        if results:
            db.log_search(
                query=query,
                search_type='hybrid',
                results_count=len(results),
                top_lab_ids=[r.lab_id for r in results[:5]],
                avg_score=sum(r.score for r in results) / len(results),
                duration_ms=duration_ms
            )
        
        return SearchResponse(
            query=query,
            search_type='hybrid',
            results=[
                SearchResultModel(
                    doc_id=r.doc_id,
                    lab_id=r.lab_id,
                    lab_name=r.lab_name,
                    section=r.section,
                    title=r.title,
                    text=r.text[:500],
                    score=r.score,
                    vector_score=r.vector_score,
                    keyword_score=r.keyword_score
                )
                for r in results
            ],
            total_results=len(results),
            duration_ms=duration_ms
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """데이터베이스 통계"""
    try:
        stats = db.get_stats()
        
        return StatsResponse(
            total_labs=stats['total_labs'],
            total_docs=stats['total_docs'],
            avg_quality_score=stats['avg_quality_score'],
            section_distribution=stats.get('section_distribution', {}),
            language_distribution=stats.get('language_distribution', {})
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "db_connected": db is not None,
        "model_loaded": embedding_pipeline is not None
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "search_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
