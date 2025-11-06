"""
통합 재랭킹 스코어러
후보군 연구실들에 대해 모든 유사도를 계산하고 최종 점수 산출
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path

from .config import ScorerConfig, DEFAULT_CONFIG
from .base import SimilarityResult
from .sentence_similarity import (
    SentenceSimilarity,
    SentenceSimilarityWithKeyword,
    PortfolioSimilarity
)
from .keyword_similarity import (
    MajorSimilarity,
    CertificationSimilarity,
    AwardSimilarity,
    TechStackSimilarity
)
from .numeric_similarity import (
    LanguageScoreSimilarity,
    LanguageProficiencySimilarity,
    GPASimilarity
)
from .candidate_generator import Lab, Student


@dataclass
class StudentProfile:
    """학생 프로필 (재랭킹용 상세 정보)"""
    # 문장형 데이터
    intro1: str = ""  # 관심 연구 분야
    intro2: str = ""  # 기술 경험
    intro3: str = ""  # 연구 목표
    portfolio: str = ""  # 포트폴리오
    
    # 키워드형 데이터
    major: str = ""  # 전공
    certifications: str = ""  # 자격증 (콤마 구분)
    awards: str = ""  # 수상경력
    tech_stack: str = ""  # 기술 스택 (콤마 구분)
    
    # 정량형 데이터
    toeic_score: str = ""  # TOEIC 점수
    opic_grade: str = ""  # OPIc 등급
    korean_proficiency: str = ""  # 한국어 구사능력
    english_proficiency: str = ""  # 영어 구사능력
    gpa: str = ""  # 학점
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "intro1": self.intro1,
            "intro2": self.intro2,
            "intro3": self.intro3,
            "portfolio": self.portfolio,
            "major": self.major,
            "certifications": self.certifications,
            "awards": self.awards,
            "tech_stack": self.tech_stack,
            "toeic_score": self.toeic_score,
            "opic_grade": self.opic_grade,
            "korean_proficiency": self.korean_proficiency,
            "english_proficiency": self.english_proficiency,
            "gpa": self.gpa,
        }


@dataclass
class RerankingScore:
    """재랭킹 점수 상세"""
    lab_id: str
    lab_name: str
    
    # 대분류 점수
    sentence_score: float = 0.0
    keyword_score: float = 0.0
    numeric_score: float = 0.0
    
    # 문장형 세부 점수
    intro1_score: float = 0.0
    intro2_score: float = 0.0
    intro3_score: float = 0.0
    portfolio_score: float = 0.0
    
    # 키워드형 세부 점수
    major_score: float = 0.0
    certification_score: float = 0.0
    award_score: float = 0.0
    tech_stack_score: float = 0.0
    
    # 정량형 세부 점수
    language_score: float = 0.0
    proficiency_score: float = 0.0
    gpa_score: float = 0.0
    
    # 최종 점수
    final_score: float = 0.0
    
    # 추가 정보
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "lab_id": self.lab_id,
            "lab_name": self.lab_name,
            "final_score": round(self.final_score, 4),
            "sentence_score": round(self.sentence_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "numeric_score": round(self.numeric_score, 4),
            "details": {
                "sentence": {
                    "intro1": round(self.intro1_score, 4),
                    "intro2": round(self.intro2_score, 4),
                    "intro3": round(self.intro3_score, 4),
                    "portfolio": round(self.portfolio_score, 4),
                },
                "keyword": {
                    "major": round(self.major_score, 4),
                    "certification": round(self.certification_score, 4),
                    "award": round(self.award_score, 4),
                    "tech_stack": round(self.tech_stack_score, 4),
                },
                "numeric": {
                    "language": round(self.language_score, 4),
                    "proficiency": round(self.proficiency_score, 4),
                    "gpa": round(self.gpa_score, 4),
                }
            }
        }


class RerankingScorer:
    """
    재랭킹 스코어러
    후보군 연구실들에 대해 모든 유사도를 계산하고 최종 점수 산출
    """
    
    def __init__(self, config: Optional[ScorerConfig] = None):
        """
        Args:
            config: 스코어러 설정 (None이면 기본 설정 사용)
        """
        self.config = config or DEFAULT_CONFIG
        self.config.validate()
        
        # 문장형 유사도 측정기
        self.sentence_sim = SentenceSimilarity(self.config.sentence.model_name)
        self.sentence_keyword_sim = SentenceSimilarityWithKeyword(
            self.config.sentence.model_name
        )
        self.portfolio_sim = PortfolioSimilarity(self.config.sentence.model_name)
        
        # 키워드형 유사도 측정기
        self.major_sim = MajorSimilarity()
        self.cert_sim = CertificationSimilarity()
        self.award_sim = AwardSimilarity()
        self.tech_sim = TechStackSimilarity(self.config.keyword.tech_embedding_model)
        
        # 정량형 유사도 측정기
        self.language_sim = LanguageScoreSimilarity(score_type="toeic")
        self.proficiency_sim = LanguageProficiencySimilarity()
        self.gpa_sim = GPASimilarity(self.config.numeric.default_expected_gpa)
        
        print(f"✅ 재랭킹 스코어러 초기화 완료")
        print(f"   대분류 가중치: 문장={self.config.sentence_weight}, "
              f"키워드={self.config.keyword_weight}, 정량={self.config.numeric_weight}")
    
    def score_lab(
        self, 
        student: StudentProfile, 
        lab: Lab
    ) -> RerankingScore:
        """
        단일 연구실에 대한 재랭킹 점수 계산
        
        Args:
            student: 학생 프로필
            lab: 연구실 정보
            
        Returns:
            RerankingScore 객체
        """
        score = RerankingScore(lab_id=lab.id, lab_name=lab.name)
        
        # 연구실 텍스트 통합
        lab_research = lab.sections.get("research", "")
        lab_about = lab.sections.get("about", "")
        lab_methods = lab.sections.get("methods", "")
        lab_projects = lab.sections.get("projects", "")
        
        # 1. 문장형 유사도
        if student.intro1:
            result = self.sentence_sim.calculate(student.intro1, lab_research + " " + lab_about)
            score.intro1_score = result.score
        
        if student.intro2:
            result = self.sentence_keyword_sim.calculate(
                student.intro2, 
                lab_methods + " " + lab_projects,
                keyword_weight=self.config.sentence.keyword_overlap_weight
            )
            score.intro2_score = result.score
        
        if student.intro3:
            lab_vision = lab.sections.get("vision", lab_about)
            result = self.sentence_sim.calculate(student.intro3, lab_vision)
            score.intro3_score = result.score
        
        if student.portfolio:
            lab_full = " ".join(lab.sections.values())
            result = self.portfolio_sim.calculate(
                student.portfolio, 
                lab_full,
                chunk_size=self.config.sentence.portfolio_chunk_size
            )
            score.portfolio_score = result.score
        
        # 문장형 총점
        score.sentence_score = (
            score.intro1_score * self.config.sentence.intro1_weight +
            score.intro2_score * self.config.sentence.intro2_weight +
            score.intro3_score * self.config.sentence.intro3_weight +
            score.portfolio_score * self.config.sentence.portfolio_weight
        )
        
        # 2. 키워드형 유사도
        if student.major and lab.department:
            result = self.major_sim.calculate(student.major, lab.department)
            score.major_score = result.score
        
        if student.certifications:
            # 연구실에서 요구하는 자격증 정보 (임시로 빈 문자열, 실제로는 DB에서)
            lab_certs = lab.sections.get("requirements", "")
            if lab_certs:
                result = self.cert_sim.calculate(student.certifications, lab_certs)
                score.certification_score = result.score
            else:
                score.certification_score = 0.5  # 요구사항 없으면 중립
        
        if student.awards:
            lab_achievements = lab.sections.get("achievements", lab.sections.get("publications", ""))
            if lab_achievements:
                result = self.award_sim.calculate(student.awards, lab_achievements)
                score.award_score = result.score
            else:
                score.award_score = 0.5
        
        if student.tech_stack:
            lab_tech = lab.sections.get("technologies", lab_methods)
            if lab_tech:
                result = self.tech_sim.calculate(
                    student.tech_stack, 
                    lab_tech,
                    jaccard_weight=self.config.keyword.tech_jaccard_weight,
                    embedding_weight=self.config.keyword.tech_embedding_weight
                )
                score.tech_stack_score = result.score
            else:
                score.tech_stack_score = 0.5
        
        # 키워드형 총점
        score.keyword_score = (
            score.major_score * self.config.keyword.major_weight +
            score.certification_score * self.config.keyword.certification_weight +
            score.award_score * self.config.keyword.award_weight +
            score.tech_stack_score * self.config.keyword.tech_stack_weight
        )
        
        # 3. 정량형 유사도
        if student.toeic_score:
            # 연구실 요구 점수 (임시로 800, 실제로는 DB에서)
            required_score = "800"
            result = self.language_sim.calculate(student.toeic_score, required_score)
            score.language_score = result.score
        elif student.opic_grade:
            opic_sim = LanguageScoreSimilarity(score_type="opic")
            result = opic_sim.calculate(student.opic_grade, "IM2")
            score.language_score = result.score
        
        if student.english_proficiency:
            result = self.proficiency_sim.calculate(student.english_proficiency, "중")
            score.proficiency_score = result.score
        
        if student.gpa:
            result = self.gpa_sim.calculate(student.gpa, str(self.config.numeric.default_expected_gpa))
            score.gpa_score = result.score
        
        # 정량형 총점
        score.numeric_score = (
            score.language_score * self.config.numeric.language_score_weight +
            score.proficiency_score * self.config.numeric.proficiency_weight +
            score.gpa_score * self.config.numeric.gpa_weight
        )
        
        # 4. 최종 점수
        score.final_score = (
            score.sentence_score * self.config.sentence_weight +
            score.keyword_score * self.config.keyword_weight +
            score.numeric_score * self.config.numeric_weight
        )
        
        return score
    
    def rerank_candidates(
        self, 
        student: StudentProfile, 
        candidate_labs: List[Lab],
        top_k: int = 10
    ) -> List[RerankingScore]:
        """
        후보 연구실들을 재랭킹
        
        Args:
            student: 학생 프로필
            candidate_labs: 후보 연구실 리스트
            top_k: 상위 몇 개 반환할지
            
        Returns:
            점수 순으로 정렬된 RerankingScore 리스트
        """
        scores = []
        
        print(f"\n🔄 재랭킹 시작: {len(candidate_labs)}개 후보 연구실")
        
        for lab in candidate_labs:
            score = self.score_lab(student, lab)
            
            # 최소 임계값 필터링
            if score.final_score >= self.config.min_score_threshold:
                scores.append(score)
        
        # 점수 순으로 정렬
        scores.sort(key=lambda x: x.final_score, reverse=True)
        
        print(f"✅ 재랭킹 완료: {len(scores)}개 연구실 (임계값 {self.config.min_score_threshold} 이상)")
        
        return scores[:top_k]
    
    def save_results(self, scores: List[RerankingScore], output_path: str):
        """
        재랭킹 결과를 JSON으로 저장
        
        Args:
            scores: 점수 리스트
            output_path: 저장 경로
        """
        results = [score.to_dict() for score in scores]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 결과 저장: {output_path}")


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("재랭킹 스코어러 테스트")
    print("="*80)
    
    # 테스트용 학생 프로필
    student = StudentProfile(
        intro1="컴퓨터 비전과 딥러닝을 활용한 이미지 인식 연구에 관심이 있습니다",
        intro2="Python, PyTorch, OpenCV를 사용한 객체 탐지 프로젝트 경험이 있습니다",
        intro3="Vision Transformer 연구를 통해 차세대 이미지 인식 기술을 개발하고 싶습니다",
        portfolio="YOLO 기반 실시간 객체 탐지, GAN 이미지 생성, Transformer 비전 모델 연구 등 3년간의 프로젝트 경험",
        major="컴퓨터공학",
        certifications="정보처리기사, 빅데이터분석기사",
        awards="AI 해커톤 대회 우수상, 캡스톤 디자인 금상",
        tech_stack="Python, PyTorch, TensorFlow, OpenCV, scikit-learn",
        toeic_score="850",
        english_proficiency="중상",
        gpa="4.0"
    )
    
    # 테스트용 연구실 (실제로는 candidate_generator에서 가져옴)
    lab1 = Lab(
        lab_id="CV001",
        name="컴퓨터비전 연구실",
        professor="홍길동",
        department="컴퓨터공학",
        sections={
            "research": "딥러닝 기반 컴퓨터 비전 기술 연구. 객체 탐지, 이미지 분류, 영상 분석",
            "about": "최신 Vision Transformer 및 CNN 아키텍처 연구",
            "methods": "PyTorch, TensorFlow 기반 모델 개발",
            "projects": "YOLO 실시간 탐지, GAN 이미지 생성, Vision Transformer 연구",
        }
    )
    
    lab2 = Lab(
        lab_id="NLP001",
        name="자연어처리 연구실",
        professor="김철수",
        department="소프트웨어",
        sections={
            "research": "자연어처리 및 대화형 AI 연구",
            "about": "Transformer 기반 언어 모델 연구",
            "methods": "Hugging Face, GPT, BERT 활용",
            "projects": "챗봇 개발, 감정 분석, 기계 번역",
        }
    )
    
    # 스코어러 초기화
    print("\n1️⃣ 기본 설정 스코어러")
    scorer_default = RerankingScorer()
    
    # 단일 연구실 점수 계산
    print(f"\n2️⃣ {lab1.name} 점수 계산")
    score1 = scorer_default.score_lab(student, lab1)
    print(f"최종 점수: {score1.final_score:.4f}")
    print(f"  - 문장형: {score1.sentence_score:.4f}")
    print(f"  - 키워드형: {score1.keyword_score:.4f}")
    print(f"  - 정량형: {score1.numeric_score:.4f}")
    
    print(f"\n3️⃣ {lab2.name} 점수 계산")
    score2 = scorer_default.score_lab(student, lab2)
    print(f"최종 점수: {score2.final_score:.4f}")
    print(f"  - 문장형: {score2.sentence_score:.4f}")
    print(f"  - 키워드형: {score2.keyword_score:.4f}")
    print(f"  - 정량형: {score2.numeric_score:.4f}")
    
    # 재랭킹
    print("\n4️⃣ 재랭킹 수행")
    candidates = [lab1, lab2]
    results = scorer_default.rerank_candidates(student, candidates, top_k=2)
    
    print(f"\n📊 최종 랭킹:")
    for i, result in enumerate(results, 1):
        print(f"{i}위. {result.lab_name} - {result.final_score:.4f}점")
    
    # 결과 저장
    print("\n5️⃣ 결과 저장")
    output_path = "test_reranking_results.json"
    scorer_default.save_results(results, output_path)
    
    # 연구 중심 설정 테스트
    print("\n6️⃣ 연구 중심 설정 스코어러")
    from .config import RESEARCH_CONFIG
    scorer_research = RerankingScorer(RESEARCH_CONFIG)
    score1_research = scorer_research.score_lab(student, lab1)
    print(f"{lab1.name} 점수 (연구 중심): {score1_research.final_score:.4f}")
    print(f"  기본 설정과 비교: {score1.final_score:.4f} -> {score1_research.final_score:.4f}")
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
