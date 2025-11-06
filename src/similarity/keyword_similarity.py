"""
키워드형 유사도 측정 (Label-level Similarity)

전공/복수전공: 단일 라벨, 분류 기반 Rule Similarity
자격증: 리스트(텍스트), Weighted Jaccard
수상경력: 텍스트(수상명 + 내용), TF-IDF Cosine / Jaccard
기술 스택: 리스트(키워드), Jaccard + Embedding 보조
"""

from typing import List, Set, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from .base import BaseSimilarity, SimilarityResult


class MajorSimilarity(BaseSimilarity):
    """
    전공/복수전공 유사도
    Rule-based Similarity: 동일 학과=1.0, 유사 계열=0.8, 비관련=0.5, 무관=0.0
    """
    
    # 학과 계열 정의
    MAJOR_GROUPS = {
        "컴퓨터": ["컴퓨터공학", "소프트웨어", "인공지능", "데이터사이언스"],
        "전기전자": ["전기공학", "전자공학", "전기전자공학", "제어계측"],
        "기계": ["기계공학", "기계설계", "자동차공학", "항공우주"],
        "화학생명": ["화학공학", "생명공학", "환경공학", "신소재"],
        "경영경제": ["경영학", "경제학", "회계학", "금융학"],
    }
    
    def __init__(self):
        # 역방향 매핑 생성 (학과명 -> 계열)
        self.major_to_group = {}
        for group, majors in self.MAJOR_GROUPS.items():
            for major in majors:
                self.major_to_group[major] = group
    
    def calculate(self, text1: str, text2: str, **kwargs) -> SimilarityResult:
        """
        전공 유사도 계산
        
        Args:
            text1: 학생 전공
            text2: 연구실 관련 학과
            
        Returns:
            SimilarityResult (rule-based score)
        """
        major1 = text1.strip()
        major2 = text2.strip()
        
        # 1. 완전 일치
        if major1 == major2:
            return SimilarityResult(
                score=1.0,
                method="exact_match",
                details={"major1": major1, "major2": major2}
            )
        
        # 2. 같은 계열
        group1 = self.major_to_group.get(major1)
        group2 = self.major_to_group.get(major2)
        
        if group1 and group2 and group1 == group2:
            return SimilarityResult(
                score=0.8,
                method="same_group",
                details={"group": group1, "major1": major1, "major2": major2}
            )
        
        # 3. 부분 문자열 매칭 (예: "컴퓨터" in "컴퓨터공학")
        if major1 in major2 or major2 in major1:
            return SimilarityResult(
                score=0.6,
                method="partial_match",
                details={"major1": major1, "major2": major2}
            )
        
        # 4. 관련 있는 계열인지 확인
        if group1 and group2:
            # 공학 계열끼리는 0.5
            engineering_groups = {"컴퓨터", "전기전자", "기계", "화학생명"}
            if group1 in engineering_groups and group2 in engineering_groups:
                return SimilarityResult(
                    score=0.5,
                    method="related_engineering",
                    details={"group1": group1, "group2": group2}
                )
        
        # 5. 무관
        return SimilarityResult(
            score=0.0,
            method="no_match",
            details={"major1": major1, "major2": major2}
        )


