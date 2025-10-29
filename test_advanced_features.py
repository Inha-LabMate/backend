"""
고급 기능 종합 테스트

이 스크립트는 새로 추가된 모든 기능을 테스트합니다:
    1. 품질 점수 계산
    2. PII 감지
    3. 크롤링 매니저 (속도 제한, 재시도)
    4. 표 추출
    5. PDF 처리 (선택)

실행:
    python test_advanced_features.py
"""

import sys
import os


def test_quality_scorer():
    """품질 점수 계산 테스트"""
    print("=" * 60)
    print("1. 품질 점수 계산 테스트")
    print("=" * 60)
    
    from quality_guard import QualityScorer
    from chunking import Chunk
    
    scorer = QualityScorer()
    
    # 테스트 청크들
    test_cases = [
        {
            'name': '고품질 연구 텍스트',
            'chunk': Chunk(
                text="우리 연구실은 컴퓨터 비전과 딥러닝을 중심으로 연구합니다. " * 5,
                section="research",
                char_count=300
            )
        },
        {
            'name': '너무 짧은 텍스트',
            'chunk': Chunk(
                text="짧은 텍스트",
                section="general",
                char_count=7
            )
        },
        {
            'name': '섹션 불일치',
            'chunk': Chunk(
                text="우리 연구실에서는 다양한 프로젝트를 진행합니다. " * 5,
                section="publication",  # 프로젝트 내용인데 publication으로 분류됨
                char_count=270
            )
        },
    ]
    
    for test in test_cases:
        print(f"\n테스트: {test['name']}")
        print(f"텍스트: {test['chunk'].text[:50]}...")
        
        report = scorer.calculate_quality(test['chunk'])
        
        print(f"  전체 점수: {report.overall_score:.2f}")
        print(f"  - 섹션 일치: {report.section_score:.2f}")
        print(f"  - 길이: {report.length_score:.2f}")
        print(f"  - 언어: {report.language_score:.2f}")
        print(f"  - 중복: {report.duplicate_score:.2f}")
        
        if report.needs_review:
            print(f"  ⚠️  검수 필요: {report.reason}")
        else:
            print(f"  ✅ 품질 양호")
    
    print("\n✅ 품질 점수 테스트 완료\n")


def test_guardrail():
    """가드레일 (PII 감지) 테스트"""
    print("=" * 60)
    print("2. 가드레일 (PII 감지) 테스트")
    print("=" * 60)
    
    from quality_guard import GuardRail
    
    guard = GuardRail()
    
    # URL 차단 테스트
    print("\n[URL 차단 테스트]")
    test_urls = [
        ("https://example.com/research", False),
        ("https://example.com/login", True),
        ("https://example.com/admin/portal", True),
        ("https://example.com/data?password=123", True),
    ]
    
    for url, expected_block in test_urls:
        should_exclude, reason = guard.should_exclude_url(url)
        status = "✅ 정상" if should_exclude == expected_block else "❌ 오류"
        action = "차단" if should_exclude else "허용"
        
        print(f"{status} {action}: {url}")
        if should_exclude:
            print(f"   이유: {reason}")
    
    # PII 텍스트 감지 테스트
    print("\n[PII 텍스트 감지 테스트]")
    test_texts = [
        ("우리 연구실은 AI를 연구합니다.", False),
        ("로그인하여 개인정보를 입력하세요.", True),
        ("Please sign in with your password.", True),
    ]
    
    for text, expected_pii in test_texts:
        has_pii, keywords = guard.detect_pii_in_text(text)
        status = "✅ 정상" if has_pii == expected_pii else "❌ 오류"
        result = "PII 발견" if has_pii else "안전"
        
        print(f"{status} {result}: {text}")
        if has_pii:
            print(f"   키워드: {', '.join(keywords)}")
    
    print("\n✅ 가드레일 테스트 완료\n")


