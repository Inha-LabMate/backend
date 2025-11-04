"""
크롤링 매니저: Playwright 기반 JavaScript 렌더링 지원

이 모듈은 Playwright를 사용하여 JavaScript가 포함된 모든 웹사이트를 크롤링합니다:
    1. JavaScript 완전 실행 (Google Sites, Wix, SPA 등 모두 지원)
    2. 자동 대기 (AJAX, 동적 콘텐츠 로딩 완료까지 기다림)
    3. 속도 제어 (서버 부담 최소화)
    4. 재시도 로직 (일시적 오류 대응)
    5. Headless 모드 (브라우저 창 안 띄움)

사용법:
    manager = CrawlManager(delay=1.0)  # 1초 딜레이
    result = manager.fetch_url("https://example.com")
    print(result.html)  # JavaScript 렌더링된 최종 HTML
"""

import time
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict
from dataclasses import dataclass
import json
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout


@dataclass
class CrawlResult:
    """
    크롤링 결과를 담는 데이터 클래스
    
    속성:
        success (bool): 크롤링 성공 여부
        status_code (int): HTTP 상태 코드 (200=성공, 404=없음, 500=서버오류 등)
        html (str): JavaScript까지 모두 실행된 최종 HTML 콘텐츠
        error (str): 에러 발생 시 에러 메시지
        cached (bool): 캐시된 데이터를 사용했는지 여부
    
    예시:
        result = CrawlResult(success=True, status_code=200, html="<html>...")
        if result.success:
            print(result.html)  # 실제 HTML 출력
    """
    success: bool          # 성공/실패 여부
    status_code: int = 0   # HTTP 상태 코드
    html: str = ""         # 렌더링된 HTML
    error: str = ""        # 에러 메시지
    cached: bool = False   # 캐시 사용 여부


@dataclass
class CrawlStats:
    """
    크롤링 통계를 추적하는 데이터 클래스
    
    속성:
        total_requests (int): 총 시도한 요청 수
        successful (int): 성공한 요청 수
        failed (int): 실패한 요청 수
        cached (int): 캐시에서 가져온 수 (네트워크 요청 안함)
        retry_count (int): 재시도한 총 횟수
        js_rendered (int): JavaScript 렌더링이 필요했던 페이지 수
    
    예시:
        stats.total_requests = 10
        stats.successful = 8
        성공률 = 8/10 = 80%
    """
    total_requests: int = 0   # 총 요청
    successful: int = 0       # 성공
    failed: int = 0           # 실패
    cached: int = 0           # 캐시 사용
    retry_count: int = 0      # 재시도
    js_rendered: int = 0      # JS 렌더링 페이지


