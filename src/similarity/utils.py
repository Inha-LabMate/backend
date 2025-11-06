"""
유사도 측정 공통 유틸리티 함수
"""

from typing import List, Dict, Any
import numpy as np


def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    점수를 지정 범위로 정규화
    
    Args:
        score: 원본 점수
        min_val: 최소값
        max_val: 최대값
        
    Returns:
        정규화된 점수 (0~1)
    """
    if max_val == min_val:
        return 0.0
    normalized = (score - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def weighted_average(scores: List[float], weights: List[float]) -> float:
    """
    가중 평균 계산
    
    Args:
        scores: 점수 리스트
        weights: 가중치 리스트
        
    Returns:
        가중 평균
    """
    if len(scores) != len(weights):
        raise ValueError("Scores and weights must have the same length")
    
    if sum(weights) == 0:
        return 0.0
    
    return sum(s * w for s, w in zip(scores, weights)) / sum(weights)


def jaccard_similarity(set1: set, set2: set) -> float:
    """
    Jaccard 유사도 계산
    
    Args:
        set1: 첫 번째 집합
        set2: 두 번째 집합
        
    Returns:
        Jaccard 유사도 (0~1)
    """
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def cosine_similarity_vectors(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    벡터 간 코사인 유사도
    
    Args:
        vec1: 첫 번째 벡터
        vec2: 두 번째 벡터
        
    Returns:
        코사인 유사도 (0~1, 정규화된 경우)
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def text_to_tokens(text: str, lowercase: bool = True) -> List[str]:
    """
    텍스트를 토큰으로 분할
    
    Args:
        text: 입력 텍스트
        lowercase: 소문자 변환 여부
        
    Returns:
        토큰 리스트
    """
    if lowercase:
        text = text.lower()
    
    # 간단한 공백 기반 토큰화
    tokens = text.split()
    
    # 특수문자 제거 (선택)
    import re
    tokens = [re.sub(r'[^\w\s]', '', token) for token in tokens]
    tokens = [t for t in tokens if t]  # 빈 문자열 제거
    
    return tokens


def min_max_normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Min-Max 정규화
    
    Args:
        value: 정규화할 값
        min_val: 최소값
        max_val: 최대값
        
    Returns:
        정규화된 값 (0~1)
    """
    if max_val == min_val:
        return 0.0
    
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def combine_similarities(
    similarities: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """
    여러 유사도를 가중 결합
    
    Args:
        similarities: {이름: 유사도} 딕셔너리
        weights: {이름: 가중치} 딕셔너리
        
    Returns:
        결합된 최종 유사도
    """
    total_weight = 0.0
    weighted_sum = 0.0
    
    for name, similarity in similarities.items():
        weight = weights.get(name, 0.0)
        weighted_sum += similarity * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return weighted_sum / total_weight


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("유틸리티 함수 테스트\n")
    
    # 1. 정규화
    print("1. normalize_score(0.5, 0, 1):", normalize_score(0.5, 0, 1))
    print("   normalize_score(75, 0, 100):", normalize_score(75, 0, 100))
    
    # 2. 가중 평균
    scores = [0.8, 0.6, 0.9]
    weights = [0.5, 0.3, 0.2]
    print(f"\n2. weighted_average({scores}, {weights}):", weighted_average(scores, weights))
    
    # 3. Jaccard
    set1 = {"python", "pytorch", "tensorflow"}
    set2 = {"python", "pytorch", "keras"}
    print(f"\n3. jaccard_similarity({set1}, {set2}):", jaccard_similarity(set1, set2))
    
    # 4. 코사인 유사도
    vec1 = np.array([1, 2, 3])
    vec2 = np.array([2, 3, 4])
    print(f"\n4. cosine_similarity_vectors([1,2,3], [2,3,4]):", 
          cosine_similarity_vectors(vec1, vec2))
    
    # 5. 토큰화
    text = "Hello, World! This is a test."
    print(f"\n5. text_to_tokens('{text}'):", text_to_tokens(text))
    
    # 6. 유사도 결합
    sims = {"sentence": 0.8, "keyword": 0.6, "numeric": 0.9}
    weights_dict = {"sentence": 0.5, "keyword": 0.3, "numeric": 0.2}
    print(f"\n6. combine_similarities(...):", combine_similarities(sims, weights_dict))
    
    print("\n✅ 테스트 완료!")
