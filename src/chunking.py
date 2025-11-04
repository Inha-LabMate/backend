"""
청킹 & 본문 추출 모듈
===================

이 모듈은 웹페이지(HTML)에서 의미있는 본문을 추출하고, 
적절한 크기로 잘라서 청크(chunk)로 만드는 역할을 합니다.

주요 기능:
1. HTML에서 본문만 추출 (광고, 메뉴, 푸터 등 제거)
2. 텍스트를 200-400자 단위로 분할
3. 각 청크의 섹션 자동 분류 (연구, 논문, 멤버 등)
4. MD5 해시로 중복 문서 방지

예시:
    processor = DocumentProcessor()
    chunks = processor.process_html(html_content, url)
    # → Chunk 객체들의 리스트 반환
"""

import re
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag, NavigableString
import unicodedata


@dataclass
class Chunk:
    """
    청크 데이터 클래스
    
    하나의 청크는 웹페이지에서 추출한 텍스트 조각입니다.
    
    속성:
        text (str): 청크의 실제 텍스트 내용
        title (str, optional): 청크의 제목 (예: 'Research Area', '연구 분야')
        section (str): 청크가 속한 섹션 종류
            - 'about': 연구실 소개
            - 'research': 연구 분야
            - 'publication': 논문 목록
            - 'project': 프로젝트
            - 'join': 모집 정보
            - 'people': 구성원
            - 'general': 기타
        parent_heading (str, optional): 상위 헤딩 (문맥 파악용)
        char_count (int): 문자 수
        token_count (int): 토큰 수 추정값 (한글 1.5토큰/자, 영문 0.25토큰/단어)
        md5 (str): 텍스트의 MD5 해시 (중복 체크용)
        source_url (str): 출처 URL
        crawl_depth (int): 크롤링 깊이 (0=메인 페이지, 1=링크된 페이지)
        quality_score (float): 품질 점수 (0.0-1.0)
            - 섹션 일치도, 길이, 언어 일관성 등 고려
        has_pii (bool): 개인정보 포함 여부
        is_duplicate (bool): 중복 여부
    
    예시:
        chunk = Chunk(
            text="우리 연구실은 AI를 연구합니다",
            section="about",
            char_count=18,
            quality_score=0.85
        )
    """
    text: str
    title: Optional[str] = None
    section: str = 'general'
    parent_heading: Optional[str] = None
    char_count: int = 0
    token_count: int = 0
    md5: str = ''
    source_url: str = ''
    crawl_depth: int = 0
    quality_score: float = 0.0  # 0.0-1.0
    has_pii: bool = False  # 개인정보 포함 여부
    is_duplicate: bool = False  # 중복 여부
    
    def __post_init__(self):
        """
        객체 생성 후 자동으로 실행되는 초기화 함수
        - char_count가 0이면 텍스트 길이로 자동 설정
        - md5가 없으면 텍스트로부터 자동 생성
        """
        if not self.char_count:
            self.char_count = len(self.text)
        if not self.md5:
            self.md5 = hashlib.md5(self.text.encode('utf-8')).hexdigest()


