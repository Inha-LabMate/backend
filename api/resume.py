"""
이력서 관리 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .database import get_db_connection, get_cursor

router = APIRouter(prefix="/api/resume", tags=["Resume"])


# ============================================================================
# Request 모델
# ============================================================================

class BasicInfoRequest(BaseModel):
    student_id: str
    research_interests: str
    major: Optional[str] = None
    gpa: Optional[float] = None


class LanguageRequest(BaseModel):
    student_id: str
    toeic_score: Optional[int] = None
    english_proficiency: Optional[str] = None


class CertificateRequest(BaseModel):
    student_id: str
    certificate: str


class AwardRequest(BaseModel):
    student_id: str
    award: str


class PortfolioRequest(BaseModel):
    student_id: str
    portfolio_item: str


class CoverLetterRequest(BaseModel):
    student_id: str
    intro1: Optional[str] = None
    intro2: Optional[str] = None
    intro3: Optional[str] = None


# ============================================================================
# API 엔드포인트
# ============================================================================

@router.get("")
async def get_resume(student_id: str):
    """전체 조회"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute(
            "SELECT * FROM student_profiles WHERE student_id = %s",
            (student_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
        
        return dict(result)


@router.put("/basic-info")
async def update_basic_info(request: BasicInfoRequest):
    """기본 정보 수정"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        # 기존 프로필 확인
        cursor.execute(
            "SELECT id FROM student_profiles WHERE student_id = %s",
            (request.student_id,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # 업데이트
            cursor.execute(
                """
                UPDATE student_profiles 
                SET research_interests = %s, major = %s, gpa = %s, updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
                """,
                (request.research_interests, request.major, request.gpa, request.student_id)
            )
        else:
            # 새로 생성
            cursor.execute(
                """
                INSERT INTO student_profiles (student_id, research_interests, major, gpa)
                VALUES (%s, %s, %s, %s)
                """,
                (request.student_id, request.research_interests, request.major, request.gpa)
            )
        
        return {"status": "success", "message": "기본 정보가 저장되었습니다."}


@router.post("/language")
async def add_language(request: LanguageRequest):
    """언어 능력 추가"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            """
            UPDATE student_profiles 
            SET toeic_score = %s, english_proficiency = %s, updated_at = CURRENT_TIMESTAMP
            WHERE student_id = %s
            """,
            (request.toeic_score, request.english_proficiency, request.student_id)
        )
        
        return {"status": "success", "message": "언어 능력이 추가되었습니다."}


@router.delete("/language/{student_id}")
async def delete_language(student_id: str):
    """언어 능력 삭제"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            """
            UPDATE student_profiles 
            SET toeic_score = NULL, english_proficiency = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE student_id = %s
            """,
            (student_id,)
        )
        
        return {"status": "success", "message": "언어 능력이 삭제되었습니다."}


@router.post("/certificate")
async def add_certificate(request: CertificateRequest):
    """자격증 추가"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        # 기존 자격증 조회
        cursor.execute(
            "SELECT certifications FROM student_profiles WHERE student_id = %s",
            (request.student_id,)
        )
        result = cursor.fetchone()
        
        if result and result['certifications']:
            new_certs = result['certifications'] + ", " + request.certificate
        else:
            new_certs = request.certificate
        
        cursor.execute(
            """
            UPDATE student_profiles 
            SET certifications = %s, updated_at = CURRENT_TIMESTAMP
            WHERE student_id = %s
            """,
            (new_certs, request.student_id)
        )
        
        return {"status": "success", "message": "자격증이 추가되었습니다."}


@router.delete("/certificate/{student_id}")
async def delete_certificate(student_id: str, certificate: str):
    """자격증 삭제"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            "SELECT certifications FROM student_profiles WHERE student_id = %s",
            (student_id,)
        )
        result = cursor.fetchone()
        
        if result and result['certifications']:
            certs = [c.strip() for c in result['certifications'].split(',')]
            certs = [c for c in certs if c != certificate]
            new_certs = ", ".join(certs) if certs else None
            
            cursor.execute(
                """
                UPDATE student_profiles 
                SET certifications = %s, updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
                """,
                (new_certs, student_id)
            )
        
        return {"status": "success", "message": "자격증이 삭제되었습니다."}


@router.post("/award")
async def add_award(request: AwardRequest):
    """수상경력 추가"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            "SELECT awards FROM student_profiles WHERE student_id = %s",
            (request.student_id,)
        )
        result = cursor.fetchone()
        
        if result and result['awards']:
            new_awards = result['awards'] + ", " + request.award
        else:
            new_awards = request.award
        
        cursor.execute(
            """
            UPDATE student_profiles 
            SET awards = %s, updated_at = CURRENT_TIMESTAMP
            WHERE student_id = %s
            """,
            (new_awards, request.student_id)
        )
        
        return {"status": "success", "message": "수상경력이 추가되었습니다."}


@router.delete("/award/{student_id}")
async def delete_award(student_id: str, award: str):
    """수상경력 삭제"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            "SELECT awards FROM student_profiles WHERE student_id = %s",
            (student_id,)
        )
        result = cursor.fetchone()
        
        if result and result['awards']:
            awards = [a.strip() for a in result['awards'].split(',')]
            awards = [a for a in awards if a != award]
            new_awards = ", ".join(awards) if awards else None
            
            cursor.execute(
                """
                UPDATE student_profiles 
                SET awards = %s, updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
                """,
                (new_awards, student_id)
            )
        
        return {"status": "success", "message": "수상경력이 삭제되었습니다."}


@router.post("/portfolio")
async def add_portfolio(request: PortfolioRequest):
    """포트폴리오 추가"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            "SELECT portfolio FROM student_profiles WHERE student_id = %s",
            (request.student_id,)
        )
        result = cursor.fetchone()
        
        if result and result['portfolio']:
            new_portfolio = result['portfolio'] + " " + request.portfolio_item
        else:
            new_portfolio = request.portfolio_item
        
        cursor.execute(
            """
            UPDATE student_profiles 
            SET portfolio = %s, updated_at = CURRENT_TIMESTAMP
            WHERE student_id = %s
            """,
            (new_portfolio, request.student_id)
        )
        
        return {"status": "success", "message": "포트폴리오가 추가되었습니다."}


@router.delete("/portfolio/{student_id}")
async def delete_portfolio(student_id: str, portfolio_item: str):
    """포트폴리오 삭제"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            "SELECT portfolio FROM student_profiles WHERE student_id = %s",
            (student_id,)
        )
        result = cursor.fetchone()
        
        if result and result['portfolio']:
            new_portfolio = result['portfolio'].replace(portfolio_item, "").strip()
            
            cursor.execute(
                """
                UPDATE student_profiles 
                SET portfolio = %s, updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
                """,
                (new_portfolio if new_portfolio else None, student_id)
            )
        
        return {"status": "success", "message": "포트폴리오가 삭제되었습니다."}


@router.put("/cover-letter")
async def save_cover_letter(request: CoverLetterRequest):
    """자기소개서 저장"""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        
        cursor.execute(
            """
            UPDATE student_profiles 
            SET intro1 = %s, intro2 = %s, intro3 = %s, updated_at = CURRENT_TIMESTAMP
            WHERE student_id = %s
            """,
            (request.intro1, request.intro2, request.intro3, request.student_id)
        )
        
        return {"status": "success", "message": "자기소개서가 저장되었습니다."}