class CrawlManager:
    """
    Playwright 기반 크롤링 관리자
    
    ✨ 핵심 기능:
        1. JavaScript 완전 실행 - Google Sites, Wix, React 등 모든 사이트 지원
        2. 자동 대기 - 페이지 로딩, AJAX 완료까지 자동 대기
        3. 속도 제어 - 서버에 부담 주지 않도록 요청 간격 조절
        4. 재시도 로직 - 일시적 오류 발생 시 자동 재시도
        5. 캐싱 - 같은 페이지 재방문 시 캐시 사용 (속도 향상)
    
    💡 사용법:
        # 1. 기본 사용 (1초 간격)
        manager = CrawlManager()
        result = manager.fetch_url("https://example.com")
        
        # 2. 빠르게 크롤링 (0.5초 간격)
        manager = CrawlManager(delay=0.5)
        
        # 3. 재시도 많이 (최대 5회)
        manager = CrawlManager(max_retries=5)
        
        # 4. 캐시 사용
        result = manager.fetch_url("https://example.com")  # 네트워크 요청
        result = manager.fetch_url("https://example.com")  # 캐시 사용 (빠름!)
    
    🔧 내부 동작:
        fetch_url() 호출
        → 캐시 확인 (있으면 바로 반환)
        → 속도 제한 적용 (너무 빠르면 대기)
        → Playwright로 브라우저 실행
        → 페이지 로딩 + JavaScript 실행 완료 대기
        → HTML 추출
        → 캐시 저장
        → 결과 반환
    """
    
    # 기본 User-Agent (우리가 누구인지 명시)
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "INHA-LabSearch-Bot/2.0 (Educational Research)"
    )
    
    def __init__(
        self,
        delay: float = 1.0,              # 요청 간 대기 시간 (초)
        max_retries: int = 3,            # 최대 재시도 횟수
        timeout: int = 30000,            # 페이지 로딩 타임아웃 (밀리초) - 30초
        user_agent: Optional[str] = None,  # 커스텀 User-Agent
        cache_dir: str = './crawl_cache',  # 캐시 저장 디렉토리
        headless: bool = True,           # Headless 모드 (브라우저 창 안 띄움)
        wait_for_network_idle: bool = True  # 네트워크 완료까지 대기
    ):
        """
        Playwright 기반 크롤링 매니저 초기화
        
        매개변수 설명:
            delay (float): 요청 간 대기 시간 (초)
                - 0.5 = 빠름 (서버 부담 약간 큼)
                - 1.0 = 권장 (안전하고 빠름)
                - 2.0 = 느림 (매우 안전)
            
            max_retries (int): 실패 시 최대 재시도 횟수
                - 3 = 권장 (대부분 충분)
                - 5 = 불안정한 서버용
            
            timeout (int): 페이지 로딩 타임아웃 (밀리초)
                - 30000 = 30초 (권장)
                - 느린 사이트는 더 늘려도 됨
            
            user_agent (str): 커스텀 User-Agent
                - None이면 기본값 사용
            
            cache_dir (str): HTML 캐시 저장 디렉토리
                - 같은 페이지 재방문 시 네트워크 요청 안함
            
            headless (bool): Headless 모드
                - True = 브라우저 창 안 보임 (권장)
                - False = 브라우저 창 보임 (디버깅용)
            
            wait_for_network_idle (bool): 네트워크 완료 대기
                - True = AJAX 등 모든 요청 완료까지 기다림 (권장)
                - False = 페이지만 로드되면 바로 진행 (빠르지만 불완전할 수 있음)
        
        초기화 과정:
            1. 설정 저장
            2. 통계 객체 생성
            3. 캐시 디렉토리 생성
            4. 기존 캐시 로드
            5. Playwright 브라우저는 필요할 때마다 실행 (효율적)
        """
        # ===== 설정 저장 =====
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.cache_dir = cache_dir
        self.headless = headless
        self.wait_for_network_idle = wait_for_network_idle
        
        # ===== 상태 추적 =====
        self.last_request_time = 0.0  # 마지막 요청 시간 (속도 제한용)
        self.stats = CrawlStats()      # 통계 객체
        
        # ===== 캐시 관리 =====
        self.http_cache: Dict[str, dict] = {}  # URL -> {html, timestamp} 매핑
        
        # 캐시 디렉토리 생성 (없으면)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 기존 캐시 로드 (이전에 크롤링한 데이터 재사용)
        self._load_cache()
    
    def fetch_url(
        self, 
        url: str,
        force_refresh: bool = False
    ) -> CrawlResult:
        """
        URL에서 HTML 가져오기 (Playwright 사용 - JavaScript 완전 실행)
        
        매개변수:
            url (str): 크롤링할 URL
                예: "https://sites.google.com/view/inha-aif-lab"
            
            force_refresh (bool): 캐시 무시 여부
                - False (기본값): 캐시 있으면 사용 (빠름)
                - True: 무조건 새로 크롤링 (최신 데이터)
        
        반환값:
            CrawlResult: 크롤링 결과 객체
                - result.success: 성공 여부 (True/False)
                - result.html: JavaScript 렌더링된 최종 HTML
                - result.error: 에러 메시지 (실패 시)
        
        동작 순서:
            1. 통계 업데이트 (total_requests += 1)
            2. 캐시 확인 (있고 force_refresh=False면 바로 반환)
            3. 속도 제한 적용 (너무 빠르면 대기)
            4. Playwright로 HTML 가져오기 (재시도 포함)
            5. 성공 시 캐시 저장
            6. 결과 반환
        
        예시:
            # 기본 사용
            result = manager.fetch_url("https://example.com")
            if result.success:
                print(result.html)  # JavaScript 실행된 HTML
            
            # 캐시 무시하고 최신 데이터 가져오기
            result = manager.fetch_url("https://example.com", force_refresh=True)
        """
        # ===== 1단계: 통계 업데이트 =====
        self.stats.total_requests += 1
        
        # ===== 2단계: 캐시 확인 =====
        if not force_refresh:
            cached_result = self._check_cache(url)
            if cached_result:
                self.stats.cached += 1
                return cached_result
        
        # ===== 3단계: 속도 제한 적용 =====
        # (마지막 요청 후 delay초 만큼 대기)
        self._apply_rate_limit()
        
        # ===== 4단계: Playwright로 크롤링 (재시도 포함) =====
        result = self._fetch_with_playwright(url)
        
        # ===== 5단계: 결과 처리 =====
        if result.success:
            # 성공: 캐시 저장 + 성공 통계 증가
            self._save_to_cache(url, result)
            self.stats.successful += 1
            self.stats.js_rendered += 1  # JavaScript 렌더링 횟수
        else:
            # 실패: 실패 통계 증가
            self.stats.failed += 1
        
        return result
    
    def _apply_rate_limit(self):
        """
        속도 제한 적용 - 서버에 부담 주지 않기
        
        동작 원리:
            - 마지막 요청 시간을 기록
            - 현재 시간과 비교
            - delay초가 안 지났으면 대기
        
        예시:
            delay = 1.0초 설정 시
            - 0초: 첫 요청 (즉시 실행)
            - 0.5초: 두 번째 요청 시도 → 0.5초 대기 후 실행
            - 2초: 세 번째 요청 (1초 지났으므로 즉시 실행)
        
        왜 필요한가?:
            - 서버 과부하 방지
            - IP 차단 방지
            - 예의 바른 크롤링
        """
        current_time = time.time()  # 현재 시간 (초 단위)
        time_since_last = current_time - self.last_request_time  # 마지막 요청 후 경과 시간
        
        # delay초가 안 지났으면 대기
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last  # 남은 대기 시간
            time.sleep(sleep_time)  # 실제 대기
        
        # 현재 시간을 마지막 요청 시간으로 업데이트
        self.last_request_time = time.time()
    
    def _fetch_with_playwright(self, url: str) -> CrawlResult:
        """
        Playwright로 HTML 가져오기 (JavaScript 완전 실행)
        
        매개변수:
            url (str): 크롤링할 URL
        
        반환값:
            CrawlResult: 크롤링 결과
        
        동작 과정:
            1. Playwright 시작 (브라우저 실행)
            2. 새 페이지 열기
            3. URL 접속
            4. JavaScript 실행 완료 대기
            5. 최종 HTML 추출
            6. 브라우저 종료
            7. 실패 시 재시도 (최대 max_retries회)
        
        재시도 로직 (지수 백오프):
            - 1회 실패: 1초 대기 후 재시도
            - 2회 실패: 2초 대기 후 재시도
            - 3회 실패: 4초 대기 후 재시도
            - 일시적 네트워크 오류 대응
        
        왜 Playwright인가?:
            - Google Sites: JavaScript로 콘텐츠 로딩 → Playwright만 가능
            - Wix: 동적 렌더링 → Playwright만 가능
            - React/Vue SPA: 초기 HTML 거의 비어있음 → Playwright 필수
        """
        last_error = ""  # 마지막 에러 메시지 저장용
        
        # ===== 재시도 루프 =====
        for attempt in range(self.max_retries + 1):
            try:
                # ===== Playwright 실행 =====
                with sync_playwright() as p:
                    # 1. 브라우저 실행
                    #    headless=True: 창 안 띄움 (백그라운드 실행)
                    browser = p.chromium.launch(headless=self.headless)
                    
                    # 2. 브라우저 컨텍스트 생성 (쿠키, 로컬스토리지 등 격리)
                    context = browser.new_context(
                        user_agent=self.user_agent,  # User-Agent 설정
                        viewport={'width': 1920, 'height': 1080}  # 화면 크기 (반응형 대응)
                    )
                    
                    # 3. 새 페이지 열기
                    page = context.new_page()
                    
                    # 4. URL 접속 + JavaScript 실행 대기
                    #    wait_until='networkidle': 네트워크 요청 모두 완료까지 대기
                    #    timeout: 최대 대기 시간 (밀리초)
                    if self.wait_for_network_idle:
                        # 느리지만 완벽: AJAX, 이미지 등 모든 로딩 완료까지 대기
                        page.goto(url, wait_until='networkidle', timeout=self.timeout)
                    else:
                        # 빠르지만 불완전할 수 있음: DOM 로딩만 완료
                        page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                    
                    # 추가 대기: 동적 콘텐츠가 렌더링되도록 1초 더 대기
                    page.wait_for_timeout(1000)  # 1초 = 1000밀리초
                    
                    # 5. 최종 HTML 추출
                    #    이 시점에서 JavaScript가 모두 실행된 완전한 HTML
                    html = page.content()
                    
                    # 6. 브라우저 종료 (리소스 정리)
                    browser.close()
                    
                    # ===== 성공 =====
                    return CrawlResult(
                        success=True,
                        status_code=200,  # Playwright는 항상 200 (접속 성공)
                        html=html
                    )
            
            # ===== 에러 처리 =====
            except PlaywrightTimeout:
                # 타임아웃: 페이지 로딩이 너무 오래 걸림
                last_error = f"타임아웃 ({self.timeout/1000}초 초과)"
                self.stats.retry_count += 1
            
            except Exception as e:
                # 기타 에러: 네트워크 오류, DNS 실패 등
                last_error = str(e)
                self.stats.retry_count += 1
            
            # ===== 재시도 대기 (지수 백오프) =====
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # 1, 2, 4, 8초...
                time.sleep(wait_time)
        
        # ===== 모든 재시도 실패 =====
        return CrawlResult(
            success=False,
            error=f"최대 재시도 초과 ({self.max_retries}회): {last_error}"
        )
    
    def _check_cache(self, url: str) -> Optional[CrawlResult]:
        """
        캐시 확인 - 이전에 크롤링한 데이터가 있는가?
        
        매개변수:
            url (str): 확인할 URL
        
        반환값:
            CrawlResult 또는 None
                - None: 캐시 없음 → 새로 크롤링 필요
                - CrawlResult: 캐시 있음 → 네트워크 요청 안함 (빠름!)
        
        캐시 유효 기간:
            - 7일 이내: 유효 (캐시 사용)
            - 7일 초과: 만료 (새로 크롤링)
        
        왜 캐시를 사용하는가?:
            1. 속도 향상: 네트워크 요청 없이 즉시 반환
            2. 서버 부담 감소: 같은 페이지 반복 요청 안함
            3. 안정성: 네트워크 오류에 영향 안 받음
        
        예시:
            # 첫 방문: 캐시 없음
            result = manager.fetch_url("https://example.com")  # 3초 소요
            
            # 재방문: 캐시 있음
            result = manager.fetch_url("https://example.com")  # 0.001초 소요!
        """
        # URL이 캐시에 없으면 None 반환
        if url not in self.http_cache:
            return None
        
        cache_data = self.http_cache[url]
        
        # ===== 캐시 유효 기간 확인 =====
        # timestamp: 캐시 저장 시간 (ISO 형식 문자열)
        cached_time = datetime.fromisoformat(cache_data['timestamp'])
        age = datetime.now() - cached_time  # 캐시 나이
        
        # 7일 넘으면 만료
        if age > timedelta(days=7):
            return None  # 너무 오래됨 → 새로 크롤링
        
        # ===== 캐시 유효 → 반환 =====
        return CrawlResult(
            success=True,
            status_code=200,
            html=cache_data['html'],  # 저장된 HTML
            cached=True  # 캐시 사용했다고 표시
        )
    
    def _save_to_cache(self, url: str, result: CrawlResult):
        """
        캐시에 저장 - 나중에 재사용
        
        매개변수:
            url (str): URL
            result (CrawlResult): 크롤링 결과
        
        저장 내용:
            - html: JavaScript 렌더링된 최종 HTML
            - timestamp: 저장 시간 (유효 기간 계산용)
        
        디스크 저장:
            - 10개마다 자동 저장 (메모리 손실 방지)
            - JSON 파일로 저장 (./crawl_cache/http_cache.json)
        
        예시:
            캐시 파일 구조:
            {
              "https://example.com": {
                "html": "<html>...</html>",
                "timestamp": "2025-11-04T17:30:00"
              },
              "https://another.com": {
                ...
              }
            }
        """
        # ===== 메모리 캐시에 저장 =====
        self.http_cache[url] = {
            'html': result.html,            # HTML 콘텐츠
            'timestamp': datetime.now().isoformat()  # 현재 시간 (ISO 형식)
        }
        
        # ===== 주기적으로 디스크에 저장 =====
        # 10개마다 저장 (너무 자주 저장하면 느려짐)
        if len(self.http_cache) % 10 == 0:
            self._persist_cache()
    
    def _load_cache(self):
        """
        디스크에서 캐시 로드 - 이전 크롤링 데이터 재사용
        
        동작:
            1. ./crawl_cache/http_cache.json 파일 찾기
            2. JSON 파싱
            3. self.http_cache에 로드
            4. 실패 시 빈 캐시로 시작
        
        언제 호출되는가?:
            - __init__() 시 자동 호출
            - 프로그램 재시작해도 이전 캐시 유지
        
        이점:
            - 프로그램 재시작해도 캐시 유지
            - 개발 중 반복 테스트 시 빠름
        """
        cache_file = os.path.join(self.cache_dir, 'http_cache.json')
        
        # 파일이 있으면 로드
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.http_cache = json.load(f)
            except Exception as e:
                # 파일 손상 등 에러 시 빈 캐시로 시작
                print(f"⚠️  캐시 로드 실패: {e}")
                self.http_cache = {}
        else:
            # 파일 없으면 빈 캐시
            self.http_cache = {}
    
    def _persist_cache(self):
        """
        캐시를 디스크에 저장 - 프로그램 종료 후에도 유지
        
        동작:
            1. self.http_cache를 JSON으로 변환
            2. ./crawl_cache/http_cache.json에 저장
            3. 실패해도 프로그램 계속 (치명적 아님)
        
        저장 시점:
            - 10개마다 자동 (_save_to_cache에서 호출)
            - 수동으로도 호출 가능
        
        파일 형식:
            - JSON (사람이 읽기 쉬움)
            - UTF-8 인코딩 (한글 지원)
            - 들여쓰기 2칸 (가독성)
        """
        cache_file = os.path.join(self.cache_dir, 'http_cache.json')
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(
                    self.http_cache, 
                    f, 
                    ensure_ascii=False,  # 한글 그대로 저장
                    indent=2             # 들여쓰기 (예쁘게)
                )
        except Exception as e:
            # 저장 실패해도 계속 진행 (메모리에는 있음)
            print(f"⚠️  캐시 저장 실패: {e}")
    
    
    def get_stats(self) -> CrawlStats:
        """
        통계 가져오기
        
        반환값:
            CrawlStats 객체
                - total_requests: 총 요청 수
                - successful: 성공 수
                - failed: 실패 수
                - cached: 캐시 사용 수
                - retry_count: 재시도 횟수
                - js_rendered: JavaScript 렌더링 페이지 수
        
        사용 예시:
            stats = manager.get_stats()
            print(f"성공률: {stats.successful / stats.total_requests * 100}%")
        """
        return self.stats
    
    def print_stats(self):
        """
        통계 출력 - 크롤링 성과 요약
        
        출력 내용:
            - 총 요청 수
            - 성공/실패 수
            - 캐시 사용 수
            - 재시도 횟수
            - JavaScript 렌더링 페이지 수
            - 성공률 (백분율)
        
        예시 출력:
            === Playwright 크롤링 통계 ===
            총 요청: 27
            성공: 25
            실패: 2
            캐시 사용: 5
            재시도: 3
            JS 렌더링: 25
            성공률: 92.6%
        """
        print("=" * 50)
        print("=== Playwright 크롤링 통계 ===")
        print("=" * 50)
        print(f"📊 총 요청: {self.stats.total_requests}")
        print(f"✅ 성공: {self.stats.successful}")
        print(f"❌ 실패: {self.stats.failed}")
        print(f"💾 캐시 사용: {self.stats.cached}")
        print(f"🔄 재시도: {self.stats.retry_count}")
        print(f"🎭 JS 렌더링: {self.stats.js_rendered}")
        
        # 성공률 계산
        if self.stats.total_requests > 0:
            success_rate = self.stats.successful / self.stats.total_requests * 100
            print(f"📈 성공률: {success_rate:.1f}%")
        
        print("=" * 50)


# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    """
    Playwright 크롤링 매니저 테스트
    
    테스트 시나리오:
        1. 정적 HTML 사이트 (인하대 메인)
        2. JavaScript 렌더링 필요한 사이트 (연구실 홈페이지)
        3. Google Sites (가장 까다로운 케이스)
        4. 캐시 테스트 (중복 요청)
    """
    print("=" * 70)
    print("🚀 Playwright 크롤링 매니저 테스트 시작")
    print("=" * 70)
    print()
    
    # ===== 크롤링 매니저 생성 =====
    # headless=False로 하면 브라우저 창이 보임 (디버깅용)
    manager = CrawlManager(
        delay=1.0,              # 1초 간격
        max_retries=3,          # 최대 3회 재시도
        headless=True,          # 브라우저 창 안 띄움
        wait_for_network_idle=True  # 네트워크 완료까지 대기
    )
    
    # ===== 테스트 URL 목록 =====
    test_urls = [
        {
            'url': 'https://www.inha.ac.kr',
            'desc': '인하대 메인 (정적 HTML)'
        },
        {
            'url': 'https://sites.google.com/view/inha-aif-lab',
            'desc': '금융 AI 연구실 (Google Sites - JS 필수)'
        },
        {
            'url': 'https://youngsungkim-ai.github.io/',
            'desc': 'AI 연구그룹 (GitHub Pages)'
        },
        {
            'url': 'https://sites.google.com/view/inha-aif-lab',
            'desc': '금융 AI 연구실 재방문 (캐시 테스트)'
        }
    ]
    
    print(f"📋 테스트 URL: {len(test_urls)}개\n")
    
    # ===== 크롤링 시작 =====
    for i, test in enumerate(test_urls, 1):
        url = test['url']
        desc = test['desc']
        
        print(f"[{i}/{len(test_urls)}] {desc}")
        print(f"🔗 URL: {url}")
        
        # 크롤링 실행
        result = manager.fetch_url(url)
        
        # 결과 출력
        if result.success:
            status = "✅ 성공"
            if result.cached:
                status += " (캐시 사용 - 네트워크 요청 없음)"
            
            print(f"   {status}")
            print(f"   📄 HTML 길이: {len(result.html):,} 문자")
            
            # JavaScript 렌더링 확인 (Google Sites 특징)
            if 'google' in url and 'sites-canvas-main-content' in result.html:
                print(f"   🎭 JavaScript 렌더링 확인됨!")
        else:
            print(f"   ❌ 실패: {result.error}")
        
        print()
    
    # ===== 최종 통계 =====
    print()
    manager.print_stats()
    
    print()
    print("=" * 70)
    print("✨ 테스트 완료!")
    print("=" * 70)
    print()
    print("💡 다음 단계:")
    print("   1. src/main_pipeline.py 실행")
    print("   2. 27개 연구실 크롤링")
    print("   3. documents.json에서 결과 확인")
    print()


