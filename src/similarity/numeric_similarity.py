"""
정량형 유사도 측정 (Numeric-level Similarity)

어학점수 (TOEIC/OPIc): 수치형, Min-Max 정규화 + Threshold Rule
구사능력 (상/중/하): 범주형, Rule-based Ordinal Similarity
학점 (0~4.5): 연속형, Min-Max 정규화 기반 거리 유사도
"""

from typing import Union, Optional
import numpy as np

from .base import BaseSimilarity, SimilarityResult


class LanguageScoreSimilarity(BaseSimilarity):
    """
    어학 점수 유사도 (TOEIC, OPIc 등)
    Min-Max 정규화 + Threshold Rule
    기준 점수 이상 -> 1.0, 이하 -> 선형 감소
    """
    
    # TOEIC 기준
    TOEIC_MIN = 0
    TOEIC_MAX = 990
    TOEIC_THRESHOLD = 800  # 기준 점수
    
    # OPIc 등급 -> 점수 변환
    OPIC_GRADES = {
        "AL": 990,
        "IH": 900,
        "IM3": 850,
        "IM2": 800,
        "IM1": 750,
        "IL": 700,
        "NH": 650,
        "NM": 600,
        "NL": 550,
    }
    
    def __init__(
        self, 
        score_type: str = "toeic",  # "toeic" or "opic"
        threshold: Optional[int] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None
    ):
        """
        Args:
            score_type: 점수 타입 ("toeic", "opic")
            threshold: 기준 점수 (None이면 기본값 사용)
            min_score: 최소 점수
            max_score: 최대 점수
        """
        self.score_type = score_type.lower()
        
        if score_type == "toeic":
            self.min_score = min_score or self.TOEIC_MIN
            self.max_score = max_score or self.TOEIC_MAX
            self.threshold = threshold or self.TOEIC_THRESHOLD
        else:
            self.min_score = min_score or 0
            self.max_score = max_score or 990
            self.threshold = threshold or 800
    
    def calculate(
        self, 
        text1: str,  # 학생 점수 (문자열 또는 숫자)
        text2: str,  # 연구실 요구 점수
        **kwargs
    ) -> SimilarityResult:
        """
        어학 점수 유사도 계산
        
        Args:
            text1: 학생 점수 (예: "850", "IM3")
            text2: 연구실 요구 점수 (예: "800")
            
        Returns:
            SimilarityResult (normalized score)
        """
        # 점수 변환
        score1 = self._parse_score(text1)
        score2 = self._parse_score(text2)
        
        if score1 is None or score2 is None:
            return SimilarityResult(score=0.0, method="invalid_score")
        
        # 학생 점수가 요구 점수 이상이면 1.0
        if score1 >= score2:
            return SimilarityResult(
                score=1.0,
                method="above_requirement",
                details={
                    "student_score": score1,
                    "required_score": score2,
                    "score_type": self.score_type
                }
            )
        
        # 요구 점수 미달: 선형 감소
        # threshold 이하는 점수 비율로 계산
        if score2 > 0:
            ratio = score1 / score2
        else:
            ratio = 0.0
        
        # 0.7 미만이면 0으로 (너무 낮은 점수는 제외)
        if ratio < 0.7:
            final_score = 0.0
        else:
            # 0.7~1.0 구간을 0~1로 선형 매핑
            final_score = (ratio - 0.7) / 0.3
        
        return SimilarityResult(
            score=final_score,
            method="linear_decay",
            details={
                "student_score": score1,
                "required_score": score2,
                "ratio": ratio,
                "score_type": self.score_type
            }
        )
    
    def _parse_score(self, score_str: str) -> Optional[int]:
        """점수 문자열을 숫자로 변환"""
        score_str = str(score_str).strip()
        
        # 숫자인 경우
        try:
            return int(score_str)
        except ValueError:
            pass
        
        # OPIc 등급인 경우
        score_upper = score_str.upper()
        if score_upper in self.OPIC_GRADES:
            return self.OPIC_GRADES[score_upper]
        
        return None


class LanguageProficiencySimilarity(BaseSimilarity):
    """
    언어 구사능력 유사도 (상/중/하)
    Rule-based Ordinal Similarity
    """
    
    # 구사능력 레벨
    PROFICIENCY_LEVELS = {
        "상": 1.0,
        "중상": 0.85,
        "중": 0.7,
        "중하": 0.55,
        "하": 0.4,
        "native": 1.0,
        "fluent": 1.0,
        "advanced": 0.85,
        "intermediate": 0.7,
        "beginner": 0.4,
    }
    
    def calculate(
        self, 
        text1: str,  # 학생 구사능력
        text2: str,  # 연구실 요구 수준
        **kwargs
    ) -> SimilarityResult:
        """
        언어 구사능력 유사도 계산
        
        Args:
            text1: 학생 구사능력 ("상", "중", "하" 또는 영문)
            text2: 연구실 요구 수준
            
        Returns:
            SimilarityResult (ordinal similarity)
        """
        level1 = self._get_level_score(text1)
        level2 = self._get_level_score(text2)
        
        if level1 is None or level2 is None:
            return SimilarityResult(score=0.0, method="unknown_level")
        
        # 학생 레벨이 요구 레벨 이상이면 1.0
        if level1 >= level2:
            return SimilarityResult(
                score=1.0,
                method="meets_requirement",
                details={
                    "student_level": text1,
                    "required_level": text2,
                    "student_score": level1,
                    "required_score": level2
                }
            )
        
        # 미달: 레벨 차이에 따라 점수 부여
        gap = level2 - level1
        
        # 1단계 차이: 0.7
        # 2단계 차이: 0.4
        # 3단계 이상: 0.0
        if gap <= 0.15:  # 거의 비슷
            similarity = 0.9
        elif gap <= 0.3:  # 1단계 차이
            similarity = 0.7
        elif gap <= 0.45:  # 2단계 차이
            similarity = 0.4
        else:  # 3단계 이상
            similarity = 0.0
        
        return SimilarityResult(
            score=similarity,
            method="ordinal_similarity",
            details={
                "student_level": text1,
                "required_level": text2,
                "gap": gap
            }
        )
    
    def _get_level_score(self, level_str: str) -> Optional[float]:
        """구사능력 레벨을 점수로 변환"""
        level_str = str(level_str).strip().lower()
        
        for key, score in self.PROFICIENCY_LEVELS.items():
            if key.lower() in level_str or level_str in key.lower():
                return score
        
        return None


