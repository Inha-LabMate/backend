"""
임베딩 테스트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.embedding import EmbeddingPipeline
import numpy as np

def test_embedding_basic():
    """기본 임베딩 테스트"""
    pipeline = EmbeddingPipeline(model_name='multilingual-e5-large', device='cpu')
    
    # 단일 텍스트
    text = "인공지능 연구"
    result = pipeline.embed(text)
    
    assert result.embedding.shape == (1024,), f"Expected shape (1024,), got {result.embedding.shape}"
    assert result.model_name == 'multilingual-e5-large'
    assert result.normalized == True
    
    print("✅ 기본 임베딩 테스트 통과")

def test_embedding_batch():
    """배치 임베딩 테스트"""
    pipeline = EmbeddingPipeline(model_name='multilingual-e5-large', device='cpu')
    
    # 배치 텍스트
    texts = ["컴퓨터 비전", "자연어 처리", "강화학습"]
    results = pipeline.embed_batch(texts)
    
    assert len(results) == 3
    assert all(r.embedding.shape == (1024,) for r in results)
    
    print("✅ 배치 임베딩 테스트 통과")

def test_embedding_similarity():
    """유사도 테스트"""
    pipeline = EmbeddingPipeline(model_name='multilingual-e5-large', device='cpu')
    
    # 유사한 텍스트
    emb1 = pipeline.embed("인공지능").embedding
    emb2 = pipeline.embed("AI").embedding
    emb3 = pipeline.embed("요리").embedding
    
    # 코사인 유사도
    sim_12 = np.dot(emb1, emb2)
    sim_13 = np.dot(emb1, emb3)
    
    assert sim_12 > sim_13, "유사한 텍스트의 유사도가 더 높아야 함"
    
    print(f"✅ 유사도 테스트 통과 (AI vs 인공지능: {sim_12:.3f}, AI vs 요리: {sim_13:.3f})")

if __name__ == "__main__":
    print("="*80)
    print("임베딩 테스트 시작")
    print("="*80)
    
    test_embedding_basic()
    test_embedding_batch()
    test_embedding_similarity()
    
    print("\n" + "="*80)
    print("✅ 모든 테스트 통과!")
    print("="*80)
