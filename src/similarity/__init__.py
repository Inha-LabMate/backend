"""
Similarity 모듈
재랭킹을 위한 다양한 유사도 측정 알고리즘
"""

from .base import BaseSimilarity, SimilarityResult
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
from .candidate_generator import CandidateGenerator, Lab, Student
from .config import (
    ScorerConfig,
    SentenceSimilarityConfig,
    KeywordSimilarityConfig,
    NumericSimilarityConfig,
    DEFAULT_CONFIG,
    RESEARCH_CONFIG,
    SKILL_CONFIG,
    ACADEMIC_CONFIG
)
from .scorer import RerankingScorer, StudentProfile, RerankingScore

__all__ = [
    # Base
    'BaseSimilarity',
    'SimilarityResult',
    
    # Sentence-level
    'SentenceSimilarity',
    'SentenceSimilarityWithKeyword',
    'PortfolioSimilarity',
    
    # Keyword-level
    'MajorSimilarity',
    'CertificationSimilarity',
    'AwardSimilarity',
    'TechStackSimilarity',
    
    # Numeric-level
    'LanguageScoreSimilarity',
    'LanguageProficiencySimilarity',
    'GPASimilarity',
    
    # Candidate Generation
    'CandidateGenerator',
    'Lab',
    'Student',
    
    # Config
    'ScorerConfig',
    'SentenceSimilarityConfig',
    'KeywordSimilarityConfig',
    'NumericSimilarityConfig',
    'DEFAULT_CONFIG',
    'RESEARCH_CONFIG',
    'SKILL_CONFIG',
    'ACADEMIC_CONFIG',
    
    # Scorer
    'RerankingScorer',
    'StudentProfile',
    'RerankingScore',
]
