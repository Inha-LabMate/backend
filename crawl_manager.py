"""
크롤링 매니저: 속도 제어 및 재시도 로직

이 모듈은 안전하고 예의바른 크롤링을 위한 기능을 제공합니다:
    1. User-Agent 설정
    2. 요청 속도 제한 (0.5-1 req/sec)
    3. 실패 재시도 (지수 백오프)
    4. robots.txt 준수
    5. ETag/Last-Modified 캐싱

사용법:
    manager = CrawlManager(delay=1.0)  # 1초 딜레이
    html, status = manager.fetch_url("https://example.com")
"""

import time
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import Optional, Tuple, Dict
from dataclasses import dataclass, field
import json
import os
from datetime import datetime, timedelta


@dataclass
class CrawlResult:
    """
    크롤링 결과
    
    속성:
        success: 성공 여부
        status_code: HTTP 상태 코드 (200, 404, 500 등)
        html: HTML 콘텐츠
        error: 에러 메시지
        cached: 캐시 사용 여부
        etag: ETag 헤더 값
        last_modified: Last-Modified 헤더 값
    """
    success: bool
    status_code: int = 0
    html: str = ""
    error: str = ""
    cached: bool = False
    etag: Optional[str] = None
    last_modified: Optional[str] = None


@dataclass
class CrawlStats:
    """
    크롤링 통계
    
    속성:
        total_requests: 총 요청 수
        successful: 성공 수
        failed: 실패 수
        cached: 캐시 사용 수
        retry_count: 재시도 횟수
    """
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    cached: int = 0
    retry_count: int = 0


