"""
FastAPI 연구실 추천 시스템 API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

# src 경로 추가
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from similarity import (
    CandidateGenerator,
    Student,
    RerankingScorer,
    StudentProfile,
    DEFAULT_CONFIG,
    RESEARCH_CONFIG,
    SKILL_CONFIG,
    ACADEMIC_CONFIG
)

# 이력서 API 라우터 임포트
from api.resume import router as resume_router
from api.diagnosis import router as diagnosis_router

# FastAPI 앱 생성
app = FastAPI(
    title="연구실 추천 시스템 API",
    description="학생 프로필 기반 연구실 추천 시스템",
    version="1.0.0"
)

# 라우터 등록
app.include_router(resume_router)
app.include_router(diagnosis_router)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수로 생성기와 스코어러 초기화
generator = None
scorer = None


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델 로드"""
    global generator, scorer
    print("🚀 연구실 추천 시스템 초기화 중...")
    generator = CandidateGenerator()
    scorer = RerankingScorer(DEFAULT_CONFIG)
    print("✅ 초기화 완료!")


# ============================================================================
# Request/Response 모델
# ============================================================================

class StudentProfileRequest(BaseModel):
    """학생 프로필 요청"""
    # 1단계: 후보군 생성용
    research_interests: str
    
    # 2단계: 재랭킹용 문장형 데이터
    intro1: Optional[str] = ""
    intro2: Optional[str] = ""
    intro3: Optional[str] = ""
    portfolio: Optional[str] = ""
    
    # 키워드형 데이터
    major: Optional[str] = ""
    certifications: Optional[str] = ""
    awards: Optional[str] = ""
    tech_stack: Optional[str] = ""
    
    # 정량형 데이터
    toeic_score: Optional[str] = ""
    opic_grade: Optional[str] = ""
    korean_proficiency: Optional[str] = ""
    english_proficiency: Optional[str] = ""
    gpa: Optional[str] = ""
    
    # 설정
    config_type: Optional[str] = "default"  # default, research, skill, academic
    top_k: Optional[int] = 5


class LabResponse(BaseModel):
    """연구실 추천 결과"""
    rank: int
    lab_name: str
    professor: str
    research_description: str  # 연구 내용
    final_score: float
    fitness_level: str  # 적합도: "매우 높음", "높음", "낮음"
    
    # 대분류 점수
    sentence_score: float
    keyword_score: float
    numeric_score: float
    
    # 상세 점수
    intro1_score: float
    intro2_score: float
    intro3_score: float
    portfolio_score: float
    major_score: float
    certification_score: float
    award_score: float
    tech_stack_score: float
    language_score: float
    proficiency_score: float
    gpa_score: float


class RecommendationResponse(BaseModel):
    """추천 응답"""
    status: str
    message: str
    total_candidates: int
    recommendations: List[LabResponse]


# ============================================================================
# API 엔드포인트
# ============================================================================

@app.get("/")
async def root():
    """API 루트"""
    return {
        "status": "ok",
        "message": "연구실 추천 시스템 API",
        "version": "1.0.0",
        "endpoints": {
            "POST /recommend": "연구실 추천",
            "GET /health": "헬스 체크"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "ok",
        "generator_loaded": generator is not None,
        "scorer_loaded": scorer is not None
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_labs(profile: StudentProfileRequest):
    """
    연구실 추천 API
    
    1단계: research_interests로 후보군 생성 (10개)
    2단계: 상세 프로필로 재랭킹
    """
    try:
        # 1단계: 후보군 생성
        student_query = Student(research_interests=profile.research_interests)
        result = generator.get_candidates_with_scores(
            student_query,
            final_top_k=10
        )
        
        # 후보군 리스트 생성
        candidates = []
        for lab_id, lab_info in result.items():
            lab = next((l for l in generator.labs if l.id == lab_id), None)
            if lab:
                candidates.append(lab)
        
        if not candidates:
            raise HTTPException(status_code=404, detail="추천할 연구실을 찾을 수 없습니다.")
        
        # 2단계: 재랭킹
        student_profile = StudentProfile(
            research_interests=profile.research_interests,
            intro1=profile.intro1,
            intro2=profile.intro2,
            intro3=profile.intro3,
            portfolio=profile.portfolio,
            major=profile.major,
            certifications=profile.certifications,
            awards=profile.awards,
            tech_stack=profile.tech_stack,
            toeic_score=profile.toeic_score,
            opic_grade=profile.opic_grade,
            korean_proficiency=profile.korean_proficiency,
            english_proficiency=profile.english_proficiency,
            gpa=profile.gpa
        )
        
        # 설정 선택
        config_map = {
            "default": DEFAULT_CONFIG,
            "research": RESEARCH_CONFIG,
            "skill": SKILL_CONFIG,
            "academic": ACADEMIC_CONFIG
        }
        config = config_map.get(profile.config_type, DEFAULT_CONFIG)
        
        # 스코어러 업데이트
        global scorer
        scorer = RerankingScorer(config)
        
        # 재랭킹 수행
        results = scorer.rerank_candidates(student_profile, candidates, top_k=profile.top_k)
        
        # 적합도 판정 함수
        def get_fitness_level(score: float) -> str:
            if score >= 0.7:
                return "매우 높음"
            elif score >= 0.5:
                return "높음"
            else:
                return "낮음"
        
        # 응답 생성
        recommendations = []
        for i, r in enumerate(results):
            # 연구실 정보 찾기
            lab = next((l for l in candidates if l.name == r.lab_name), None)
            
            recommendations.append(
                LabResponse(
                    rank=i + 1,
                    lab_name=r.lab_name,
                    professor=lab.professor if lab else "Unknown",
                    research_description=lab.description if lab else "",
                    final_score=r.final_score,
                    fitness_level=get_fitness_level(r.final_score),
                    sentence_score=r.sentence_score,
                    keyword_score=r.keyword_score,
                    numeric_score=r.numeric_score,
                    intro1_score=r.intro1_score,
                    intro2_score=r.intro2_score,
                    intro3_score=r.intro3_score,
                    portfolio_score=r.portfolio_score,
                    major_score=r.major_score,
                    certification_score=r.certification_score,
                    award_score=r.award_score,
                    tech_stack_score=r.tech_stack_score,
                    language_score=r.language_score,
                    proficiency_score=r.proficiency_score,
                    gpa_score=r.gpa_score
                )
            )
        
        return RecommendationResponse(
            status="success",
            message=f"{len(candidates)}개 후보 중 상위 {len(recommendations)}개 추천",
            total_candidates=len(candidates),
            recommendations=recommendations
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 서버 실행 (개발용)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
