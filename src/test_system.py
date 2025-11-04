"""
간단한 통합 테스트 스크립트
각 모듈이 정상 작동하는지 확인
"""

import sys


def test_imports():
    """모듈 임포트 테스트"""
    print("="*80)
    print("1. 모듈 임포트 테스트")
    print("="*80)
    
    modules = [
        'chunking',
        'text_normalization',
        'embedding',
        'vector_db',
        'main_pipeline'
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False
    
    print()
    return True


def test_chunking():
    """청킹 모듈 테스트"""
    print("="*80)
    print("2. 청킹 모듈 테스트")
    print("="*80)
    
    try:
        from chunking import DocumentProcessor
        
        processor = DocumentProcessor()
        
        sample_html = """
        <html>
        <body>
            <main>
                <h1>테스트 연구실</h1>
                <p>우리 연구실은 인공지능을 연구합니다. """ + "AI "* 50 + """</p>
                <p>주요 연구 분야는 컴퓨터 비전입니다.</p>
            </main>
        </body>
        </html>
        """
        
        chunks = processor.process_html(
            html=sample_html,
            url="https://example.com/lab"
        )
        
        print(f"  생성된 청크: {len(chunks)}개")
        
        if chunks:
            print(f"  첫 번째 청크:")
            print(f"    - 섹션: {chunks[0].section}")
            print(f"    - 길이: {chunks[0].char_count}자")
            print(f"    - 토큰: {chunks[0].token_count}")
            print(f"    - MD5: {chunks[0].md5[:16]}...")
        
        print("✅ 청킹 테스트 통과")
        
    except Exception as e:
        print(f"❌ 청킹 테스트 실패: {e}")
        return False
    
    print()
    return True


def test_normalization():
    """정규화 모듈 테스트"""
    print("="*80)
    print("3. 텍스트 정규화 테스트")
    print("="*80)
    
    try:
        from text_normalization import TextNormalizer
        
        normalizer = TextNormalizer()
        
        sample_text = """
        우리 연구실은 AI를 연구합니다.
        연락처: test@example.com
        전화: 032-860-7000
        URL: https://example.com
        
        Copyright © 2024
        """
        
        result = normalizer.normalize(sample_text)
        
        print(f"  언어: {result.language}")
        print(f"  토큰: {result.tokens}")
        print(f"  이메일: {len(result.emails)}개")
        print(f"  URL: {len(result.urls)}개")
        print(f"  전화: {len(result.phones)}개")
        print(f"  정리된 텍스트: {len(result.cleaned_text)}자")
        
        print("✅ 정규화 테스트 통과")
        
    except Exception as e:
        print(f"❌ 정규화 테스트 실패: {e}")
        return False
    
    print()
    return True


def test_embedding():
    """임베딩 모듈 테스트"""
    print("="*80)
    print("4. 임베딩 모듈 테스트")
    print("="*80)
    
    try:
        from embedding import EmbeddingPipeline
        import numpy as np
        
        print("  임베딩 모델 로딩 중...")
        pipeline = EmbeddingPipeline(
            model_name='multilingual-mpnet',
            device='cpu'
        )
        
        texts = [
            "인공지능 연구",
            "컴퓨터 비전",
            "Artificial Intelligence"
        ]
        
        print(f"  {len(texts)}개 텍스트 임베딩 중...")
        results = pipeline.embed(texts)
        
        print(f"  임베딩 완료:")
        for i, result in enumerate(results):
            print(f"    {i+1}. shape={result.embedding.shape}, "
                  f"norm={np.linalg.norm(result.embedding):.3f}")
        
        # 유사도 테스트
        from embedding import cosine_similarity
        sim = cosine_similarity(results[0].embedding, results[1].embedding)
        print(f"  유사도 ('인공지능 연구' vs '컴퓨터 비전'): {sim:.3f}")
        
        print("✅ 임베딩 테스트 통과")
        
    except ImportError as e:
        print(f"⚠️  임베딩 모듈 스킵 (sentence-transformers 미설치): {e}")
        return True  # 임베딩은 선택 사항으로 처리
    except Exception as e:
        print(f"❌ 임베딩 테스트 실패: {e}")
        return False
    
    print()
    return True


def test_database_schema():
    """데이터베이스 스키마 테스트"""
    print("="*80)
    print("5. 데이터베이스 스키마 확인")
    print("="*80)
    
    try:
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema = f.read()
        
        # 주요 테이블 확인
        tables = ['lab', 'lab_docs', 'lab_tag', 'lab_link', 'crawl_log', 'search_log']
        
        for table in tables:
            if f"CREATE TABLE IF NOT EXISTS {table}" in schema:
                print(f"  ✅ {table} 테이블 정의 존재")
            else:
                print(f"  ❌ {table} 테이블 정의 없음")
                return False
        
        # 함수 확인
        functions = ['search_by_vector', 'hybrid_search', 'check_duplicate_chunk']
        
        for func in functions:
            if f"CREATE OR REPLACE FUNCTION {func}" in schema:
                print(f"  ✅ {func} 함수 정의 존재")
            else:
                print(f"  ❌ {func} 함수 정의 없음")
                return False
        
        print("✅ 스키마 테스트 통과")
        
    except Exception as e:
        print(f"❌ 스키마 테스트 실패: {e}")
        return False
    
    print()
    return True


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("연구실 검색 시스템 - 통합 테스트")
    print("="*80)
    print()
    
    tests = [
        ("Import", test_imports),
        ("Chunking", test_chunking),
        ("Normalization", test_normalization),
        ("Embedding", test_embedding),
        ("Database Schema", test_database_schema)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} 테스트 중 예외 발생: {e}")
            results.append((name, False))
    
    # 결과 요약
    print("="*80)
    print("테스트 결과 요약")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print()
    print(f"총 {passed}/{total} 테스트 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        print("\n다음 단계:")
        print("  1. PostgreSQL 데이터베이스 설정")
        print("  2. python main_pipeline.py 실행")
        print("  3. uvicorn search_api:app --reload 실행")
        return 0
    else:
        print("\n⚠️  일부 테스트 실패")
        print("  실패한 테스트를 확인하고 필요한 패키지를 설치하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
