"""
텍스트 정규화 모듈
=================

이 모듈은 추출된 텍스트를 깨끗하게 정리하고 분석합니다.

주요 기능:
1. 언어 자동 감지 (한글/영문/혼합)
2. 연락처 정보 추출 (이메일, URL, 전화번호)
3. 불필요한 요소 제거 (과도한 공백, 저작권 문구 등)
4. 토큰 수 추정 (임베딩 모델용)

처리 흐름:
    원본 텍스트 
    → 연락처 추출 (이메일, URL 등)
    → 공백/특수문자 정리
    → 언어 감지
    → 토큰 수 계산
    → NormalizedText 객체 반환

예시:
    normalizer = TextNormalizer()
    result = normalizer.normalize("연구실 이메일: lab@example.com")
    print(result.language)  # 'ko'
    print(result.emails)    # ['lab@example.com']
    print(result.cleaned_text)  # 이메일이 제거된 깨끗한 텍스트
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import string


@dataclass
class NormalizedText:
    """
    정규화된 텍스트 데이터 클래스
    
    텍스트 정규화 후 결과를 담는 컨테이너입니다.
    
    속성:
        text (str): 정리된 텍스트 (연락처 포함)
        language (str): 감지된 언어
            - 'ko': 한글 (한글 비율 > 40%)
            - 'en': 영문 (영문 비율 > 60%)
            - 'mixed': 혼합 (한글+영문)
            - 'unknown': 알 수 없음
        tokens (int): 추정 토큰 수 (임베딩 모델용)
        urls (List[str]): 추출된 URL 목록
        emails (List[str]): 추출된 이메일 주소 목록
        phones (List[str]): 추출된 전화번호 목록
        cleaned_text (str): URL/이메일이 제거된 순수 텍스트
            → 검색 및 임베딩에 사용
    
    예시:
        result = NormalizedText(
            text="연구실: AI Lab, 이메일: ai@lab.com",
            language='ko',
            tokens=15,
            emails=['ai@lab.com'],
            cleaned_text="연구실: AI Lab"
        )
    """
    text: str
    language: str  # ko, en, mixed, unknown
    tokens: int
    urls: List[str]
    emails: List[str]
    phones: List[str]
    cleaned_text: str


class LanguageDetector:
    """
    언어 감지기
    
    텍스트의 언어를 자동으로 감지합니다.
    한글, 영문, 혼합을 구분할 수 있습니다.
    
    감지 기준:
        - 한글 비율 > 40% → 'ko' (한국어)
        - 영문 비율 > 60% → 'en' (영어)
        - 그 외 → 'mixed' (혼합) 또는 'unknown'
    
    사용 예:
        detector = LanguageDetector()
        lang = detector.detect_language("우리 연구실은 AI를 연구합니다")
        # → 'ko'
    """
    
    @staticmethod
    def detect_language(text: str) -> str:
        """
        언어 감지
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            'ko', 'en', 'mixed', 'unknown' 중 하나
        
        예시:
            detect_language("안녕하세요")  # → 'ko'
            detect_language("Hello world")  # → 'en'
            detect_language("Hello 안녕")  # → 'mixed'
        """
        if not text:
            return 'unknown'
        
        # 문자 유형별 카운트
        total_chars = len(text)
        korean_chars = len(re.findall(r'[가-힣]', text))  # 한글만 카운트
        english_chars = len(re.findall(r'[a-zA-Z]', text))  # 영문만 카운트
        
        # 비율 계산
        korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0
        
        # 언어 판정
        if korean_ratio > 0.4:  # 한글이 40% 이상
            return 'ko'
        elif english_ratio > 0.6:  # 영문이 60% 이상
            return 'en'
        elif korean_ratio > 0.1 or english_ratio > 0.1:  # 둘 다 조금씩
            return 'mixed'
        else:
            return 'unknown'
    
    @staticmethod
    def get_language_stats(text: str) -> Dict[str, float]:
        """언어별 통계"""
        total_chars = len(text)
        
        if total_chars == 0:
            return {'korean': 0.0, 'english': 0.0, 'other': 0.0}
        
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = total_chars - korean_chars - english_chars
        
        return {
            'korean': korean_chars / total_chars,
            'english': english_chars / total_chars,
            'other': other_chars / total_chars,
            'total_chars': total_chars
        }


class ContactExtractor:
    """연락처 정보 추출기"""
    
    # 정규식 패턴
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    URL_PATTERN = r'https?://[^\s<>"{}|\\^`\[\]]+'
    
    # 한국 전화번호 패턴
    PHONE_PATTERNS = [
        r'0\d{1,2}-\d{3,4}-\d{4}',  # 02-1234-5678
        r'0\d{9,10}',                # 0212345678
        r'\d{2,3}-\d{3,4}-\d{4}',   # 국번 포함
    ]
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """이메일 추출"""
        emails = re.findall(ContactExtractor.EMAIL_PATTERN, text)
        
        # 중복 제거 및 정리
        emails = list(set(email.lower() for email in emails))
        
        # 유효성 검증 (간단한)
        valid_emails = [
            email for email in emails
            if len(email) < 100 and '@' in email and '.' in email.split('@')[1]
        ]
        
        return valid_emails
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """URL 추출"""
        urls = re.findall(ContactExtractor.URL_PATTERN, text)
        
        # 중복 제거
        urls = list(set(urls))
        
        # URL 정리 (끝의 특수문자 제거)
        cleaned_urls = []
        for url in urls:
            url = url.rstrip('.,;:)')
            if len(url) < 500:  # 너무 긴 URL 제외
                cleaned_urls.append(url)
        
        return cleaned_urls
    
    @staticmethod
    def extract_phones(text: str) -> List[str]:
        """전화번호 추출"""
        phones = []
        
        for pattern in ContactExtractor.PHONE_PATTERNS:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # 중복 제거 및 정규화
        phones = list(set(phones))
        
        # 숫자만 추출하여 길이 검증
        valid_phones = []
        for phone in phones:
            digits = re.sub(r'\D', '', phone)
            if 9 <= len(digits) <= 11:  # 한국 전화번호 길이
                valid_phones.append(phone)
        
        return valid_phones


class TextCleaner:
    """텍스트 클리너"""
    
    # 제거할 패턴들
    COPYRIGHT_PATTERNS = [
        r'copyright\s+©?\s*\d{4}',
        r'©\s*\d{4}',
        r'all rights reserved',
        r'저작권',
    ]
    
    NAVIGATION_PATTERNS = [
        r'home\s*[|>]\s*about\s*[|>]',
        r'홈\s*[>|]\s*소개\s*[>|]',
    ]
    
    @staticmethod
    def remove_excessive_whitespace(text: str) -> str:
        """과도한 공백 제거"""
        # 연속된 공백을 하나로
        text = re.sub(r' +', ' ', text)
        
        # 연속된 줄바꿈을 최대 2개로
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 탭을 공백으로
        text = text.replace('\t', ' ')
        
        return text.strip()
    
    @staticmethod
    def remove_section_numbers(text: str) -> str:
        """
        섹션 번호 제거 (선택적)
        예: "1. 소개" → "소개"
        """
        # 줄 시작의 숫자 + 점
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # 로마 숫자
        text = re.sub(r'^[IVX]+\.\s+', '', text, flags=re.MULTILINE)
        
        return text
    
    @staticmethod
    def remove_copyright(text: str) -> str:
        """저작권 문구 제거"""
        for pattern in TextCleaner.COPYRIGHT_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def remove_navigation(text: str) -> str:
        """내비게이션 텍스트 제거"""
        for pattern in TextCleaner.NAVIGATION_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """유니코드 정규화"""
        # NFKC: 호환성 분해 후 정규 결합
        text = unicodedata.normalize('NFKC', text)
        
        return text
    
    @staticmethod
    def remove_special_chars(text: str, keep_punctuation: bool = True) -> str:
        """특수문자 제거 (선택적)"""
        if keep_punctuation:
            # 기본 구두점은 유지
            allowed = string.ascii_letters + string.digits + string.punctuation + ' \n가-힣'
        else:
            # 구두점도 제거
            allowed = string.ascii_letters + string.digits + ' \n가-힣'
        
        # 허용된 문자만 남기기
        text = ''.join(char for char in text if char in allowed or ord(char) > 127)
        
        return text
    
    @staticmethod
    def clean_all(text: str) -> str:
        """전체 클리닝 파이프라인"""
        # 1. 유니코드 정규화
        text = TextCleaner.normalize_unicode(text)
        
        # 2. 저작권 제거
        text = TextCleaner.remove_copyright(text)
        
        # 3. 내비게이션 제거
        text = TextCleaner.remove_navigation(text)
        
        # 4. 섹션 번호 제거 (선택)
        # text = TextCleaner.remove_section_numbers(text)
        
        # 5. 공백 정리
        text = TextCleaner.remove_excessive_whitespace(text)
        
        return text


class TokenCounter:
    """토큰 카운터"""
    
    @staticmethod
    def estimate_tokens(text: str, language: str = 'mixed') -> int:
        """
        토큰 수 추정
        - 한글: ~1.5 토큰/글자
        - 영문: ~0.25 토큰/단어 (4글자/단어 가정)
        - 숫자/기호: ~0.5 토큰/문자
        """
        if language == 'ko':
            # 한글 위주
            korean_chars = len(re.findall(r'[가-힣]', text))
            other_chars = len(text) - korean_chars
            return int(korean_chars * 1.5 + other_chars * 0.5)
        
        elif language == 'en':
            # 영문 위주
            words = len(re.findall(r'\b\w+\b', text))
            return int(words * 0.25)
        
        else:
            # 혼합 (정밀 계산)
            korean_chars = len(re.findall(r'[가-힣]', text))
            english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
            numbers = len(re.findall(r'\d+', text))
            
            total = int(
                korean_chars * 1.5 +
                english_words * 0.25 +
                numbers * 0.3
            )
            
            # 최소값 보장 (문자 수의 1/4)
            return max(total, len(text) // 4)
    
    @staticmethod
    def count_words(text: str) -> Dict[str, int]:
        """단어 수 세기 (언어별)"""
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        numbers = len(re.findall(r'\d+', text))
        
        return {
            'korean_chars': korean_chars,
            'english_words': english_words,
            'numbers': numbers,
            'total_chars': len(text)
        }


class TextNormalizer:
    """텍스트 정규화 통합 클래스"""
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.contact_extractor = ContactExtractor()
        self.cleaner = TextCleaner()
        self.token_counter = TokenCounter()
    
    def normalize(self, text: str, extract_contacts: bool = True) -> NormalizedText:
        """
        텍스트 정규화 파이프라인
        1. 언어 감지
        2. 연락처 추출
        3. 텍스트 클리닝
        4. 토큰 수 계산
        """
        if not text or len(text.strip()) == 0:
            return NormalizedText(
                text='',
                language='unknown',
                tokens=0,
                urls=[],
                emails=[],
                phones=[],
                cleaned_text=''
            )
        
        # 1. 연락처 추출 (원본 텍스트에서)
        urls = []
        emails = []
        phones = []
        
        if extract_contacts:
            urls = self.contact_extractor.extract_urls(text)
            emails = self.contact_extractor.extract_emails(text)
            phones = self.contact_extractor.extract_phones(text)
        
        # 2. 텍스트 클리닝
        cleaned_text = self.cleaner.clean_all(text)
        
        # 3. 연락처 제거 (검색용 순수 텍스트)
        text_without_contacts = cleaned_text
        for url in urls:
            text_without_contacts = text_without_contacts.replace(url, '')
        for email in emails:
            text_without_contacts = text_without_contacts.replace(email, '')
        
        text_without_contacts = self.cleaner.remove_excessive_whitespace(text_without_contacts)
        
        # 4. 언어 감지
        language = self.language_detector.detect_language(text_without_contacts)
        
        # 5. 토큰 수 계산
        tokens = self.token_counter.estimate_tokens(text_without_contacts, language)
        
        return NormalizedText(
            text=cleaned_text,
            language=language,
            tokens=tokens,
            urls=urls,
            emails=emails,
            phones=phones,
            cleaned_text=text_without_contacts
        )
    
    def get_language_info(self, text: str) -> Dict:
        """언어 정보 상세 분석"""
        return {
            'language': self.language_detector.detect_language(text),
            'stats': self.language_detector.get_language_stats(text),
            'word_counts': self.token_counter.count_words(text)
        }


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    normalizer = TextNormalizer()
    
    sample_texts = [
        # 한글 위주
        """
        우리 연구실은 인공지능과 컴퓨터 비전을 연구합니다.
        연락처: ai-lab@inha.ac.kr
        전화: 032-860-7000
        홈페이지: https://ailab.inha.ac.kr
        
        Copyright © 2024 AI Lab. All rights reserved.
        """,
        
        # 영문 위주
        """
        Our lab focuses on deep learning and computer vision.
        Contact: vision@example.com
        Visit our website: https://vision-lab.com
        
        1. Research Areas
        2. Publications
        3. Members
        """,
        
        # 혼합
        """
        AI Research Lab
        
        연구 분야: Machine Learning, NLP, Computer Vision
        
        Contact Information:
        - Email: contact@ailab.kr
        - Phone: 02-1234-5678
        - URL: http://ailab.kr
        """
    ]
    
    for i, text in enumerate(sample_texts):
        print(f"\n{'='*80}")
        print(f"예시 {i+1}")
        print(f"{'='*80}")
        
        result = normalizer.normalize(text)
        
        print(f"원본 텍스트 길이: {len(text)}자")
        print(f"언어: {result.language}")
        print(f"토큰 수 (추정): {result.tokens}")
        print(f"URL: {len(result.urls)}개 - {result.urls}")
        print(f"이메일: {len(result.emails)}개 - {result.emails}")
        print(f"전화: {len(result.phones)}개 - {result.phones}")
        print(f"\n정리된 텍스트:")
        print(result.cleaned_text[:200], "...")
        
        # 상세 언어 정보
        lang_info = normalizer.get_language_info(text)
        print(f"\n언어 통계:")
        for key, value in lang_info['stats'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2%}")
            else:
                print(f"  {key}: {value}")