class CrawlManager:
    """
    크롤링 관리자
    
    안전하고 효율적인 크롤링을 위한 핵심 기능:
        - 속도 제한으로 서버 부담 최소화
        - 재시도 로직으로 일시적 오류 대응
        - 캐싱으로 불필요한 요청 방지
        - robots.txt 준수로 법적 문제 예방
    
    사용법:
        # 1. 기본 사용
        manager = CrawlManager()
        result = manager.fetch_url("https://example.com")
        
        # 2. 속도 제어 (2초마다 1번 요청)
        manager = CrawlManager(delay=2.0)
        
        # 3. 재시도 설정 (최대 5회)
        manager = CrawlManager(max_retries=5)
    """
    
    # 기본 User-Agent (자신을 명확히 밝힘)
    DEFAULT_USER_AGENT = (
        "INHA-LabSearch-Bot/1.0 "
        "(Educational Research Purpose; "
        "Contact: your-email@example.com)"
    )
    
    def __init__(
        self,
        delay: float = 1.0,  # 요청 간 딜레이 (초)
        max_retries: int = 3,  # 최대 재시도 횟수
        timeout: int = 10,  # 타임아웃 (초)
        user_agent: Optional[str] = None,  # 커스텀 User-Agent
        cache_dir: str = './crawl_cache',  # 캐시 디렉토리
        respect_robots: bool = True  # robots.txt 준수 여부
    ):
        """
        크롤링 매니저 초기화
        
        Args:
            delay: 요청 간 대기 시간 (초) - 0.5~1.0 권장
            max_retries: 실패 시 최대 재시도 횟수
            timeout: HTTP 요청 타임아웃
            user_agent: 커스텀 User-Agent
            cache_dir: 캐시 저장 디렉토리
            respect_robots: robots.txt를 준수할지 여부
        """
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.cache_dir = cache_dir
        self.respect_robots = respect_robots
        
        # 마지막 요청 시간 (속도 제한용)
        self.last_request_time = 0.0
        
        # 통계
        self.stats = CrawlStats()
        
        # robots.txt 파서 캐시
        self.robots_parsers: Dict[str, RobotFileParser] = {}
        
        # HTTP 캐시 (ETag, Last-Modified)
        self.http_cache: Dict[str, dict] = {}
        
        # 캐시 디렉토리 생성
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 캐시 로드
        self._load_cache()
    
    def fetch_url(
        self, 
        url: str,
        force_refresh: bool = False
    ) -> CrawlResult:
        """
        URL에서 HTML 가져오기
        
        Args:
            url: 크롤링할 URL
            force_refresh: True면 캐시 무시하고 새로 가져옴
        
        Returns:
            CrawlResult 객체
            
        동작 흐름:
            1. robots.txt 확인
            2. 캐시 확인 (ETag/Last-Modified)
            3. 속도 제한 적용
            4. HTTP 요청 (실패 시 재시도)
            5. 캐시 저장
        """
        self.stats.total_requests += 1
        
        # 1. robots.txt 확인
        if self.respect_robots and not self._can_fetch(url):
            self.stats.failed += 1
            return CrawlResult(
                success=False,
                error="robots.txt에 의해 차단됨"
            )
        
        # 2. 캐시 확인
        if not force_refresh:
            cached_result = self._check_cache(url)
            if cached_result:
                self.stats.cached += 1
                return cached_result
        
        # 3. 속도 제한
        self._apply_rate_limit()
        
        # 4. HTTP 요청 (재시도 포함)
        result = self._fetch_with_retry(url)
        
        # 5. 캐시 저장
        if result.success:
            self._save_to_cache(url, result)
            self.stats.successful += 1
        else:
            self.stats.failed += 1
        
        return result
    
    def _can_fetch(self, url: str) -> bool:
        """
        robots.txt 확인 - 이 URL을 크롤링해도 되는가?
        
        Args:
            url: 확인할 URL
        
        Returns:
            크롤링 가능 여부
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # 도메인별 robots.txt 파서 캐시
        if base_url not in self.robots_parsers:
            parser = RobotFileParser()
            robots_url = urljoin(base_url, "/robots.txt")
            
            try:
                parser.set_url(robots_url)
                parser.read()
                self.robots_parsers[base_url] = parser
            except:
                # robots.txt 읽기 실패 시 허용으로 간주
                return True
        
        parser = self.robots_parsers[base_url]
        return parser.can_fetch(self.user_agent, url)
    
    def _apply_rate_limit(self):
        """
        속도 제한 적용 - 너무 빠른 요청 방지
        
        마지막 요청 후 설정된 delay(초)만큼 대기
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _fetch_with_retry(self, url: str) -> CrawlResult:
        """
        재시도 로직이 포함된 HTTP 요청
        
        지수 백오프(Exponential Backoff):
            1회: 1초 대기
            2회: 2초 대기
            3회: 4초 대기
            ...
        
        Args:
            url: 요청할 URL
        
        Returns:
            CrawlResult
        """
        headers = {
            'User-Agent': self.user_agent
        }
        
        # 캐시된 ETag/Last-Modified 사용
        if url in self.http_cache:
            cache_data = self.http_cache[url]
            if cache_data.get('etag'):
                headers['If-None-Match'] = cache_data['etag']
            if cache_data.get('last_modified'):
                headers['If-Modified-Since'] = cache_data['last_modified']
        
        last_error = ""
        
        # 재시도 루프
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # 304 Not Modified - 캐시 사용
                if response.status_code == 304:
                    cached_html = self.http_cache[url].get('html', '')
                    return CrawlResult(
                        success=True,
                        status_code=304,
                        html=cached_html,
                        cached=True
                    )
                
                # 성공
                if response.status_code == 200:
                    return CrawlResult(
                        success=True,
                        status_code=200,
                        html=response.text,
                        etag=response.headers.get('ETag'),
                        last_modified=response.headers.get('Last-Modified')
                    )
                
                # 4xx, 5xx 에러
                return CrawlResult(
                    success=False,
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}"
                )
            
            except requests.exceptions.Timeout:
                last_error = "타임아웃"
                self.stats.retry_count += 1
            
            except requests.exceptions.ConnectionError:
                last_error = "연결 오류"
                self.stats.retry_count += 1
            
            except Exception as e:
                last_error = str(e)
                self.stats.retry_count += 1
            
            # 재시도 전 대기 (지수 백오프)
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # 1, 2, 4, 8초...
                time.sleep(wait_time)
        
        # 모든 재시도 실패
        return CrawlResult(
            success=False,
            error=f"최대 재시도 초과: {last_error}"
        )
    
    def _check_cache(self, url: str) -> Optional[CrawlResult]:
        """
        캐시 확인 - 최근에 크롤링한 적이 있는가?
        
        Args:
            url: 확인할 URL
        
        Returns:
            캐시된 결과 또는 None
        """
        if url not in self.http_cache:
            return None
        
        cache_data = self.http_cache[url]
        
        # 캐시 유효 기간 확인 (7일)
        cached_time = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cached_time > timedelta(days=7):
            return None  # 너무 오래됨
        
        return CrawlResult(
            success=True,
            status_code=200,
            html=cache_data['html'],
            cached=True,
            etag=cache_data.get('etag'),
            last_modified=cache_data.get('last_modified')
        )
    
    def _save_to_cache(self, url: str, result: CrawlResult):
        """
        캐시에 저장
        
        Args:
            url: URL
            result: 크롤링 결과
        """
        self.http_cache[url] = {
            'html': result.html,
            'etag': result.etag,
            'last_modified': result.last_modified,
            'timestamp': datetime.now().isoformat()
        }
        
        # 주기적으로 디스크에 저장
        if len(self.http_cache) % 10 == 0:
            self._persist_cache()
    
    def _load_cache(self):
        """디스크에서 캐시 로드"""
        cache_file = os.path.join(self.cache_dir, 'http_cache.json')
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.http_cache = json.load(f)
            except:
                self.http_cache = {}
    
    def _persist_cache(self):
        """캐시를 디스크에 저장"""
        cache_file = os.path.join(self.cache_dir, 'http_cache.json')
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.http_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
    
    def get_stats(self) -> CrawlStats:
        """통계 가져오기"""
        return self.stats
    
    def print_stats(self):
        """통계 출력"""
        print("=== 크롤링 통계 ===")
        print(f"총 요청: {self.stats.total_requests}")
        print(f"성공: {self.stats.successful}")
        print(f"실패: {self.stats.failed}")
        print(f"캐시 사용: {self.stats.cached}")
        print(f"재시도: {self.stats.retry_count}")
        
        if self.stats.total_requests > 0:
            success_rate = self.stats.successful / self.stats.total_requests * 100
            print(f"성공률: {success_rate:.1f}%")


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    # 크롤링 매니저 생성 (1초 딜레이)
    manager = CrawlManager(
        delay=1.0,
        max_retries=3,
        user_agent="INHA-LabSearch-Bot/1.0"
    )
    
    # 테스트 URL 목록
    test_urls = [
        "https://www.inha.ac.kr",
        "https://inhaece.co.kr/page/labs05",
        "https://httpbin.org/status/500",  # 실패 테스트
        "https://www.inha.ac.kr",  # 캐시 테스트 (중복)
    ]
    
    print("=== 크롤링 시작 ===\n")
    
    for i, url in enumerate(test_urls, 1):
        print(f"{i}. {url}")
        result = manager.fetch_url(url)
        
        if result.success:
            status = "✅ 성공"
            if result.cached:
                status += " (캐시)"
            print(f"   {status}")
            print(f"   상태 코드: {result.status_code}")
            print(f"   HTML 길이: {len(result.html)} 문자")
        else:
            print(f"   ❌ 실패: {result.error}")
        
        print()
    
    # 통계 출력
    print()
    manager.print_stats()

