"""
로컬 저장소 검색 테스트 스크립트
================================

PostgreSQL 없이 JSON 파일에서 벡터 검색을 수행합니다.

3가지 모드:
    1. interactive (대화형) - 계속 검색어를 입력하며 테스트
    2. search (단일 검색) - 한 번만 검색하고 종료
    3. stats (통계) - 저장된 데이터 통계 확인

사용 예:
    # 대화형 모드 (추천)
    python search_local.py
    
    # 단일 검색
    python search_local.py --mode search --query "컴퓨터 비전"
    
    # 통계 보기
    python search_local.py --mode stats

동작 원리:
    1. crawl_data/ 폴더에서 JSON 파일 로드
    2. 검색어를 768차원 벡터로 변환
    3. 모든 문서와 코사인 유사도 계산
    4. 유사도 높은 순으로 정렬하여 표시
"""

from storage.local_storage import LocalVectorStore
from core.embedding import EmbeddingPipeline
import sys


def search_local(query: str, limit: int = 5, data_dir: str = './crawl_data'):
    """
    로컬 저장소 검색 함수
    
    Args:
        query: 검색어 (예: "컴퓨터 비전과 딥러닝")
        limit: 최대 결과 개수 (기본 5개)
        data_dir: 데이터 디렉토리 경로 (기본 './crawl_data')
    
    동작 과정:
        1. JSON 파일에서 저장된 데이터 로드
        2. 임베딩 모델 로드 (1.1GB, 첫 실행시만)
        3. 검색어를 768차원 벡터로 변환
        4. 모든 문서와 유사도 계산
        5. 상위 N개 결과 출력
    
    예시:
        search_local("인공지능 연구", limit=10)
        # → AI 관련 문서 10개 출력
    """
    
    print("="*80)
    print(f"로컬 벡터 검색: '{query}'")
    print("="*80)
    
    # 1. 저장소 로드
    print("\n1. 로컬 저장소 로딩...")
    store = LocalVectorStore(data_dir=data_dir)
    
    stats = store.get_stats()
    print(f"   - 총 연구실: {stats['total_labs']}")
    print(f"   - 총 문서: {stats['total_docs']}")
    
    # 2. 임베딩 파이프라인
    print("\n2. 임베딩 모델 로딩...")
    pipeline = EmbeddingPipeline(model_name='multilingual-mpnet', device='cpu')
    
    # 3. 쿼리 임베딩
    print(f"\n3. 쿼리 임베딩 생성: '{query}'")
    query_emb = pipeline.embed(query)
    
    # 4. 검색
    print(f"\n4. 벡터 검색 수행 (상위 {limit}개)...")
    results = store.search_vector(
        query_embedding=query_emb.embedding,
        limit=limit,
        min_quality=0
    )
    
    # 5. 결과 출력
    print("\n" + "="*80)
    print("검색 결과")
    print("="*80)
    
    if not results:
        print("❌ 검색 결과 없음")
        return
    
    for i, result in enumerate(results):
        print(f"\n{'='*80}")
        print(f"{i+1}. [{result.lab_name}] {result.section}")
        print(f"{'='*80}")
        print(f"제목: {result.title or '없음'}")
        print(f"유사도 점수: {result.score:.4f}")  # 0~1 사이 값 (1에 가까울수록 유사)
        print(f"텍스트 미리보기:")
        print(f"  {result.text[:200]}...")
    
    print("\n" + "="*80)
    print(f"✅ 총 {len(results)}개 결과")
    print("="*80)


def interactive_search(data_dir: str = './crawl_data'):
    """대화형 검색"""
    print("="*80)
    print("로컬 벡터 검색 - 대화형 모드")
    print("="*80)
    print("종료하려면 'exit' 또는 'quit'를 입력하세요\n")
    
    # 저장소 & 파이프라인 초기화
    store = LocalVectorStore(data_dir=data_dir)
    pipeline = EmbeddingPipeline(model_name='multilingual-mpnet', device='cpu')
    
    stats = store.get_stats()
    print(f"📊 저장소 정보: 연구실 {stats['total_labs']}개, 문서 {stats['total_docs']}개\n")
    
    while True:
        try:
            query = input("🔍 검색어를 입력하세요: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("👋 검색 종료")
                break
            
            if not query:
                continue
            
            # 검색
            query_emb = pipeline.embed(query)
            results = store.search_vector(query_emb.embedding, limit=5)
            
            print(f"\n{'='*60}")
            print(f"검색 결과: '{query}'")
            print(f"{'='*60}")
            
            if not results:
                print("❌ 결과 없음\n")
                continue
            
            for i, result in enumerate(results):
                print(f"\n{i+1}. [{result.lab_name}] 점수: {result.score:.3f}")
                print(f"   {result.text[:100]}...")
            
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 검색 종료")
            break
        except Exception as e:
            print(f"❌ 오류: {e}\n")


def show_stats(data_dir: str = './crawl_data'):
    """통계 정보 출력"""
    print("="*80)
    print("로컬 저장소 통계")
    print("="*80)
    
    store = LocalVectorStore(data_dir=data_dir)
    stats = store.get_stats()
    
    print(f"\n📊 기본 통계:")
    print(f"  총 연구실: {stats['total_labs']}")
    print(f"  총 문서: {stats['total_docs']}")
    print(f"  평균 품질: {stats.get('avg_quality_score', 0):.1f}")
    
    if 'section_distribution' in stats:
        print(f"\n📂 섹션별 문서 수:")
        for section, count in sorted(stats['section_distribution'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {section:15s}: {count:4d}")
    
    if 'language_distribution' in stats:
        print(f"\n🌐 언어별 문서 수:")
        for lang, count in sorted(stats['language_distribution'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {lang:15s}: {count:4d}")
    
    # 연구실 목록
    print(f"\n🏫 연구실 목록:")
    for lab in store.labs.values():
        doc_count = sum(1 for doc in store.documents.values() if doc.lab_id == lab.lab_id)
        print(f"  [{lab.lab_id:2d}] {lab.kor_name:30s} - 문서 {doc_count:3d}개")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='로컬 벡터 저장소 검색')
    parser.add_argument('--mode', choices=['search', 'interactive', 'stats'], default='interactive',
                        help='실행 모드: search(단일 검색), interactive(대화형), stats(통계)')
    parser.add_argument('--query', '-q', type=str, help='검색어 (search 모드)')
    parser.add_argument('--limit', '-l', type=int, default=5, help='결과 개수')
    parser.add_argument('--data-dir', '-d', type=str, default='./crawl_data', help='데이터 디렉토리')
    
    args = parser.parse_args()
    
    if args.mode == 'search':
        if not args.query:
            print("❌ search 모드에서는 --query 옵션이 필요합니다")
            print("예: python search_local.py --mode search --query '컴퓨터 비전'")
            sys.exit(1)
        search_local(args.query, args.limit, args.data_dir)
    
    elif args.mode == 'interactive':
        interactive_search(args.data_dir)
    
    elif args.mode == 'stats':
        show_stats(args.data_dir)
