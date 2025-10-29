"""
임베딩 & 검색 테스트

실제 텍스트를 임베딩하고 유사도 검색을 테스트합니다.
"""

import numpy as np
import hashlib
from embedding import EmbeddingPipeline
from local_storage import LocalVectorStore


def test_embedding_and_search():
    """임베딩 생성 및 검색 테스트"""
    print("=" * 60)
    print("임베딩 & 검색 종합 테스트")
    print("=" * 60)
    
    # 1. 임베딩 파이프라인 초기화
    print("\n[1단계] 임베딩 모델 로딩...")
    pipeline = EmbeddingPipeline(
        model_name='multilingual-mpnet',  # 지원되는 모델 이름
        device='cpu'
    )
    print("✅ 모델 로딩 완료")
    
    # 2. 샘플 연구실 문서들
    print("\n[2단계] 샘플 문서 준비...")
    
    sample_docs = [
        {
            'lab_name': 'Computer Vision Lab',
            'text': '우리 연구실은 컴퓨터 비전과 딥러닝을 연구합니다. 특히 객체 탐지, 이미지 분할, 3D 재구성 등의 분야에 집중하고 있습니다.',
            'section': 'research'
        },
        {
            'lab_name': 'NLP Lab',
            'text': '자연어 처리와 대화 시스템을 연구합니다. BERT, GPT 등의 트랜스포머 모델을 활용한 한국어 처리 기술을 개발하고 있습니다.',
            'section': 'research'
        },
        {
            'lab_name': 'Robotics Lab',
            'text': '로봇 제어와 자율 주행 시스템을 연구합니다. 센서 융합, 경로 계획, 강화학습 기반 로봇 제어를 다룹니다.',
            'section': 'research'
        },
        {
            'lab_name': 'Computer Vision Lab',
            'text': 'CVPR 2024에 2편, ICCV 2023에 1편의 논문이 채택되었습니다. 주요 주제는 Transformer 기반 객체 탐지입니다.',
            'section': 'publication'
        },
        {
            'lab_name': 'NLP Lab',
            'text': '학부 연구생을 모집합니다. 주당 10시간 이상 참여 가능한 학생을 선발합니다. 기계학습 기초 지식이 필요합니다.',
            'section': 'join'
        },
    ]
    
    print(f"✅ {len(sample_docs)}개 문서 준비 완료")
    
    # 3. 임베딩 생성
    print("\n[3단계] 임베딩 생성 중...")
    
    embeddings = []
    for i, doc in enumerate(sample_docs):
        result = pipeline.embed(doc['text'])
        embeddings.append(result.embedding)
        print(f"  문서 {i+1}/{len(sample_docs)}: {doc['lab_name']} - {doc['section']}")
        print(f"    벡터 차원: {len(result.embedding)}")
        print(f"    정규화 여부: {result.normalized}")
    
    print(f"✅ 총 {len(embeddings)}개 임베딩 생성 완료")
    
    # 4. 로컬 저장소에 저장
    print("\n[4단계] 로컬 저장소에 저장...")
    
    store = LocalVectorStore(data_dir='./test_embedding_data')
    
    # 연구실 ID 매핑
    lab_ids = {}
    
    # 연구실 생성
    for lab_name in set(doc['lab_name'] for doc in sample_docs):
        lab_id = store.insert_lab({
            'kor_name': lab_name,
            'eng_name': lab_name,
            'homepage': f"https://example.com/{lab_name.lower().replace(' ', '_')}",
            'description': f"{lab_name} 연구실"
        })
        lab_ids[lab_name] = lab_id
    
    # 문서 삽입
    for doc, emb in zip(sample_docs, embeddings):
        lab_id = lab_ids[doc['lab_name']]
        
        store.insert_document(
            lab_id=lab_id,
            doc_data={
                'text': doc['text'],
                'embedding': emb.tolist(),
                'section': doc['section'],
                'char_count': len(doc['text']),
                'md5': hashlib.md5(doc['text'].encode()).hexdigest()
            }
        )
    
    stats = store.get_stats()
    print(f"✅ 저장 완료: 연구실 {stats['total_labs']}개, 문서 {stats['total_docs']}개")
    
    # 5. 검색 테스트
    print("\n[5단계] 검색 테스트...")
    print("=" * 60)
    
    queries = [
        "딥러닝과 컴퓨터 비전으로 이미지 분석",
        "자연어 처리 한국어 모델",
        "로봇 자율주행 강화학습",
        "CVPR 논문 객체 탐지",
        "학부생 연구실 모집"
    ]
    
    for query in queries:
        print(f"\n🔍 쿼리: '{query}'")
        
        # 쿼리 임베딩
        query_result = pipeline.embed(query)
        query_emb = query_result.embedding
        
        # 검색
        results = store.search_vector(
            query_embedding=query_emb,
            limit=3
        )
        
        print(f"   결과 {len(results)}개:")
        
        for i, result in enumerate(results, 1):
            print(f"\n   {i}. [{result.lab_name}] (유사도: {result.score:.3f})")
            print(f"      섹션: {result.section}")
            print(f"      내용: {result.text[:80]}...")
    
    # 6. 통계 출력
    print("\n" + "=" * 60)
    print("[통계]")
    print("=" * 60)
    
    stats = store.get_stats()
    print(f"총 연구실: {stats['total_labs']}")
    print(f"총 문서: {stats['total_docs']}")
    print(f"평균 문서 길이: {stats.get('avg_char_count', 0):.1f}자")
    
    if 'section_distribution' in stats:
        print("\n섹션별 분포:")
        for section, count in stats['section_distribution'].items():
            print(f"  {section}: {count}개")
    
    print("\n✅ 모든 테스트 완료!")


if __name__ == "__main__":
    test_embedding_and_search()
