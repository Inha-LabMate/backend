"""
검색 테스트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.local_storage import LocalVectorStore
from core.embedding import EmbeddingPipeline

def test_search():
    """기본 검색 테스트"""
    # 데이터 로드
    store = LocalVectorStore(data_dir='./data/crawl_data')
    pipeline = EmbeddingPipeline(model_name='multilingual-e5-large', device='cpu')
    
    # 검색어
    query = "컴퓨터 비전"
    emb_result = pipeline.embed(query)
    
    # 검색
    results = store.search_vector(
        query_embedding=emb_result.embedding,
        limit=5
    )
    
    assert len(results) > 0, "검색 결과가 없습니다"
    assert all(r.score >= 0 for r in results), "유사도 점수는 0 이상이어야 함"
    
    print(f"✅ 검색 테스트 통과 ('{query}' 검색 결과: {len(results)}개)")
    
    # 결과 출력
    for i, result in enumerate(results[:3]):
        print(f"  [{i+1}] {result.lab_name} - 점수: {result.score:.3f}")

if __name__ == "__main__":
    print("="*80)
    print("검색 테스트 시작")
    print("="*80)
    
    test_search()
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
