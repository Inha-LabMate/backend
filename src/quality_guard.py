"""
품질 점수 및 가드레일 모듈

이 모듈은 크롤링한 콘텐츠의 품질을 평가하고,
개인정보나 비공개 페이지를 차단합니다.

주요 기능:
    1. 품질 점수 계산 (0.0-1.0)
       - 섹션 일치도, 길이, 언어 일관성, 중복 여부
    2. PII(개인정보) 감지
    3. 제외 URL 패턴 관리
    
품질 점수가 0.5 미만이면 검수 대상으로 표시됩니다.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from chunking import Chunk


@dataclass
class QualityReport:
    """
    품질 점수 상세 리포트
    
    속성:
        overall_score: 전체 점수 (0.0-1.0)
        section_score: 섹션 일치도 점수
        length_score: 길이 적절성 점수
        language_score: 언어 일관성 점수
        duplicate_score: 중복 점수
        needs_review: 검수 필요 여부 (0.5 미만)
        reason: 낮은 점수의 이유
    """
    overall_score: float
    section_score: float
    length_score: float
    language_score: float
    duplicate_score: float
    needs_review: bool
    reason: str = ""


class GuardRail:
    """
    가드레일: PII 및 비공개 페이지 차단
    
    역할:
        크롤링하면 안 되는 페이지를 사전에 차단합니다.
        - 로그인 페이지
        - 포털/인트라넷
        - 개인정보 입력 폼
        
    사용법:
        guard = GuardRail()
        if guard.should_exclude_url(url):
            print("차단된 URL입니다!")
    """
    
    # PII(개인정보) 관련 키워드
    PII_KEYWORDS = [
        # 영문
        'login', 'password', 'signin', 'signup', 'register',
        'personal information', 'credit card', 'social security',
        'passport', 'driver license', 'authentication',
        # 한글
        '로그인', '비밀번호', '회원가입', '개인정보', '주민등록번호',
        '신용카드', '여권', '운전면허', '인증', '본인확인',
        # 포털/사내망
        'portal', 'intranet', '인트라넷', '사내망', 'vpn'
    ]
    
    # 제외할 URL 패턴 (정규식)
    EXCLUDED_URL_PATTERNS = [
        r'/login',
        r'/signin',
        r'/signup',
        r'/register',
        r'/admin',
        r'/portal',
        r'/mypage',
        r'/privacy',
        r'/personal',
        r'/auth',
        r'/password',
        r'\?(.*&)?(password|token|key|secret)=',  # 쿼리에 민감정보
        r'/download/.*\.(exe|zip|rar)',  # 실행파일 다운로드
    ]
    
    # 제외할 콘텐츠 타입
    EXCLUDED_CONTENT_TYPES = [
        'application/octet-stream',
        'application/zip',
        'application/x-msdownload',
        'video/',
        'audio/'
    ]
    
    def should_exclude_url(self, url: str) -> Tuple[bool, str]:
        """
        URL이 색인 제외 대상인지 확인
        
        Args:
            url: 확인할 URL
            
        Returns:
            (제외 여부, 이유)
            
        예시:
            should_exclude, reason = guard.should_exclude_url(
                "https://example.com/login"
            )
            # (True, "URL 패턴 '/login' 매칭")
        """
        url_lower = url.lower()
        
        # URL 패턴 매칭
        for pattern in self.EXCLUDED_URL_PATTERNS:
            if re.search(pattern, url_lower):
                return True, f"URL 패턴 '{pattern}' 매칭"
        
        return False, ""
    
    def detect_pii_in_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        텍스트에서 PII(개인정보) 관련 내용 감지
        
        Args:
            text: 확인할 텍스트
            
        Returns:
            (PII 발견 여부, 발견된 키워드 목록)
            
        예시:
            has_pii, keywords = guard.detect_pii_in_text(
                "로그인하여 개인정보를 입력하세요"
            )
            # (True, ['로그인', '개인정보'])
        """
        text_lower = text.lower()
        found_keywords = []
        
        # 키워드 매칭
        for keyword in self.PII_KEYWORDS:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        has_pii = len(found_keywords) > 0
        return has_pii, found_keywords
    
    def detect_pii_in_html(self, html: str) -> Tuple[bool, List[str]]:
        """
        HTML에서 PII 관련 입력 폼 감지
        
        비밀번호, 이메일, 전화번호 입력 필드가 있으면 개인정보 페이지로 판단
        
        Args:
            html: HTML 소스
            
        Returns:
            (PII 발견 여부, 발견된 필드 타입 목록)
        """
        html_lower = html.lower()
        found_fields = []
        
        # 입력 필드 패턴
        pii_patterns = [
            (r'type=["\']password["\']', 'password'),
            (r'type=["\']email["\']', 'email'),
            (r'type=["\']tel["\']', 'phone'),
            (r'name=["\'].*password.*["\']', 'password'),
            (r'name=["\'].*email.*["\']', 'email'),
            (r'name=["\'].*phone.*["\']', 'phone'),
            (r'id=["\'].*password.*["\']', 'password'),
        ]
        
        for pattern, field_type in pii_patterns:
            if re.search(pattern, html_lower):
                if field_type not in found_fields:
                    found_fields.append(field_type)
        
        has_pii = len(found_fields) > 0
        return has_pii, found_fields


