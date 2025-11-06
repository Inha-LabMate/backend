"""
문장형 유사도 측정 (Sentence-level Similarity)

자기소개1: 관심 연구 분야 및 주제 (자유 서술문, 의미 단락)
자기소개2: 기술적 경험 및 접근 방식 (자유 서술문, 목표 서술형)
자기소개3: 연구 목표 및 성장 방향 (자유 서술문, 목표 서술형)
포트폴리오: 긴 문단이거나 문서 요약
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from .base import BaseSimilarity, SimilarityResult


class SentenceSimilarity(BaseSimilarity):
    """
    E5 / SBERT 기반 문장 임베딩 + Cosine Similarity
    """
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        """
        Args:
            model_name: 사용할 임베딩 모델
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        print(f"✅ 문장 유사도 모델 로드: {model_name}")
    
    def calculate(
        self, 
        text1: str, 
        text2: str, 
        use_prefix: bool = True,
        **kwargs
    ) -> SimilarityResult:
        """
        두 문장의 의미적 유사도 계산
        
        Args:
            text1: 학생 자기소개 (query)
            text2: 연구실 설명 (passage)
            use_prefix: E5 모델용 prefix 사용 여부
            
        Returns:
            SimilarityResult (cosine similarity)
        """
        # E5 모델은 "query:" / "passage:" prefix 필요
        if use_prefix and "e5" in self.model_name.lower():
            text1 = f"query: {text1}"
            text2 = f"passage: {text2}"
        
        # 임베딩 생성
        emb1 = self.model.encode(text1, normalize_embeddings=True)
        emb2 = self.model.encode(text2, normalize_embeddings=True)
        
        # 코사인 유사도 (정규화된 벡터이므로 내적으로 계산)
        cosine_sim = float(np.dot(emb1, emb2))
        
        return SimilarityResult(
            score=cosine_sim,
            method="cosine_similarity",
            details={
                "model": self.model_name,
                "text1_length": len(text1),
                "text2_length": len(text2)
            }
        )


class SentenceSimilarityWithKeyword(BaseSimilarity):
    """
    E5 Cosine + Keyword Overlap 보조
    (자기소개2: 기술적 경험 및 접근 방식용)
    """
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self.sentence_sim = SentenceSimilarity(model_name)
    
    def calculate(
        self, 
        text1: str, 
        text2: str,
        keyword_weight: float = 0.3,  # 키워드 오버랩 가중치
        **kwargs
    ) -> SimilarityResult:
        """
        문장 유사도 + 키워드 오버랩 결합
        
        Args:
            text1: 학생 텍스트
            text2: 연구실 텍스트
            keyword_weight: 키워드 오버랩 가중치 (0~1)
            
        Returns:
            SimilarityResult (weighted combination)
        """
        # 1. 문장 유사도
        sentence_result = self.sentence_sim.calculate(text1, text2)
        
        # 2. 키워드 오버랩
        keywords1 = set(text1.lower().split())
        keywords2 = set(text2.lower().split())
        
        if len(keywords1) == 0 or len(keywords2) == 0:
            keyword_overlap = 0.0
        else:
            intersection = len(keywords1 & keywords2)
            union = len(keywords1 | keywords2)
            keyword_overlap = intersection / union if union > 0 else 0.0
        
        # 3. 가중 평균
        final_score = (
            sentence_result.score * (1 - keyword_weight) +
            keyword_overlap * keyword_weight
        )
        
        return SimilarityResult(
            score=final_score,
            method="sentence_with_keyword",
            details={
                "sentence_score": sentence_result.score,
                "keyword_overlap": keyword_overlap,
                "keyword_weight": keyword_weight
            }
        )


