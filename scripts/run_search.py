"""
로컬 검색 실행 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.local_storage import LocalVectorStore
from core.embedding import EmbeddingPipeline

def main():
    """대화형 검색 실행"""
    print("="*80)
    print("🔍 연구실 검색 시스템 (로컬 모드)")
    print("="*80)
    
    # 데이터 로드
    print("\n데이터 로딩...")
    store = LocalVectorStore(data_dir='./data/crawl_data')
    pipeline = EmbeddingPipeline(model_name='multilingual-e5-large', device='cpu')
    print("✅ 준비 완료\n")
    
    # 대화형 검색
    while True:
        query = input("\n🔍 검색어 입력 (종료: q): ").strip()
        
        if query.lower() == 'q':
            print("\n검색 종료")
            break
        
        if not query:
            continue
        
        # 임베딩 생성
        print(f"\n'{query}' 검색 중...")
        emb_result = pipeline.embed(query)
        
        # 검색 실행
        results = store.search_vector(
            query_embedding=emb_result.embedding,
            limit=5
        )
        
        # 결과 출력
        print(f"\n📊 검색 결과 ({len(results)}개):")
        print("="*80)
        
        for i, result in enumerate(results):
            print(f"\n[{i+1}] {result.lab_name}")
            print(f"    섹션: {result.section}")
            print(f"    점수: {result.score:.3f}")
            print(f"    내용: {result.text[:150]}...")
            print(f"    URL: {result.source_url}")

if __name__ == "__main__":
    main()
