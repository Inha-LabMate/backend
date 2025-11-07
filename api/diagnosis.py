"""
진단 결과 API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
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
from .database import get_db_connection, get_cursor

router = APIRouter(prefix="/api/diagnosis", tags=["Diagnosis"])

# 전역 변수
generator = None
scorer = None


def init_models():
    """모델 초기화"""
    global generator, scorer
    if generator is None:
        generator = CandidateGenerator()
    if scorer is None:
        scorer = RerankingScorer(DEFAULT_CONFIG)


# ============================================================================
# Response 모델
# ============================================================================

class ScoreDetail(BaseModel):
    """점수 상세"""
    intro1: float
    intro2: float
    intro3: float
    portfolio: float


class KeywordDetail(BaseModel):
    """키워드 점수 상세"""
    major: float
    certification: float
    award: float
    tech_stack: float


class NumericDetail(BaseModel):
    """정량 점수 상세"""
    language: float
    proficiency: float
    gpa: float


class LabResult(BaseModel):
    """연구실 추천 결과"""
    rank: int
    lab_id: str
    lab_name: str
    professor: str
    final_score: float
    sentence_score: float
    keyword_score: float
    numeric_score: float
    sentence_details: ScoreDetail
    keyword_details: KeywordDetail
    numeric_details: NumericDetail


class DiagnosisResponse(BaseModel):
    """진단 결과 응답"""
    status: str
    student_id: str
    config_type: str
    total_candidates: int
    top_results: List[LabResult]


# ============================================================================
# API 엔드포인트
# ============================================================================

@router.get("/results", response_model=DiagnosisResponse)
async def get_diagnosis_results(
    student_id: str = Query(..., description="학생 ID"),
    config_type: str = Query("default", description="설정 타입: default, research, skill, academic"),
    top_k: int = Query(5, description="상위 몇 개 결과", ge=1, le=20)
):
    """
    진단 결과 조회
    
    학생의 프로필을 기반으로 연구실 추천 결과 반환
    """
    try:
        # 모델 초기화
        init_models()
        
        # 1. 데이터베이스에서 학생 프로필 조회
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            cursor.execute(
                "SELECT * FROM student_profiles WHERE student_id = %s",
                (student_id,)
            )
            profile_data = cursor.fetchone()
        
        if not profile_data:
            raise HTTPException(status_code=404, detail="학생 프로필을 찾을 수 없습니다.")
        
        # 2. StudentProfile 객체 생성
        student_profile = StudentProfile(
            research_interests=profile_data.get('research_interests', ''),
            intro1=profile_data.get('intro1', ''),
            intro2=profile_data.get('intro2', ''),
            intro3=profile_data.get('intro3', ''),
            portfolio=profile_data.get('portfolio', ''),
            major=profile_data.get('major', ''),
            certifications=profile_data.get('certifications', ''),
            awards=profile_data.get('awards', ''),
            tech_stack=profile_data.get('tech_stack', ''),
            toeic_score=str(profile_data.get('toeic_score', '')),
            english_proficiency=profile_data.get('english_proficiency', ''),
            gpa=str(profile_data.get('gpa', ''))
        )
        
        # 3. 1단계: 후보군 생성
        student_query = Student(research_interests=student_profile.research_interests)
        result = generator.get_candidates_with_scores(student_query, final_top_k=10)
        
        # 후보군 리스트 생성
        candidates = []
        for lab_id, lab_info in result.items():
            lab = next((l for l in generator.labs if l.id == lab_id), None)
            if lab:
                candidates.append(lab)
        
        if not candidates:
            raise HTTPException(status_code=404, detail="추천할 연구실을 찾을 수 없습니다.")
        
        # 4. 설정 선택
        config_map = {
            "default": DEFAULT_CONFIG,
            "research": RESEARCH_CONFIG,
            "skill": SKILL_CONFIG,
            "academic": ACADEMIC_CONFIG
        }
        config = config_map.get(config_type, DEFAULT_CONFIG)
        
        # 5. 2단계: 재랭킹
        global scorer
        scorer = RerankingScorer(config)
        results = scorer.rerank_candidates(student_profile, candidates, top_k=top_k)
        
        # 6. 응답 생성
        lab_results = []
        for i, result in enumerate(results):
            # 연구실 정보 찾기
            lab = next((l for l in candidates if l.name == result.lab_name), None)
            professor = lab.professor if lab else "Unknown"
            
            lab_results.append(
                LabResult(
                    rank=i + 1,
                    lab_id=result.lab_id,
                    lab_name=result.lab_name,
                    professor=professor,
                    final_score=round(result.final_score, 4),
                    sentence_score=round(result.sentence_score, 4),
                    keyword_score=round(result.keyword_score, 4),
                    numeric_score=round(result.numeric_score, 4),
                    sentence_details=ScoreDetail(
                        intro1=round(result.intro1_score, 4),
                        intro2=round(result.intro2_score, 4),
                        intro3=round(result.intro3_score, 4),
                        portfolio=round(result.portfolio_score, 4)
                    ),
                    keyword_details=KeywordDetail(
                        major=round(result.major_score, 4),
                        certification=round(result.certification_score, 4),
                        award=round(result.award_score, 4),
                        tech_stack=round(result.tech_stack_score, 4)
                    ),
                    numeric_details=NumericDetail(
                        language=round(result.language_score, 4),
                        proficiency=round(result.proficiency_score, 4),
                        gpa=round(result.gpa_score, 4)
                    )
                )
            )
        
        return DiagnosisResponse(
            status="success",
            student_id=student_id,
            config_type=config_type,
            total_candidates=len(candidates),
            top_results=lab_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단 처리 중 오류 발생: {str(e)}")