class ContentExtractor:
    """
    HTML에서 핵심 콘텐츠만 추출하는 클래스
    
    역할:
        웹페이지에는 메뉴, 광고, 푸터 등 불필요한 내용이 많습니다.
        이 클래스는 연구실 설명, 논문 목록 등 중요한 내용만 골라냅니다.
    
    제거 대상:
        - 네비게이션 메뉴 (nav, menu)
        - 푸터/헤더 (footer, header, sidebar)
        - 광고 (ad, advertisement, sponsored)
        - 댓글 영역 (comment, reply)
        - SNS 공유 버튼 등
    
    예시:
        extractor = ContentExtractor()
        html = "<html>...</html>"
        clean_text = extractor.clean_html(html, "https://example.com")
    """
    
    # PII(개인정보) 및 비공개 페이지 탐지 패턴
    PII_KEYWORDS = [
        'login', 'password', 'signin', 'signup', 'register',
        'personal information', '개인정보', '로그인', '회원가입',
        '비밀번호', 'portal', 'intranet', '인트라넷'
    ]
    
    # 색인 제외할 URL 패턴
    EXCLUDED_PATTERNS = [
        r'/login', r'/signin', r'/admin', r'/portal',
        r'/mypage', r'/privacy', r'/personal',
        r'\?(.*&)?(password|token|key)=',  # 쿼리에 민감정보
    ]
    
    # 제거할 태그/클래스 패턴
    NOISE_PATTERNS = {
        # 태그 이름으로 제거
        'tags': ['nav', 'footer', 'header', 'aside', 'script', 'style', 'iframe'],
        
        # 클래스 이름에 이런 단어가 포함되면 제거
        'classes': [
            'navigation', 'nav', 'menu', 'sidebar', 'footer', 'header',
            'advertisement', 'ad', 'banner', 'cookie', 'popup',
            'breadcrumb', 'social', 'share', 'comment'
        ],
        
        # ID에 이런 단어가 포함되면 제거
        'ids': [
            'nav', 'navigation', 'menu', 'sidebar', 'footer', 'header',
            'comments', 'related', 'advertisement'
        ]
    }
    
    @staticmethod
    def clean_html(soup: BeautifulSoup) -> BeautifulSoup:
        """
        HTML에서 노이즈(불필요한 요소) 제거
        
        Args:
            soup: BeautifulSoup 객체 (파싱된 HTML)
        
        Returns:
            깨끗해진 BeautifulSoup 객체
        
        처리 과정:
            1. script, style 등의 태그 완전 삭제
            2. 'navigation', 'menu' 등의 클래스를 가진 요소 삭제
            3. 'sidebar', 'footer' 등의 ID를 가진 요소 삭제
        """
        # 1. 스크립트/스타일 등 제거
        for tag_name in ContentExtractor.NOISE_PATTERNS['tags']:
            for tag in soup.find_all(tag_name):
                tag.decompose()  # 태그를 완전히 삭제
        
        # 2. 노이즈 클래스 제거
        # 예: <div class="sidebar menu"> → 삭제
        for element in soup.find_all(class_=True):
            # attrs가 None인 경우 처리
            if not hasattr(element, 'attrs') or element.attrs is None:
                continue
            
            classes = element.get('class', [])
            if isinstance(classes, list) and any(noise in ' '.join(classes).lower() 
                   for noise in ContentExtractor.NOISE_PATTERNS['classes']):
                element.decompose()
        
        # 3. 노이즈 ID 제거
        # 예: <div id="navigation"> → 삭제
        for element in soup.find_all(id=True):
            # attrs가 None인 경우 처리
            if not hasattr(element, 'attrs') or element.attrs is None:
                continue
            
            element_id = element.get('id', '')
            if isinstance(element_id, str) and any(noise in element_id.lower() 
                   for noise in ContentExtractor.NOISE_PATTERNS['ids']):
                element.decompose()
        
        return soup
        
        return soup
    
    @staticmethod
    def extract_main_content(html: str) -> Tuple[BeautifulSoup, str]:
        """
        메인 콘텐츠 추출
        Returns: (cleaned_soup, main_text)
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 노이즈 제거
        soup = ContentExtractor.clean_html(soup)
        
        # 2. main 태그 우선 탐색
        main_content = soup.find('main')
        if main_content:
            return main_content, ContentExtractor._extract_clean_text(main_content)
        
        # 3. article 태그 탐색
        article = soup.find('article')
        if article:
            return article, ContentExtractor._extract_clean_text(article)
        
        # 4. content 관련 div 탐색
        for content_class in ['content', 'main-content', 'page-content', 'post-content']:
            content_div = soup.find('div', class_=re.compile(content_class, re.I))
            if content_div:
                return content_div, ContentExtractor._extract_clean_text(content_div)
        
        # 5. body 전체 (최후)
        body = soup.find('body')
        if body:
            return body, ContentExtractor._extract_clean_text(body)
        
        return soup, ContentExtractor._extract_clean_text(soup)
    
    @staticmethod
    def _extract_clean_text(element) -> str:
        """
        BeautifulSoup 엘리먼트에서 깨끗한 텍스트 추출
        
        문제: get_text()는 공백/줄바꿈이 너무 많아서 청크 생성 실패
        해결: 단락(p, div, h1-h6 등) 단위로 텍스트 추출 후 병합
        """
        text_parts = []
        
        # 의미있는 텍스트 태그들
        content_tags = [
            'p', 'div', 'span', 'article', 'section',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'li', 'td', 'th', 'blockquote', 'pre'
        ]
        
        # 모든 텍스트 노드 재귀 탐색
        for tag in element.find_all(content_tags):
            # 직접 자식 텍스트만 (중첩 방지)
            text = tag.get_text(separator=' ', strip=True)
            if text and len(text) > 10:  # 10자 이상만
                # 연속 공백 제거
                text = re.sub(r'\s+', ' ', text)
                text_parts.append(text)
        
        # 텍스트가 없으면 전체 텍스트 시도
        if not text_parts:
            text = element.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text
        
        # 중복 제거 (같은 텍스트가 중첩되어 나오는 경우)
        unique_parts = []
        seen = set()
        for part in text_parts:
            # 텍스트 정규화 (소문자 + 공백 제거)
            normalized = part.lower().replace(' ', '')
            if normalized not in seen:
                seen.add(normalized)
                unique_parts.append(part)
        
        # 문단 구분하여 병합
        return '\n\n'.join(unique_parts)
    
    @staticmethod
    def identify_section(text: str, url: str = '') -> str:
        """
        텍스트/URL에서 섹션 식별 - 이 텍스트가 어떤 종류인지 자동 분류
        
        Args:
            text: 분석할 텍스트
            url: 페이지 URL (URL에서도 힌트를 얻음)
        
        Returns:
            섹션 종류 문자열:
                - 'about': 연구실 소개
                - 'research': 연구 분야/주제
                - 'publication': 논문/출판물
                - 'project': 프로젝트
                - 'people': 구성원/멤버
                - 'join': 모집/입학 정보
                - 'general': 기타
        
        판단 기준:
            1. URL 우선 확인 (예: '/research' → research)
            2. 텍스트 내용의 키워드 확인
        
        예시:
            identify_section("연구 분야: AI, ML", "http://lab.com/research")
            # → 'research'
        """
        text_lower = text.lower()
        url_lower = url.lower()
        
        # URL 기반 우선 판단
        # 예: https://lab.com/research → 'research'
        if any(kw in url_lower for kw in ['research', 'lab', '연구']):
            return 'research'
        if any(kw in url_lower for kw in ['publication', 'paper', 'pub', '논문']):
            return 'publication'
        if any(kw in url_lower for kw in ['project', '프로젝트', 'proj']):
            return 'project'
        if any(kw in url_lower for kw in ['people', 'member', 'team', '구성원', '멤버']):
            return 'people'
        if any(kw in url_lower for kw in ['join', 'recruit', 'admission', '모집', '입학']):
            return 'join'
        if any(kw in url_lower for kw in ['about', 'intro', '소개']):
            return 'about'
        
        # 텍스트 기반 판단
        # 예: "publication: ..." → 'publication'
        if any(kw in text_lower for kw in ['publication', 'paper', '논문', 'journal', 'conference']):
            return 'publication'
        if any(kw in text_lower for kw in ['research area', 'research interest', '연구분야', '연구주제']):
            return 'research'
        if any(kw in text_lower for kw in ['project', '프로젝트', '과제']):
            return 'project'
        if any(kw in text_lower for kw in ['professor', 'phd', 'master', '교수', '박사', '석사']):
            return 'people'
        if any(kw in text_lower for kw in ['recruit', 'admission', 'join us', '모집', '지원']):
            return 'join'
        if any(kw in text_lower for kw in ['about', 'overview', '소개', '개요']):
            return 'about'
        
        return 'general'  # 분류 안되면 기타


class QualityScorer:
    """
    청크 품질 점수 계산 클래스 (0.0 - 1.0)
    
    낮은 품질의 청크는 검수 대상으로 표시됩니다.
    
    점수 기준:
        1. 섹션 일치도: 텍스트가 분류된 섹션과 잘 맞는가? (0.3)
        2. 길이 적절성: 너무 짧거나 길지 않은가? (0.25)
        3. 언어 일관성: 한 언어로 통일되었는가? (0.25)
        4. 중복 여부: 다른 청크와 겹치지 않는가? (0.2)
    
    예시:
        scorer = QualityScorer()
        score = scorer.calculate_quality(chunk, all_chunks)
        if score < 0.5:
            print("검수 필요!")
    """
    
    # 각 섹션별 기대 키워드
    SECTION_KEYWORDS = {
        'research': ['research', 'study', '연구', '학습', 'ai', 'ml', 'algorithm'],
        'publication': ['paper', 'journal', 'conference', '논문', 'publication', 'proc'],
        'project': ['project', 'grant', '과제', '프로젝트', 'funded'],
        'people': ['professor', 'student', 'phd', '교수', '학생', '박사', '석사'],
        'join': ['recruit', 'admission', 'apply', '모집', '지원', '입학'],
        'about': ['about', 'overview', 'intro', '소개', '개요', 'mission']
    }
    
    def calculate_quality(self, chunk: Chunk, all_chunks: List[Chunk] = None) -> float:
        """
        청크의 품질 점수 계산
        
        Args:
            chunk: 평가할 청크
            all_chunks: 전체 청크 리스트 (중복 체크용, 선택)
        
        Returns:
            품질 점수 (0.0-1.0)
        """
        scores = []
        
        # 1. 섹션 일치도 (30%)
        section_score = self._section_match_score(chunk)
        scores.append(section_score * 0.3)
        
        # 2. 길이 적절성 (25%)
        length_score = self._length_score(chunk)
        scores.append(length_score * 0.25)
        
        # 3. 언어 일관성 (25%)
        language_score = self._language_consistency_score(chunk)
        scores.append(language_score * 0.25)
        
        # 4. 중복 여부 (20%)
        if all_chunks:
            duplicate_score = self._duplicate_score(chunk, all_chunks)
        else:
            duplicate_score = 1.0
        scores.append(duplicate_score * 0.2)
        
        return sum(scores)
    
    def _section_match_score(self, chunk: Chunk) -> float:
        """섹션과 텍스트 내용의 일치도"""
        if chunk.section == 'general':
            return 0.5  # 일반 섹션은 중립
        
        text_lower = chunk.text.lower()
        keywords = self.SECTION_KEYWORDS.get(chunk.section, [])
        
        # 키워드 매칭 개수
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        # 매칭 비율
        if keywords:
            return min(matches / len(keywords) * 2, 1.0)  # 최대 1.0
        return 0.5
    
    def _length_score(self, chunk: Chunk) -> float:
        """길이 적절성 점수"""
        char_count = chunk.char_count
        
        # 200-400자가 최적
        if 200 <= char_count <= 400:
            return 1.0
        elif 150 <= char_count < 200:
            return 0.8  # 약간 짧음
        elif 400 < char_count <= 500:
            return 0.8  # 약간 김
        elif 100 <= char_count < 150:
            return 0.6  # 많이 짧음
        elif 500 < char_count <= 600:
            return 0.6  # 많이 김
        else:
            return 0.3  # 너무 짧거나 김
    
    def _language_consistency_score(self, chunk: Chunk) -> float:
        """언어 일관성 점수"""
        text = chunk.text
        
        # 한글/영문 비율 계산
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_alpha = korean_chars + english_chars
        
        if total_alpha == 0:
            return 0.5  # 문자가 없으면 중립
        
        # 한 언어가 80% 이상이면 일관성 높음
        korean_ratio = korean_chars / total_alpha
        english_ratio = english_chars / total_alpha
        
        if korean_ratio >= 0.8 or english_ratio >= 0.8:
            return 1.0  # 단일 언어
        elif korean_ratio >= 0.6 or english_ratio >= 0.6:
            return 0.8  # 약간 섞임
        else:
            return 0.5  # 많이 섞임 (혼용은 나쁘지 않을 수 있음)
    
    def _duplicate_score(self, chunk: Chunk, all_chunks: List[Chunk]) -> float:
        """중복 점수 (낮을수록 중복 많음)"""
        # 같은 MD5 해시 개수 확인
        same_md5 = sum(1 for c in all_chunks if c.md5 == chunk.md5)
        
        if same_md5 <= 1:
            return 1.0  # 중복 없음
        elif same_md5 == 2:
            return 0.5  # 1개 중복
        else:
            return 0.0  # 다중 중복


class TextChunker:
    """텍스트 청킹 (200-400자 기준)"""
    
    MIN_CHUNK_SIZE = 200  # 최소 청크 크기 (문자)
    MAX_CHUNK_SIZE = 400  # 최대 청크 크기 (문자)
    OVERLAP_SIZE = 50     # 청크 간 오버랩 (문자)
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        토큰 수 추정 (한글/영문 혼합)
        - 한글: 1.5 토큰/글자
        - 영문: 0.25 토큰/단어
        """
        # 한글 문자 수
        korean_chars = len(re.findall(r'[가-힣]', text))
        # 영문 단어 수
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        # 기타 문자
        other_chars = len(text) - korean_chars - len(re.findall(r'[a-zA-Z\s]', text))
        
        # 토큰 수 계산
        tokens = int(korean_chars * 1.5 + english_words * 0.25 + other_chars * 0.5)
        return tokens
    
    @staticmethod
    def split_by_paragraphs(text: str) -> List[str]:
        """텍스트를 문단으로 분리"""
        # 줄바꿈 2개 이상 = 문단 구분
        paragraphs = re.split(r'\n{2,}', text)
        # 빈 문단 제거
        return [p.strip() for p in paragraphs if p.strip()]
    
    @staticmethod
    def _is_heading(text: str) -> bool:
        """헤딩인지 판별 (짧고 ':' 또는 숫자로 시작)"""
        return len(text) < 100 and (
            text.endswith(':') or 
            re.match(r'^\d+\.?\s', text) or
            text.isupper()
        )
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """텍스트 정리"""
        # 공백 정규화
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def _create_chunk(text: str, title: str = None, section: str = 'general', 
                     source_url: str = '', crawl_depth: int = 0) -> Chunk:
        """청크 객체 생성"""
        cleaned_text = TextChunker._clean_text(text)
        return Chunk(
            text=cleaned_text,
            title=title,
            section=section,
            char_count=len(cleaned_text),
            token_count=TextChunker.estimate_tokens(cleaned_text),
            md5=hashlib.md5(cleaned_text.encode('utf-8')).hexdigest(),
            source_url=source_url,
            crawl_depth=crawl_depth
        )
    
    def chunk_text(self, text: str, section: str = 'general', 
                   title: Optional[str] = None,
                   source_url: str = '', crawl_depth: int = 0) -> List[Chunk]:
        """텍스트를 청크로 분리"""
        paragraphs = TextChunker.split_by_paragraphs(text)
        chunks = []
        
        current_chunk_text = ""
        current_title = title  # 전달받은 title 사용
        
        for para in paragraphs:
            # 헤딩이면 제목으로 설정
            if TextChunker._is_heading(para):
                # 이전 청크 저장
                if current_chunk_text and len(current_chunk_text) >= TextChunker.MIN_CHUNK_SIZE:
                    chunks.append(TextChunker._create_chunk(
                        current_chunk_text, current_title, section,
                        source_url, crawl_depth
                    ))
                    current_chunk_text = ""
                
                current_title = para
                continue
            
            # 문단 추가
            if current_chunk_text:
                current_chunk_text += "\n\n" + para
            else:
                current_chunk_text = para
            
            # 크기 확인
            if len(current_chunk_text) >= TextChunker.MAX_CHUNK_SIZE:
                chunks.append(TextChunker._create_chunk(
                    current_chunk_text, current_title, section,
                    source_url, crawl_depth
                ))
                
                # 오버랩 설정
                overlap_text = current_chunk_text[-TextChunker.OVERLAP_SIZE:]
                current_chunk_text = overlap_text
        
        # 마지막 청크
        if current_chunk_text and len(current_chunk_text) >= TextChunker.MIN_CHUNK_SIZE:
            chunks.append(TextChunker._create_chunk(
                current_chunk_text, current_title, section,
                source_url, crawl_depth
            ))
        
        return chunks