class CertificationSimilarity(BaseSimilarity):
    """
    자격증 유사도
    Weighted Jaccard: 기사 > 산업기사 > 민간자격 순 가중치
    """
    
    # 자격증 가중치
    CERT_WEIGHTS = {
        "기사": 1.0,
        "산업기사": 0.7,
        "기능사": 0.5,
        "민간자격": 0.3,
    }
    
    def calculate(
        self, 
        text1: str,  # 실제로는 List[str]을 문자열로 받음
        text2: str, 
        **kwargs
    ) -> SimilarityResult:
        """
        자격증 리스트 유사도 계산
        
        Args:
            text1: 학생 자격증 리스트 (콤마 구분 문자열)
            text2: 연구실 요구/선호 자격증 리스트
            
        Returns:
            SimilarityResult (weighted jaccard)
        """
        certs1 = [c.strip() for c in text1.split(',') if c.strip()]
        certs2 = [c.strip() for c in text2.split(',') if c.strip()]
        
        if not certs1 or not certs2:
            return SimilarityResult(score=0.0, method="empty_lists")
        
        # 자격증별 가중치 부여
        weighted_scores = []
        
        for cert1 in certs1:
            best_match_score = 0.0
            for cert2 in certs2:
                # 문자열 유사도
                if cert1 == cert2:
                    match_score = 1.0
                elif cert1 in cert2 or cert2 in cert1:
                    match_score = 0.7
                else:
                    # 키워드 기반 유사도
                    words1 = set(cert1.split())
                    words2 = set(cert2.split())
                    if words1 & words2:
                        match_score = len(words1 & words2) / len(words1 | words2)
                    else:
                        match_score = 0.0
                
                # 자격증 등급별 가중치 적용
                weight = self._get_cert_weight(cert1)
                weighted_match = match_score * weight
                
                best_match_score = max(best_match_score, weighted_match)
            
            weighted_scores.append(best_match_score)
        
        # 최종 점수: 평균
        final_score = np.mean(weighted_scores) if weighted_scores else 0.0
        
        return SimilarityResult(
            score=final_score,
            method="weighted_jaccard",
            details={
                "certs1": certs1,
                "certs2": certs2,
                "individual_scores": weighted_scores
            }
        )
    
    def _get_cert_weight(self, cert: str) -> float:
        """자격증 이름에서 가중치 추출"""
        for key, weight in self.CERT_WEIGHTS.items():
            if key in cert:
                return weight
        return 0.3  # 기본값: 민간자격