class QualityScorer:
    """
    청크 품질 점수 계산기 (0.0 - 1.0)
    
    낮은 품질의 청크는 검수 대상으로 표시됩니다.
    
    점수 구성:
        1. 섹션 일치도 (30%): 텍스트가 분류된 섹션과 잘 맞는가?
        2. 길이 적절성 (25%): 너무 짧거나 길지 않은가? (200-400자 최적)
        3. 언어 일관성 (25%): 한 언어로 통일되었는가?
        4. 중복 여부 (20%): 다른 청크와 겹치지 않는가?
    
    사용법:
        scorer = QualityScorer()
        report = scorer.calculate_quality(chunk, all_chunks)
        if report.needs_review:
            print(f"검수 필요: {report.reason}")
    """
    
    # 각 섹션별 기대 키워드
    SECTION_KEYWORDS = {
        'research': [
            'research', 'study', 'investigation', '연구', '학습',
            'ai', 'ml', 'deep learning', 'algorithm', '알고리즘',
            'computer vision', 'nlp', 'robotics'
        ],
        'publication': [
            'paper', 'journal', 'conference', '논문', 'publication',
            'proc', 'proceedings', 'cvpr', 'iccv', 'neurips',
            'published', '게재', 'accepted'
        ],
        'project': [
            'project', 'grant', '과제', '프로젝트', 'funded',
            'funding', '지원금', 'research grant', 'nrf'
        ],
        'people': [
            'professor', 'student', 'phd', 'master', '교수', '학생',
            '박사', '석사', '학부생', 'researcher', 'postdoc'
        ],
        'join': [
            'recruit', 'admission', 'apply', '모집', '지원', '입학',
            'application', 'deadline', '마감', 'requirement'
        ],
        'about': [
            'about', 'overview', 'introduction', '소개', '개요',
            'mission', 'vision', 'goal', '목표', 'established'
        ]
    }
    
    def calculate_quality(
        self, 
        chunk: Chunk, 
        all_chunks: List[Chunk] = None
    ) -> QualityReport:
        """
        청크의 품질 점수 계산
        
        Args:
            chunk: 평가할 청크
            all_chunks: 전체 청크 리스트 (중복 체크용, 선택)
        
        Returns:
            QualityReport 객체
            
        예시:
            report = scorer.calculate_quality(chunk)
            print(f"전체 점수: {report.overall_score:.2f}")
            print(f"검수 필요: {report.needs_review}")
        """
        # 1. 섹션 일치도 (30%)
        section_score = self._section_match_score(chunk)
        
        # 2. 길이 적절성 (25%)
        length_score = self._length_score(chunk)
        
        # 3. 언어 일관성 (25%)
        language_score = self._language_consistency_score(chunk)
        
        # 4. 중복 여부 (20%)
        if all_chunks:
            duplicate_score = self._duplicate_score(chunk, all_chunks)
        else:
            duplicate_score = 1.0
        
        # 전체 점수 계산
        overall_score = (
            section_score * 0.3 +
            length_score * 0.25 +
            language_score * 0.25 +
            duplicate_score * 0.2
        )
        
        # 검수 필요 여부 및 이유
        needs_review = overall_score < 0.5
        reason = self._get_low_score_reason(
            section_score, length_score, language_score, duplicate_score
        )
        
        return QualityReport(
            overall_score=overall_score,
            section_score=section_score,
            length_score=length_score,
            language_score=language_score,
            duplicate_score=duplicate_score,
            needs_review=needs_review,
            reason=reason if needs_review else ""
        )
    
    def _section_match_score(self, chunk: Chunk) -> float:
        """
        섹션과 텍스트 내용의 일치도
        
        섹션에 맞는 키워드가 많을수록 높은 점수
        """
        if chunk.section == 'general':
            return 0.5  # 일반 섹션은 중립 점수
        
        text_lower = chunk.text.lower()
        keywords = self.SECTION_KEYWORDS.get(chunk.section, [])
        
        if not keywords:
            return 0.5
        
        # 키워드 매칭 개수
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        
        # 매칭 비율 (최대 1.0)
        match_ratio = matches / len(keywords)
        return min(match_ratio * 2, 1.0)  # 50% 매칭이면 만점
    
    def _length_score(self, chunk: Chunk) -> float:
        """
        길이 적절성 점수
        
        200-400자가 최적 범위
        """
        char_count = chunk.char_count
        
        if 200 <= char_count <= 400:
            return 1.0  # 최적
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
        """
        언어 일관성 점수
        
        한 언어로 통일되어 있을수록 높은 점수
        (단, 혼용이 나쁜 것은 아님 - 논문 제목 등)
        """
        text = chunk.text
        
        # 한글/영문 비율 계산
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_alpha = korean_chars + english_chars
        
        if total_alpha == 0:
            return 0.5  # 문자가 없으면 중립
        
        korean_ratio = korean_chars / total_alpha
        english_ratio = english_chars / total_alpha
        
        # 한 언어가 80% 이상이면 일관성 높음
        if korean_ratio >= 0.8 or english_ratio >= 0.8:
            return 1.0  # 단일 언어 (최고)
        elif korean_ratio >= 0.6 or english_ratio >= 0.6:
            return 0.8  # 약간 섞임 (양호)
        else:
            return 0.6  # 많이 섞임 (보통 - 나쁘지 않음)
    
    def _duplicate_score(self, chunk: Chunk, all_chunks: List[Chunk]) -> float:
        """
        중복 점수 (낮을수록 중복 많음)
        
        같은 MD5 해시를 가진 청크가 많으면 점수 하락
        """
        # 같은 MD5 해시 개수 확인
        same_md5_count = sum(1 for c in all_chunks if c.md5 == chunk.md5)
        
        if same_md5_count <= 1:
            return 1.0  # 중복 없음
        elif same_md5_count == 2:
            return 0.5  # 1개 중복
        else:
            return 0.0  # 다중 중복
    
    def _get_low_score_reason(
        self, 
        section: float, 
        length: float, 
        language: float, 
        duplicate: float
    ) -> str:
        """낮은 점수의 이유 파악"""
        reasons = []
        
        if section < 0.5:
            reasons.append("섹션 불일치")
        if length < 0.5:
            reasons.append("길이 부적절")
        if language < 0.5:
            reasons.append("언어 불일관")
        if duplicate < 0.5:
            reasons.append("중복 발견")
        
        return ", ".join(reasons) if reasons else "복합 요인"


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    print("=== 가드레일 테스트 ===\n")
    
    guard = GuardRail()
    
    # 1. URL 차단 테스트
    test_urls = [
        "https://example.com/research",
        "https://example.com/login",
        "https://example.com/admin/portal",
        "https://example.com/data?password=123",
    ]
    
    for url in test_urls:
        should_exclude, reason = guard.should_exclude_url(url)
        status = "❌ 차단" if should_exclude else "✅ 허용"
        print(f"{status}: {url}")
        if should_exclude:
            print(f"   이유: {reason}")
    
    print("\n=== PII 감지 테스트 ===\n")
    
    # 2. PII 감지 테스트
    test_texts = [
        "우리 연구실은 AI를 연구합니다.",
        "로그인하여 개인정보를 입력하세요.",
        "Please sign in with your password.",
    ]
    
    for text in test_texts:
        has_pii, keywords = guard.detect_pii_in_text(text)
        status = "⚠️  PII 발견" if has_pii else "✅ 안전"
        print(f"{status}: {text}")
        if has_pii:
            print(f"   키워드: {', '.join(keywords)}")
    
    print("\n=== 품질 점수 테스트 ===\n")
    
    # 3. 품질 점수 테스트
    scorer = QualityScorer()
    
    # 테스트 청크들
    from chunking import Chunk
    
    test_chunks = [
        Chunk(
            text="우리 연구실은 컴퓨터 비전과 딥러닝을 연구합니다. " * 5,
            section="research",
            char_count=250
        ),
        Chunk(
            text="짧은 텍스트",
            section="general",
            char_count=7
        ),
        Chunk(
            text="Login to access your personal information and password settings. " * 5,
            section="about",
            char_count=330
        ),
    ]
    
    for i, chunk in enumerate(test_chunks, 1):
        report = scorer.calculate_quality(chunk)
        print(f"청크 {i}:")
        print(f"  텍스트: {chunk.text[:50]}...")
        print(f"  전체 점수: {report.overall_score:.2f}")
        print(f"  - 섹션 일치: {report.section_score:.2f}")
        print(f"  - 길이: {report.length_score:.2f}")
        print(f"  - 언어: {report.language_score:.2f}")
        print(f"  - 중복: {report.duplicate_score:.2f}")
        
        if report.needs_review:
            print(f"  ⚠️  검수 필요: {report.reason}")
        else:
            print(f"  ✅ 품질 양호")
        print()