class DocumentProcessor:
    """문서 처리 통합 클래스"""
    
    def __init__(self):
        self.extractor = ContentExtractor()
        self.chunker = TextChunker()
    
    def process_html(
        self, 
        html: str, 
        url: str = '', 
        crawl_depth: int = 0
    ) -> List[Chunk]:
        """
        HTML 문서 처리 파이프라인
        1. 본문 추출
        2. 섹션 식별
        3. 청킹
        """
        # 1. 본문 추출
        soup, main_text = ContentExtractor.extract_main_content(html)
        
        if not main_text or len(main_text) < 100:
            return []
        
        # 2. 페이지 제목 추출
        title = None
        if soup is not None:
            title_tag = soup.find('h1')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # 3. 섹션 식별
        section = ContentExtractor.identify_section(main_text, url)
        
        # 4. 청킹
        chunks = self.chunker.chunk_text(
            text=main_text,
            section=section,
            title=title,
            source_url=url,
            crawl_depth=crawl_depth
        )
        
        return chunks
    
    def process_text(
        self,
        text: str,
        section: str = 'general',
        title: Optional[str] = None,
        source_url: str = '',
        crawl_depth: int = 0
    ) -> List[Chunk]:
        """순수 텍스트 처리"""
        return self.chunker.chunk_text(
            text=text,
            section=section,
            title=title,
            source_url=source_url,
            crawl_depth=crawl_depth
        )


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    # 테스트
    processor = DocumentProcessor()
    
    sample_html = """
    <html>
    <head><title>연구실 소개</title></head>
    <body>
        <nav>메뉴1 메뉴2 메뉴3</nav>
        <main>
            <h1>AI 연구실</h1>
            <section>
                <h2>연구 분야</h2>
                <p>우리 연구실은 컴퓨터 비전과 자연어 처리를 중심으로 연구합니다. 
                최근에는 멀티모달 학습에 집중하고 있으며, 특히 이미지-텍스트 정합 기술을 
                개발하고 있습니다.</p>
                
                <p>주요 연구 주제는 다음과 같습니다:
                1) 객체 탐지 및 인식
                2) 이미지 캡셔닝
                3) 시각 질의응답</p>
            </section>
            <section>
                <h2>최근 논문</h2>
                <p>CVPR 2024에 2편의 논문이 채택되었습니다. 
                첫 번째 논문은 새로운 attention 메커니즘을 제안하였고, 
                두 번째 논문은 few-shot learning에 관한 것입니다.</p>
            </section>
        </main>
        <footer>Copyright 2024</footer>
    </body>
    </html>
    """
    
    chunks = processor.process_html(
        html=sample_html,
        url="https://example.com/research",
        crawl_depth=1
    )
    
    print(f"생성된 청크 수: {len(chunks)}\n")
    
    for i, chunk in enumerate(chunks):
        print(f"=== 청크 {i+1} ===")
        print(f"섹션: {chunk.section}")
        print(f"제목: {chunk.title}")
        print(f"길이: {chunk.char_count}자 ({chunk.token_count} 토큰 추정)")
        print(f"MD5: {chunk.md5}")
        print(f"텍스트: {chunk.text[:100]}...")
        print()