class GPASimilarity(BaseSimilarity):
    """
    학점 유사도 (0~4.5)
    Min-Max 정규화 기반 거리 유사도
    """
    
    GPA_MIN = 0.0
    GPA_MAX = 4.5
    
    def __init__(self, expected_gpa: float = 3.5):
        """
        Args:
            expected_gpa: 연구실 기대 학점 (기본값 3.5)
        """
        self.expected_gpa = expected_gpa
    
    def calculate(
        self, 
        text1: str,  # 학생 학점
        text2: str,  # 연구실 기대 학점
        **kwargs
    ) -> SimilarityResult:
        """
        학점 유사도 계산
        
        Args:
            text1: 학생 학점 (예: "4.2", "3.8")
            text2: 연구실 기대 학점 (예: "3.5")
            
        Returns:
            SimilarityResult (distance-based similarity)
        """
        try:
            gpa1 = float(text1)
            gpa2 = float(text2) if text2 else self.expected_gpa
        except (ValueError, TypeError):
            return SimilarityResult(score=0.0, method="invalid_gpa")
        
        # 범위 검증
        if not (self.GPA_MIN <= gpa1 <= self.GPA_MAX):
            return SimilarityResult(score=0.0, method="gpa_out_of_range")
        
        # 학생 학점이 기대치 이상이면 1.0
        if gpa1 >= gpa2:
            return SimilarityResult(
                score=1.0,
                method="above_expectation",
                details={
                    "student_gpa": gpa1,
                    "expected_gpa": gpa2
                }
            )
        
        # 기대치 미달: 거리 기반 유사도
        gap = gpa2 - gpa1
        
        # 0.5 차이까지는 선형 감소 (예: 3.5 기대, 3.0 실제 -> 0.5 gap -> 점수 0.0)
        # 0.3 차이: 0.6 점수
        # 0.1 차이: 0.9 점수
        max_acceptable_gap = 0.5
        
        if gap > max_acceptable_gap:
            similarity = 0.0
        else:
            # 선형 감소
            similarity = 1.0 - (gap / max_acceptable_gap)
        
        return SimilarityResult(
            score=similarity,
            method="distance_based",
            details={
                "student_gpa": gpa1,
                "expected_gpa": gpa2,
                "gap": gap
            }
        )


# ============================================================================
# 테스트 코드
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("정량형 유사도 측정 테스트")
    print("="*80)
    
    # 1. TOEIC 점수 유사도
    print("\n1️⃣ TOEIC 점수 유사도")
    toeic_sim = LanguageScoreSimilarity(score_type="toeic")
    
    test_cases = [
        ("850", "800"),  # 기준 이상
        ("780", "800"),  # 약간 미달
        ("650", "800"),  # 많이 미달
    ]
    
    for score1, score2 in test_cases:
        result = toeic_sim.calculate(score1, score2)
        print(f"  학생: {score1}, 요구: {score2} -> 유사도: {result.score:.3f} ({result.method})")
    
    # 2. OPIc 등급 유사도
    print("\n2️⃣ OPIc 등급 유사도")
    opic_sim = LanguageScoreSimilarity(score_type="opic")
    
    result = opic_sim.calculate("IM3", "IM2")
    print(f"  학생: IM3, 요구: IM2 -> 유사도: {result.score:.3f}")
    print(f"  상세: {result.details}")
    
    # 3. 언어 구사능력 유사도
    print("\n3️⃣ 언어 구사능력 유사도")
    proficiency_sim = LanguageProficiencySimilarity()
    
    test_cases = [
        ("상", "중"),
        ("중", "상"),
        ("하", "상"),
        ("fluent", "intermediate"),
    ]
    
    for level1, level2 in test_cases:
        result = proficiency_sim.calculate(level1, level2)
        print(f"  학생: {level1}, 요구: {level2} -> 유사도: {result.score:.3f}")
    
    # 4. 학점 유사도
    print("\n4️⃣ 학점 유사도 (4.5 만점)")
    gpa_sim = GPASimilarity(expected_gpa=3.5)
    
    test_cases = [
        ("4.2", "3.5"),  # 기대 이상
        ("3.5", "3.5"),  # 정확히 일치
        ("3.3", "3.5"),  # 약간 미달
        ("3.0", "3.5"),  # 많이 미달
        ("2.8", "3.5"),  # 크게 미달
    ]
    
    for gpa1, gpa2 in test_cases:
        result = gpa_sim.calculate(gpa1, gpa2)
        print(f"  학생: {gpa1}, 기대: {gpa2} -> 유사도: {result.score:.3f} ({result.method})")
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