class AwardSimilarity(BaseSimilarity):
    """
    수상경력 유사도
    TF-IDF Cosine (긴 텍스트) / Jaccard (짧은 키워드)
    """
    
    def __init__(self):
        self.tfidf = TfidfVectorizer()
    
    def calculate(
        self, 
        text1: str, 
        text2: str,
        use_tfidf_threshold: int = 20,  # 20자 이상이면 TF-IDF 사용
        **kwargs
    ) -> SimilarityResult:
        """
        수상경력 유사도 계산
        
        Args:
            text1: 학생 수상경력 (콤마 구분 리스트 또는 긴 텍스트)
            text2: 연구실 관련 수상/성과
            use_tfidf_threshold: TF-IDF 사용 기준 길이
            
        Returns:
            SimilarityResult
        """
        # 텍스트 길이에 따라 방법 선택
        avg_length = (len(text1) + len(text2)) / 2
        
        if avg_length > use_tfidf_threshold:
            # 긴 텍스트: TF-IDF Cosine
            return self._tfidf_similarity(text1, text2)
        else:
            # 짧은 키워드: Jaccard
            return self._jaccard_similarity(text1, text2)
    
    def _tfidf_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """TF-IDF 기반 코사인 유사도"""
        try:
            tfidf_matrix = self.tfidf.fit_transform([text1, text2])
            cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return SimilarityResult(
                score=float(cosine_sim),
                method="tfidf_cosine",
                details={
                    "text1_length": len(text1),
                    "text2_length": len(text2)
                }
            )
        except:
            # TF-IDF 실패 시 Jaccard로 fallback
            return self._jaccard_similarity(text1, text2)
    
    def _jaccard_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """Jaccard 유사도"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return SimilarityResult(score=0.0, method="jaccard_empty")
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        jaccard = intersection / union if union > 0 else 0.0
        
        return SimilarityResult(
            score=jaccard,
            method="jaccard",
            details={
                "intersection": intersection,
                "union": union,
                "words1": list(words1)[:5],  # 샘플만
                "words2": list(words2)[:5]
            }
        )


class TechStackSimilarity(BaseSimilarity):
    """
    기술 스택 유사도
    Jaccard + Embedding 보조
    """
    
    def __init__(self, model_name: str = "intfloat/e5-small-v2"):
        self.model = SentenceTransformer(model_name)
    
    def calculate(
        self, 
        text1: str, 
        text2: str,
        jaccard_weight: float = 0.6,  # Jaccard 가중치
        embedding_weight: float = 0.4,  # 임베딩 가중치
        **kwargs
    ) -> SimilarityResult:
        """
        기술 스택 유사도 계산
        
        Args:
            text1: 학생 기술 스택 (콤마 구분)
            text2: 연구실 기술 스택
            jaccard_weight: Jaccard 가중치
            embedding_weight: 임베딩 가중치
            
        Returns:
            SimilarityResult (hybrid)
        """
        techs1 = [t.strip().lower() for t in text1.split(',') if t.strip()]
        techs2 = [t.strip().lower() for t in text2.split(',') if t.strip()]
        
        if not techs1 or not techs2:
            return SimilarityResult(score=0.0, method="empty_stacks")
        
        # 1. Jaccard 유사도
        set1 = set(techs1)
        set2 = set(techs2)
        jaccard = len(set1 & set2) / len(set1 | set2)
        
        # 2. 임베딩 유사도 (각 기술 단어의 평균 임베딩)
        emb1 = self.model.encode(techs1, normalize_embeddings=True)
        emb2 = self.model.encode(techs2, normalize_embeddings=True)
        
        mean_emb1 = np.mean(emb1, axis=0)
        mean_emb2 = np.mean(emb2, axis=0)
        
        # 정규화
        mean_emb1 = mean_emb1 / np.linalg.norm(mean_emb1)
        mean_emb2 = mean_emb2 / np.linalg.norm(mean_emb2)
        
        embedding_sim = float(np.dot(mean_emb1, mean_emb2))
        
        # 3. 가중 평균
        final_score = (
            jaccard * jaccard_weight +
            embedding_sim * embedding_weight
        )
        
        return SimilarityResult(
            score=final_score,
            method="jaccard_embedding_hybrid",
            details={
                "jaccard": jaccard,
                "embedding_sim": embedding_sim,
                "intersection": list(set1 & set2),
                "tech_count1": len(techs1),
                "tech_count2": len(techs2)
            }
        )


# ============================================================================
# 테스트 코드
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("키워드형 유사도 측정 테스트")
    print("="*80)
    
    # 1. 전공 유사도
    print("\n1️⃣ 전공 유사도")
    major_sim = MajorSimilarity()
    
    test_cases = [
        ("컴퓨터공학", "컴퓨터공학"),  # 동일
        ("컴퓨터공학", "소프트웨어"),  # 같은 계열
        ("컴퓨터공학", "전기공학"),    # 관련 공학
        ("컴퓨터공학", "경영학"),      # 무관
    ]
    
    for major1, major2 in test_cases:
        result = major_sim.calculate(major1, major2)
        print(f"  {major1} vs {major2}: {result.score:.2f} ({result.method})")
    
    # 2. 자격증 유사도
    print("\n2️⃣ 자격증 유사도")
    cert_sim = CertificationSimilarity()
    
    student_certs = "정보처리기사, 빅데이터분석기사"
    lab_certs = "정보처리기사, AI자격증"
    
    result = cert_sim.calculate(student_certs, lab_certs)
    print(f"  유사도: {result.score:.4f}")
    print(f"  상세: {result.details}")
    
    # 3. 수상경력 유사도
    print("\n3️⃣ 수상경력 유사도")
    award_sim = AwardSimilarity()
    
    student_award = "AI 해커톤 대회 우수상, 캡스톤 디자인 금상"
    lab_award = "AI Competition Award, Best Paper Award"
    
    result = award_sim.calculate(student_award, lab_award)
    print(f"  유사도: {result.score:.4f} ({result.method})")
    
    # 4. 기술 스택 유사도
    print("\n4️⃣ 기술 스택 유사도")
    tech_sim = TechStackSimilarity()
    
    student_tech = "Python, PyTorch, TensorFlow, OpenCV"
    lab_tech = "Python, PyTorch, Keras, scikit-learn"
    
    result = tech_sim.calculate(student_tech, lab_tech)
    print(f"  최종 유사도: {result.score:.4f}")
    print(f"  Jaccard: {result.details['jaccard']:.4f}")
    print(f"  Embedding: {result.details['embedding_sim']:.4f}")
    print(f"  교집합: {result.details['intersection']}")
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