def test_crawl_manager():
    """크롤링 매니저 테스트"""
    print("=" * 60)
    print("3. 크롤링 매니저 테스트")
    print("=" * 60)
    
    from crawl_manager import CrawlManager
    
    manager = CrawlManager(
        delay=0.5,  # 테스트용으로 짧게
        max_retries=2,
        user_agent="TestBot/1.0"
    )
    
    test_urls = [
        "https://httpbin.org/html",  # 성공
        "https://httpbin.org/status/404",  # 404 에러
        "https://httpbin.org/delay/2",  # 느린 응답
    ]
    
    print("\n[URL 크롤링 테스트]")
    for url in test_urls:
        print(f"\n요청: {url}")
        result = manager.fetch_url(url)
        
        if result.success:
            print(f"  ✅ 성공 (상태: {result.status_code})")
            print(f"  HTML 길이: {len(result.html)} 문자")
            if result.cached:
                print(f"  📦 캐시 사용")
        else:
            print(f"  ❌ 실패: {result.error}")
    
    print("\n[통계]")
    manager.print_stats()
    
    print("\n✅ 크롤링 매니저 테스트 완료\n")


def test_table_extractor():
    """표 추출 테스트"""
    print("=" * 60)
    print("4. 표 추출 테스트")
    print("=" * 60)
    
    from advanced_extractors import TableExtractor
    
    extractor = TableExtractor()
    
    sample_html = """
    <table>
        <caption>최근 논문 목록</caption>
        <thead>
            <tr>
                <th>Year</th>
                <th>Venue</th>
                <th>Title</th>
                <th>Author</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>2024</td>
                <td>CVPR</td>
                <td>Vision Transformer for Image Recognition</td>
                <td>Kim et al.</td>
            </tr>
            <tr>
                <td>2023</td>
                <td>ICCV</td>
                <td>Object Detection with Deep Learning</td>
                <td>Lee et al.</td>
            </tr>
            <tr>
                <td>2023</td>
                <td>NeurIPS</td>
                <td>Efficient Neural Networks</td>
                <td>Park et al.</td>
            </tr>
        </tbody>
    </table>
    """
    
    print("\n[표 추출]")
    tables = extractor.extract_tables(sample_html)
    
    for i, table in enumerate(tables, 1):
        print(f"\n표 {i}:")
        print(f"캡션: {table.caption}")
        print(f"헤더: {table.headers}")
        print(f"행 수: {len(table.rows)}")
        
        print("\n텍스트 형식:")
        print(table.to_text())
        
        print("\n메타데이터:")
        print(f"  컬럼 매핑: {table.metadata.get('column_map', {})}")
        if 'lab_tags' in table.metadata:
            print(f"  논문 태그: {table.metadata['lab_tags']}")
        
        print("\n딕셔너리 형식 (첫 2개):")
        for row_dict in table.to_dict_list()[:2]:
            print(f"  {row_dict}")
    
    print("\n✅ 표 추출 테스트 완료\n")


def test_pdf_extractor():
    """PDF 추출 테스트 (선택)"""
    print("=" * 60)
    print("5. PDF 추출 테스트 (선택)")
    print("=" * 60)
    
    try:
        from advanced_extractors import PDFExtractor
        
        # PDF 파일이 있으면 테스트
        test_pdf = "test.pdf"
        if os.path.exists(test_pdf):
            print(f"\nPDF 파일 발견: {test_pdf}")
            
            extractor = PDFExtractor(backend='pypdf2')
            
            # 메타데이터 추출
            metadata = extractor.extract_metadata(test_pdf)
            print(f"제목: {metadata.get('title', 'N/A')}")
            print(f"저자: {metadata.get('author', 'N/A')}")
            print(f"페이지 수: {metadata.get('pages', 'N/A')}")
            
            # 텍스트 추출
            text = extractor.extract_text(test_pdf)
            print(f"\n추출된 텍스트 (처음 200자):")
            print(text[:200])
            
            print("\n✅ PDF 추출 테스트 완료")
        else:
            print(f"\n⚠️  PDF 파일이 없어 스킵: {test_pdf}")
            print("테스트하려면 'test.pdf' 파일을 현재 디렉토리에 두세요.")
    
    except ImportError as e:
        print(f"\n⚠️  PDF 라이브러리 미설치: {e}")
        print("설치: pip install PyPDF2 pdfplumber")
    
    print()


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("고급 기능 종합 테스트 시작")
    print("=" * 60 + "\n")
    
    try:
        test_quality_scorer()
        test_guardrail()
        test_crawl_manager()
        test_table_extractor()
        test_pdf_extractor()
        
        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
