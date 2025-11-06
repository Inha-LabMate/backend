"""
유사도 측정 기본 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class SimilarityResult:
    """유사도 계산 결과"""
    score: float  # 유사도 점수 (0.0 ~ 1.0)
    method: str   # 사용된 방법 (예: 'cosine', 'jaccard', 'tfidf')
    details: Dict[str, Any] = None  # 추가 정보
    
    def __post_init__(self):
        """점수 범위 검증"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")


class BaseSimilarity(ABC):
    """유사도 측정 기본 추상 클래스"""
    
    @abstractmethod
    def calculate(self, text1: str, text2: str, **kwargs) -> SimilarityResult:
        """
        두 텍스트 간 유사도 계산
        
        Args:
            text1: 첫 번째 텍스트 (학생 데이터)
            text2: 두 번째 텍스트 (연구실 데이터)
            **kwargs: 추가 파라미터
            
        Returns:
            SimilarityResult 객체
        """
        pass
    
    @staticmethod
    def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """점수를 0~1 범위로 정규화"""
        if max_val == min_val:
            return 0.0
        normalized = (score - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