class PortfolioSimilarity(BaseSimilarity):
    """
    포트폴리오 유사도: E5 + Mean-pooling Cosine
    긴 문단은 임베딩 평균 후 코사인 유사도 계산
    """
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
    
    def calculate(
        self, 
        text1: str, 
        text2: str,
        chunk_size: int = 512,  # 청크 크기 (문자 단위)
        **kwargs
    ) -> SimilarityResult:
        """
        긴 문단을 청크로 나누고 평균 임베딩으로 유사도 계산
        
        Args:
            text1: 학생 포트폴리오
            text2: 연구실 설명 (projects, publications 등)
            chunk_size: 청크 크기
            
        Returns:
            SimilarityResult (mean-pooled cosine similarity)
        """
        # 텍스트를 청크로 분할
        chunks1 = self._chunk_text(text1, chunk_size)
        chunks2 = self._chunk_text(text2, chunk_size)
        
        # 각 청크 임베딩
        emb1_list = self.model.encode(chunks1, normalize_embeddings=True)
        emb2_list = self.model.encode(chunks2, normalize_embeddings=True)
        
        # Mean-pooling
        emb1_mean = np.mean(emb1_list, axis=0)
        emb2_mean = np.mean(emb2_list, axis=0)
        
        # 정규화
        emb1_mean = emb1_mean / np.linalg.norm(emb1_mean)
        emb2_mean = emb2_mean / np.linalg.norm(emb2_mean)
        
        # 코사인 유사도
        cosine_sim = float(np.dot(emb1_mean, emb2_mean))
        
        return SimilarityResult(
            score=cosine_sim,
            method="mean_pooled_cosine",
            details={
                "chunks1_count": len(chunks1),
                "chunks2_count": len(chunks2),
                "chunk_size": chunk_size
            }
        )
    
    @staticmethod
    def _chunk_text(text: str, chunk_size: int) -> List[str]:
        """텍스트를 고정 크기로 분할"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("문장형 유사도 측정 테스트")
    print("="*80)
    
    # 1. 기본 문장 유사도
    print("\n1️⃣ 기본 문장 유사도 (E5 Cosine)")
    sentence_sim = SentenceSimilarity()
    
    student_text = "컴퓨터 비전과 딥러닝을 활용한 이미지 인식 연구에 관심이 있습니다"
    lab_text = "우리 연구실은 딥러닝 기반 컴퓨터 비전 기술을 연구하며, 특히 객체 탐지와 이미지 분류에 중점을 둡니다"
    
    result = sentence_sim.calculate(student_text, lab_text)
    print(f"유사도: {result.score:.4f}")
    print(f"방법: {result.method}")
    print(f"상세: {result.details}")
    
    # 2. 키워드 오버랩 포함
    print("\n2️⃣ 문장 + 키워드 오버랩")
    hybrid_sim = SentenceSimilarityWithKeyword()
    
    student_text2 = "Python, PyTorch, TensorFlow를 사용한 딥러닝 모델 개발 경험이 있습니다"
    lab_text2 = "PyTorch 기반 딥러닝 프레임워크를 사용하여 연구를 진행합니다"
    
    result2 = hybrid_sim.calculate(student_text2, lab_text2, keyword_weight=0.3)
    print(f"최종 유사도: {result2.score:.4f}")
    print(f"상세: {result2.details}")
    
    # 3. 포트폴리오 유사도
    print("\n3️⃣ 포트폴리오 유사도 (Mean-pooling)")
    portfolio_sim = PortfolioSimilarity()
    
    long_student = """
    저는 3년간 컴퓨터 비전 프로젝트를 수행했습니다. 
    첫 번째 프로젝트는 YOLO를 활용한 실시간 객체 탐지였고,
    두 번째는 GAN을 이용한 이미지 생성이었습니다.
    최근에는 Transformer 기반 비전 모델을 연구하고 있습니다.
    """
    
    long_lab = """
    본 연구실에서는 최신 컴퓨터 비전 기술을 연구합니다.
    주요 연구 분야는 객체 탐지, 이미지 분할, 이미지 생성입니다.
    YOLO, R-CNN, GAN 등 다양한 모델을 활용하며,
    최근에는 Vision Transformer 연구도 진행하고 있습니다.
    """
    
    result3 = portfolio_sim.calculate(long_student, long_lab, chunk_size=100)
    print(f"포트폴리오 유사도: {result3.score:.4f}")
    print(f"상세: {result3.details}")
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
