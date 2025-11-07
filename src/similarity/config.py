"""
유사도 측정 설정 및 가중치 관리
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SentenceSimilarityConfig:
    """문장형 유사도 설정"""
    # 모델 설정
    model_name: str = "intfloat/multilingual-e5-large"
    use_prefix: bool = True  # E5 모델용 query/passage prefix
    
    # 가중치
    intro1_weight: float = 0.3  # 자기소개1: 관심 연구 분야
    intro2_weight: float = 0.25  # 자기소개2: 기술 경험
    intro3_weight: float = 0.2  # 자기소개3: 연구 목표
    portfolio_weight: float = 0.25  # 포트폴리오
    
    # 자기소개2 키워드 오버랩 가중치
    keyword_overlap_weight: float = 0.3
    
    # 포트폴리오 청크 크기
    portfolio_chunk_size: int = 512


@dataclass
class KeywordSimilarityConfig:
    """키워드형 유사도 설정"""
    # 가중치
    major_weight: float = 0.35  # 전공
    certification_weight: float = 0.25  # 자격증
    award_weight: float = 0.2  # 수상경력
    tech_stack_weight: float = 0.2  # 기술 스택
    
    # 전공 유사도 점수
    exact_match_score: float = 1.0
    same_group_score: float = 0.8
    partial_match_score: float = 0.6
    related_engineering_score: float = 0.5
    
    # 자격증 가중치
    cert_weights: Dict[str, float] = field(default_factory=lambda: {
        "기사": 1.0,
        "산업기사": 0.7,
        "기능사": 0.5,
        "민간자격": 0.3,
    })
    
    # 기술 스택 하이브리드 비율
    tech_jaccard_weight: float = 0.6
    tech_embedding_weight: float = 0.4
    tech_embedding_model: str = "intfloat/e5-small-v2"


@dataclass
class NumericSimilarityConfig:
    """정량형 유사도 설정"""
    # 가중치
    language_score_weight: float = 0.3  # 어학 점수
    proficiency_weight: float = 0.3  # 구사능력
    gpa_weight: float = 0.4  # 학점
    
    # TOEIC 설정
    toeic_min: int = 0
    toeic_max: int = 990
    toeic_threshold: int = 800  # 기준 점수
    toeic_min_ratio: float = 0.7  # 최소 비율 (0.7 미만은 0점)
    
    # OPIc 등급 점수 매핑
    opic_grades: Dict[str, int] = field(default_factory=lambda: {
        "AL": 990, "IH": 900, "IM3": 850, "IM2": 800,
        "IM1": 750, "IL": 700, "NH": 650, "NM": 600, "NL": 550,
    })
    
    # 구사능력 레벨 점수
    proficiency_levels: Dict[str, float] = field(default_factory=lambda: {
        "상": 1.0, "중상": 0.85, "중": 0.7, "중하": 0.55, "하": 0.4,
        "native": 1.0, "fluent": 1.0, "advanced": 0.85,
        "intermediate": 0.7, "beginner": 0.4,
    })
    
    # 학점 설정
    gpa_min: float = 0.0
    gpa_max: float = 4.5
    default_expected_gpa: float = 3.5
    gpa_max_acceptable_gap: float = 0.5  # 최대 허용 격차


@dataclass
class ScorerConfig:
    """전체 재랭킹 스코어러 설정"""
    # 대분류 가중치 (문장형, 키워드형, 정량형)
    sentence_weight: float = 0.6
    keyword_weight: float = 0.3
    numeric_weight: float = 0.1
    
    # 세부 설정
    sentence: SentenceSimilarityConfig = field(default_factory=SentenceSimilarityConfig)
    keyword: KeywordSimilarityConfig = field(default_factory=KeywordSimilarityConfig)
    numeric: NumericSimilarityConfig = field(default_factory=NumericSimilarityConfig)
    
    # 최소 임계값 (이 이하는 제외)
    min_score_threshold: float = 0.3
    
    # 연구실 섹션별 매칭 가중치
    section_weights: Dict[str, float] = field(default_factory=lambda: {
        "research": 0.3,
        "about": 0.25,
        "methods": 0.2,
        "projects": 0.15,
        "publications": 0.1,
    })
    
    def validate(self) -> bool:
        """설정 유효성 검증"""
        # 대분류 가중치 합이 1.0인지 확인
        total_weight = self.sentence_weight + self.keyword_weight + self.numeric_weight
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Total weight must be 1.0, got {total_weight}")
        
        # 문장형 가중치 합 확인
        sentence_total = (
            self.sentence.intro1_weight +
            self.sentence.intro2_weight +
            self.sentence.intro3_weight +
            self.sentence.portfolio_weight
        )
        if not (0.99 <= sentence_total <= 1.01):
            raise ValueError(f"Sentence weights must sum to 1.0, got {sentence_total}")
        
        # 키워드형 가중치 합 확인
        keyword_total = (
            self.keyword.major_weight +
            self.keyword.certification_weight +
            self.keyword.award_weight +
            self.keyword.tech_stack_weight
        )
        if not (0.99 <= keyword_total <= 1.01):
            raise ValueError(f"Keyword weights must sum to 1.0, got {keyword_total}")
        
        # 정량형 가중치 합 확인
        numeric_total = (
            self.numeric.language_score_weight +
            self.numeric.proficiency_weight +
            self.numeric.gpa_weight
        )
        if not (0.99 <= numeric_total <= 1.01):
            raise ValueError(f"Numeric weights must sum to 1.0, got {numeric_total}")
        
        return True
    
    @classmethod
    def create_default(cls) -> "ScorerConfig":
        """기본 설정 생성"""
        return cls()
    
    @classmethod
    def create_research_focused(cls) -> "ScorerConfig":
        """연구 중심 설정 (문장형 유사도 강화)"""
        config = cls()
        config.sentence_weight = 0.5
        config.keyword_weight = 0.3
        config.numeric_weight = 0.2
        
        # 자기소개1 (연구 관심) 가중치 증가
        config.sentence.intro1_weight = 0.4
        config.sentence.intro2_weight = 0.2
        config.sentence.intro3_weight = 0.2
        config.sentence.portfolio_weight = 0.2
        
        return config
    
    @classmethod
    def create_skill_focused(cls) -> "ScorerConfig":
        """실무/기술 중심 설정 (키워드형 유사도 강화)"""
        config = cls()
        config.sentence_weight = 0.3
        config.keyword_weight = 0.45
        config.numeric_weight = 0.25
        
        # 기술 스택 가중치 증가
        config.keyword.major_weight = 0.25
        config.keyword.certification_weight = 0.25
        config.keyword.award_weight = 0.15
        config.keyword.tech_stack_weight = 0.35
        
        return config
    
    @classmethod
    def create_academic_focused(cls) -> "ScorerConfig":
        """학업 성취 중심 설정 (정량형 유사도 강화)"""
        config = cls()
        config.sentence_weight = 0.3
        config.keyword_weight = 0.3
        config.numeric_weight = 0.4
        
        # 학점 가중치 증가
        config.numeric.language_score_weight = 0.25
        config.numeric.proficiency_weight = 0.25
        config.numeric.gpa_weight = 0.5
        
        return config


# ============================================================================
# 사전 정의된 프로파일
# ============================================================================

DEFAULT_CONFIG = ScorerConfig.create_default()
RESEARCH_CONFIG = ScorerConfig.create_research_focused()
SKILL_CONFIG = ScorerConfig.create_skill_focused()
ACADEMIC_CONFIG = ScorerConfig.create_academic_focused()


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("유사도 측정 설정 테스트")
    print("="*80)
    
    # 1. 기본 설정
    print("\n1️⃣ 기본 설정 (Default)")
    default = ScorerConfig.create_default()
    print(f"대분류 가중치: 문장={default.sentence_weight}, "
          f"키워드={default.keyword_weight}, 정량={default.numeric_weight}")
    print(f"문장형 세부: intro1={default.sentence.intro1_weight}, "
          f"intro2={default.sentence.intro2_weight}, "
          f"intro3={default.sentence.intro3_weight}, "
          f"portfolio={default.sentence.portfolio_weight}")
    
    # 유효성 검증
    try:
        default.validate()
        print("✅ 설정 유효성 검증 통과")
    except ValueError as e:
        print(f"❌ 설정 오류: {e}")
    
    # 2. 연구 중심 설정
    print("\n2️⃣ 연구 중심 설정 (Research-focused)")
    research = ScorerConfig.create_research_focused()
    print(f"대분류 가중치: 문장={research.sentence_weight}, "
          f"키워드={research.keyword_weight}, 정량={research.numeric_weight}")
    print(f"문장형 세부: intro1={research.sentence.intro1_weight} (연구 관심 ↑)")
    research.validate()
    print("✅ 설정 유효성 검증 통과")
    
    # 3. 기술 중심 설정
    print("\n3️⃣ 기술 중심 설정 (Skill-focused)")
    skill = ScorerConfig.create_skill_focused()
    print(f"대분류 가중치: 문장={skill.sentence_weight}, "
          f"키워드={skill.keyword_weight}, 정량={skill.numeric_weight}")
    print(f"키워드형 세부: tech_stack={skill.keyword.tech_stack_weight} (기술 스택 ↑)")
    skill.validate()
    print("✅ 설정 유효성 검증 통과")
    
    # 4. 학업 중심 설정
    print("\n4️⃣ 학업 중심 설정 (Academic-focused)")
    academic = ScorerConfig.create_academic_focused()
    print(f"대분류 가중치: 문장={academic.sentence_weight}, "
          f"키워드={academic.keyword_weight}, 정량={academic.numeric_weight}")
    print(f"정량형 세부: gpa={academic.numeric.gpa_weight} (학점 ↑)")
    academic.validate()
    print("✅ 설정 유효성 검증 통과")
    
    # 5. 설정 커스터마이징 예시
    print("\n5️⃣ 커스텀 설정 예시")
    custom = ScorerConfig()
    custom.sentence_weight = 0.5
    custom.keyword_weight = 0.3
    custom.numeric_weight = 0.2
    custom.sentence.intro1_weight = 0.5
    custom.sentence.intro2_weight = 0.3
    custom.sentence.intro3_weight = 0.1
    custom.sentence.portfolio_weight = 0.1
    
    try:
        custom.validate()
        print("✅ 커스텀 설정 유효성 검증 통과")
    except ValueError as e:
        print(f"❌ 커스텀 설정 오류: {e}")
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
