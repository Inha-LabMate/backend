"""
통합 크롤링 & 임베딩 파이프라인
==============================

이 파일은 전체 시스템을 통합하여 실행합니다.

전체 흐름:
    1. 웹페이지 크롤링 (requests + BeautifulSoup)
       ↓
    2. HTML에서 본문 추출 (chunking.py)
       ↓
    3. 텍스트를 200-400자 단위로 분할 (chunking.py)
       ↓
    4. 텍스트 정규화 (text_normalization.py)
       - 언어 감지
       - 연락처 추출
       - 클린업
       ↓
    5. 임베딩 생성 (embedding.py)
       - 텍스트 → 768차원 벡터 변환
       ↓
    6. 저장 (local_storage.py 또는 vector_db.py)
       - 로컬 JSON 파일 또는 PostgreSQL

실행 방법:
    python main_pipeline.py

설정:
    - USE_LOCAL = True  → 로컬 JSON 파일 저장
    - USE_LOCAL = False → PostgreSQL 저장
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from typing import List, Dict, Optional
from datetime import datetime
import traceback

# 로컬 모듈 임포트
from chunking import DocumentProcessor, Chunk
from text_normalization import TextNormalizer
from embedding import EmbeddingPipeline

# ============================================================================
# 데이터베이스 선택 설정
# USE_LOCAL = True  → 로컬 JSON 파일 저장 (PostgreSQL 불필요)
# USE_LOCAL = False → PostgreSQL + pgvector 사용
# ============================================================================
USE_LOCAL = True  # ← 이 값을 False로 바꾸면 PostgreSQL 사용

if USE_LOCAL:
    # 로컬 파일 저장소 사용
    from local_storage import LocalVectorStore as VectorDatabase
    print("✅ 로컬 파일 저장소 모드")
else:
    # PostgreSQL 데이터베이스 사용
    from vector_db import VectorDatabase, DatabaseConfig, LabDocument
    print("✅ PostgreSQL 데이터베이스 모드")


class CrawlConfig:
    """
    크롤링 설정 클래스
    
    크롤링 동작을 제어하는 설정값들을 정의합니다.
    
    속성:
        MAX_PAGES (int): 연구실당 최대 크롤링 페이지 수
            예) 5 → 메인 페이지 + 링크된 페이지 4개
        TIMEOUT (int): HTTP 요청 타임아웃 (초)
        DELAY (int): 페이지 간 딜레이 (초)
            → 서버 부담을 줄이기 위한 대기 시간
        USER_AGENT (str): 브라우저 식별 문자열
            → 일부 사이트는 User-Agent 확인
        MIN_TEXT_LENGTH (int): 최소 텍스트 길이 (문자)
            → 이보다 짧은 청크는 버림
        MIN_QUALITY_SCORE (int): 최소 품질 점수
            → 이보다 낮은 청크는 버림
    
    사용 예:
        config = CrawlConfig()
        config.MAX_PAGES = 10  # 더 많은 페이지 크롤링
    """
    MAX_PAGES = 5  # 연구실당 최대 5페이지
    TIMEOUT = 10   # 10초 타임아웃
    DELAY = 1      # 페이지 간 1초 대기
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # 품질 기준
    MIN_TEXT_LENGTH = 100    # 최소 100자
    MIN_QUALITY_SCORE = 30   # 최소 품질 점수 30점


class LabCrawler:
    """
    연구실 크롤러
    
    하나의 연구실 웹사이트를 크롤링하고 처리합니다.
    
    처리 과정:
        1. 연구실 기본 정보 DB 저장
        2. 홈페이지 크롤링
        3. 관련 페이지 발견 (research, publication 등)
        4. 각 페이지에서 본문 추출
        5. 청킹 (200-400자 단위로 분할)
        6. 정규화 (언어 감지, 클린업)
        7. 임베딩 (텍스트 → 벡터)
        8. DB 저장
    
    주요 메서드:
        crawl_lab()       - 전체 프로세스 실행
        _discover_pages() - 관련 페이지 찾기
        _crawl_page()     - 단일 페이지 크롤링
        _process_chunk()  - 청크 처리 (정규화 + 임베딩)
    
    사용 예:
        crawler = LabCrawler(db, embedding_pipeline)
        result = crawler.crawl_lab(lab_data)
        print(f"저장된 청크: {result['chunks_saved']}개")
    """
    
    def __init__(
        self,
        db: VectorDatabase,
        embedding_pipeline: EmbeddingPipeline,
        config: CrawlConfig = CrawlConfig()
    ):
        """
        초기화
        
        Args:
            db: 데이터베이스 객체 (로컬 또는 PostgreSQL)
            embedding_pipeline: 임베딩 파이프라인
            config: 크롤링 설정
        """
        self.db = db
        self.embedding_pipeline = embedding_pipeline
        self.config = config
        
        # 하위 모듈 초기화
        self.doc_processor = DocumentProcessor()      # HTML → 청크
        self.text_normalizer = TextNormalizer()       # 텍스트 정규화
        
        self.visited_urls = set()  # 중복 방문 방지
    
    def crawl_lab(self, lab_data: Dict) -> Dict:
        """
        단일 연구실 크롤링
        
        Args:
            lab_data: 연구실 기본 정보
        
        Returns:
            크롤링 결과 통계
        """
        start_time = time.time()
        
        result = {
            'lab_id': None,
            'success': False,
            'pages_visited': 0,
            'chunks_created': 0,
            'chunks_saved': 0,
            'error': None
        }
        
        try:
            # 1. 연구실 정보 DB에 저장
            lab_id = self.db.insert_lab({
                'kor_name': lab_data.get('연구실명(한글)', ''),
                'eng_name': lab_data.get('연구실명(영문)', ''),
                'professor': lab_data.get('지도교수', ''),
                'homepage': lab_data.get('웹사이트', ''),
                'location': lab_data.get('연구실위치', ''),
                'contact_email': lab_data.get('이메일', ''),
                'contact_phone': lab_data.get('연락처', ''),
                'description': lab_data.get('연구내용', '')
            })
            
            result['lab_id'] = lab_id
            
            # 2. 웹사이트 크롤링
            homepage = lab_data.get('웹사이트', '')
            if not homepage or homepage == '해당없음':
                result['error'] = 'NO_WEBSITE'
                self.db.log_crawl(
                    lab_id=lab_id,
                    url='',
                    status='NO_WEBSITE',
                    duration=time.time() - start_time
                )
                return result
            
            # 3. 페이지 크롤링 & 청킹
            all_chunks = []
            pages = self._discover_pages(homepage)
            
            for i, page_url in enumerate(pages[:self.config.MAX_PAGES]):
                if page_url in self.visited_urls:
                    continue
                
                try:
                    chunks = self._crawl_page(page_url, lab_id, crawl_depth=i)
                    all_chunks.extend(chunks)
                    result['pages_visited'] += 1
                    
                    time.sleep(self.config.DELAY)
                except Exception as e:
                    print(f"    ⚠️  페이지 크롤링 실패: {page_url} - {e}")
            
            result['chunks_created'] = len(all_chunks)
            
            # 4. 텍스트 정규화 & 임베딩
            documents = []
            for chunk in all_chunks:
                try:
                    doc_data = self._process_chunk(chunk, lab_id)
                    if doc_data:
                        documents.append(doc_data)
                except Exception as e:
                    print(f"    ⚠️  청크 처리 실패: {e}")
            
            # 5. DB 저장
            if USE_LOCAL:
                # 로컬 저장소용
                saved_ids = self.db.insert_documents_batch(lab_id, documents)
            else:
                # PostgreSQL용 (주석처리 - 나중에 복원 가능)
                # saved_ids = self.db.insert_documents_batch(documents)
                saved_ids = []
            
            result['chunks_saved'] = len(saved_ids)
            
            # 6. 크롤링 상태 업데이트
            status = 'SUCCESS' if result['chunks_saved'] > 0 else 'NO_CONTENT'
            self.db.update_lab_crawl_status(
                lab_id=lab_id,
                status=status,
                quality_score=self._calculate_quality_score(result)
            )
            
            # 7. 로그 기록
            self.db.log_crawl(
                lab_id=lab_id,
                url=homepage,
                status=status,
                pages_visited=result['pages_visited'],
                chunks_created=result['chunks_saved'],
                duration=time.time() - start_time
            )
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
            
            if result['lab_id']:
                self.db.log_crawl(
                    lab_id=result['lab_id'],
                    url=lab_data.get('웹사이트', ''),
                    status='FAILED',
                    duration=time.time() - start_time,
                    error_message=str(e)
                )
        
        return result
    
    def _discover_pages(self, base_url: str) -> List[str]:
        """관련 페이지 발견"""
        pages = [base_url]
        
        try:
            response = requests.get(
                base_url,
                timeout=self.config.TIMEOUT,
                headers={'User-Agent': self.config.USER_AGENT},
                allow_redirects=True  # 리다이렉트 허용
            )
            response.raise_for_status()
            
            # 실제 URL (리다이렉트 후)
            actual_url = response.url
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 관련 링크 찾기
            relevant_keywords = [
                'research', 'publication', 'people', 'member', 'about',
                'project', 'lab', '연구', '논문', '구성원', '소개'
            ]
            
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '')
                text = a_tag.get_text(strip=True).lower()
                
                if any(kw in href.lower() or kw in text for kw in relevant_keywords):
                    # 절대 URL 변환
                    from urllib.parse import urljoin, urlparse
                    full_url = urljoin(actual_url, href)  # 리다이렉트된 URL 사용
                    
                    # 같은 도메인만
                    if urlparse(full_url).netloc == urlparse(actual_url).netloc:
                        # 중복 경로 확인 (예: /view/vcl-lab/view/vcl-lab)
                        parsed = urlparse(full_url)
                        path = parsed.path
                        
                        # 경로 중복 제거 (간단한 휴리스틱)
                        path_parts = [p for p in path.split('/') if p]
                        seen = set()
                        unique_parts = []
                        for part in path_parts:
                            if part not in seen or part in ['view', 'page']:  # 'view', 'page'는 중복 허용
                                unique_parts.append(part)
                                seen.add(part)
                        
                        cleaned_path = '/' + '/'.join(unique_parts)
                        cleaned_url = f"{parsed.scheme}://{parsed.netloc}{cleaned_path}"
                        
                        if cleaned_url not in pages and cleaned_url != base_url:
                            pages.append(cleaned_url)
        
        except Exception as e:
            print(f"    ⚠️  페이지 발견 실패: {e}")
        
        return pages
    
    def _crawl_page(self, url: str, lab_id: int, crawl_depth: int) -> List[Chunk]:
        """단일 페이지 크롤링"""
        self.visited_urls.add(url)
        
        try:
            # HTML 가져오기
            response = requests.get(
                url,
                timeout=self.config.TIMEOUT,
                headers={'User-Agent': self.config.USER_AGENT},
                allow_redirects=True
            )
            response.raise_for_status()
            
            # 응답 내용 확인
            if not response.text or len(response.text) < 100:
                print(f"    ⚠️  빈 응답: {url}")
                return []
            
            # 청킹
            chunks = self.doc_processor.process_html(
                html=response.text,
                url=url,
                crawl_depth=crawl_depth
            )
            
            return chunks
            
        except requests.exceptions.HTTPError as e:
            # HTTP 에러 (404, 403 등)는 조용히 처리
            if e.response.status_code in [404, 403, 410]:
                print(f"    ⚠️  페이지 없음 ({e.response.status_code}): {url}")
            else:
                print(f"    ⚠️  HTTP 에러 ({e.response.status_code}): {url}")
            return []
            
        except requests.exceptions.RequestException as e:
            # 네트워크 에러 (타임아웃, 연결 실패 등)
            print(f"    ⚠️  네트워크 에러: {url} - {str(e)}")
            return []
            
        except Exception as e:
            # 기타 에러 (파싱 에러 등)
            print(f"    ⚠️  처리 에러: {url} - {type(e).__name__}: {str(e)}")
            return []
    
    def _process_chunk(self, chunk: Chunk, lab_id: int) -> Optional[Dict]:
        """청크 처리 (정규화 + 임베딩)"""
        # 1. 텍스트 정규화
        normalized = self.text_normalizer.normalize(chunk.text)
        
        # 텍스트가 너무 짧으면 스킵
        if len(normalized.cleaned_text) < self.config.MIN_TEXT_LENGTH:
            return None
        
        # 2. 임베딩 생성
        emb_result = self.embedding_pipeline.embed(normalized.cleaned_text)
        
        # 3. 문서 데이터 생성 (Dict 형태)
        doc_data = {
            'section': chunk.section,
            'title': chunk.title,
            'text': normalized.cleaned_text,
            'lang': normalized.language,
            'tokens': normalized.tokens,
            'source_url': chunk.source_url,
            'parent_url': chunk.source_url,
            'crawl_depth': chunk.crawl_depth,
            'source_type': 'html',
            'md5': chunk.md5,
            'embedding': emb_result.embedding.tolist() if USE_LOCAL else emb_result.embedding,
            'emb_model': emb_result.model_name,
            'emb_ver': emb_result.model_version,
            'quality_score': self._calculate_chunk_quality(chunk, normalized)
        }
        
        return doc_data
    
    # ========================================================================
    # PostgreSQL용 기존 코드 (주석처리 - 나중에 복원 가능)
    # ========================================================================
    # def _process_chunk(self, chunk: Chunk, lab_id: int) -> Optional[LabDocument]:
    #     """청크 처리 (정규화 + 임베딩)"""
    #     # 1. 텍스트 정규화
    #     normalized = self.text_normalizer.normalize(chunk.text)
    #     
    #     # 텍스트가 너무 짧으면 스킵
    #     if len(normalized.cleaned_text) < self.config.MIN_TEXT_LENGTH:
    #         return None
    #     
    #     # 2. 임베딩 생성
    #     emb_result = self.embedding_pipeline.embed(normalized.cleaned_text)
    #     
    #     # 3. LabDocument 생성
    #     doc = LabDocument(
    #         lab_id=lab_id,
    #         section=chunk.section,
    #         title=chunk.title,
    #         text=normalized.cleaned_text,
    #         lang=normalized.language,
    #         tokens=normalized.tokens,
    #         source_url=chunk.source_url,
    #         parent_url=chunk.source_url,  # 일단 동일하게
    #         crawl_depth=chunk.crawl_depth,
    #         source_type='html',
    #         md5=chunk.md5,
    #         embedding=emb_result.embedding,
    #         emb_model=emb_result.model_name,
    #         emb_ver=emb_result.model_version,
    #         quality_score=self._calculate_chunk_quality(chunk, normalized)
    #     )
    #     
    #     return doc
    
    def _calculate_chunk_quality(self, chunk: Chunk, normalized) -> int:
        """청크 품질 점수 (0-100)"""
        score = 50  # 기본 점수
        
        # 텍스트 길이
        if len(normalized.cleaned_text) > 500:
            score += 20
        elif len(normalized.cleaned_text) > 300:
            score += 10
        
        # 언어 명확성
        if normalized.language in ['ko', 'en']:
            score += 15
        
        # 토큰 수
        if normalized.tokens > 100:
            score += 10
        
        # 제목 존재
        if chunk.title:
            score += 5
        
        return min(score, 100)
    
    def _calculate_quality_score(self, result: Dict) -> int:
        """전체 품질 점수"""
        score = 0
        
        if result['pages_visited'] > 0:
            score += 30
        
        if result['chunks_saved'] >= 5:
            score += 40
        elif result['chunks_saved'] >= 2:
            score += 20
        
        if result['success']:
            score += 30
        
        return min(score, 100)


class CrawlOrchestrator:
    """크롤링 오케스트레이터"""
    
    def __init__(
        self,
        db_config=None,  # None이면 로컬 저장소 사용
        embedding_model: str = 'multilingual-mpnet',
        device: str = 'cpu',
        local_data_dir: str = './crawl_data'  # 로컬 저장소 경로
    ):
        # 데이터베이스 초기화
        if USE_LOCAL:
            # 로컬 저장소 사용
            self.db = VectorDatabase(data_dir=local_data_dir)
            print(f"✅ 로컬 저장소 경로: {local_data_dir}")
        else:
            # PostgreSQL 사용 (주석처리 - 나중에 복원 가능)
            # if db_config is None:
            #     raise ValueError("PostgreSQL 모드에서는 db_config가 필요합니다")
            # self.db = VectorDatabase(db_config)
            pass
        
        # 임베딩 파이프라인 초기화
        print("임베딩 파이프라인 초기화...")
        self.embedding_pipeline = EmbeddingPipeline(
            model_name=embedding_model,
            device=device,
            use_cache=True
        )
        print(f"✅ 모델 로드 완료: {embedding_model}\n")
    
    def crawl_from_url(self, url: str) -> pd.DataFrame:
        """
        URL에서 연구실 목록 크롤링 후 각 연구실 처리
        
        Args:
            url: 연구실 목록 페이지 URL
        """
        print("="*80)
        print("1단계: 연구실 목록 크롤링")
        print("="*80)
        
        # 연구실 목록 가져오기
        response = requests.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        all_labs = soup.find_all('div', class_='labs')
        
        labs_data = []
        
        for lab_div in all_labs:
            dl = lab_div.find('dl')
            if not dl:
                continue
            
            lab_info = {
                '연구실명(한글)': '',
                '연구실명(영문)': '',
                '지도교수': '',
                '연구내용': '',
                '연구실위치': '',
                '연락처': '',
                '이메일': '',
                '웹사이트': ''
            }
            
            dt = dl.find('dt')
            if dt:
                dt_text = dt.get_text(strip=True)
                small = dt.find('small')
                
                if small:
                    lab_info['연구실명(영문)'] = small.get_text(strip=True)
                    lab_info['연구실명(한글)'] = dt_text.replace(
                        lab_info['연구실명(영문)'], ''
                    ).strip()
                else:
                    lab_info['연구실명(한글)'] = dt_text
            
            dds = dl.find_all('dd')
            for dd in dds:
                span = dd.find('span')
                if span:
                    field_name = span.get_text(strip=True)
                    value_text = dd.get_text(strip=True).replace(field_name, '', 1).strip()
                    
                    a_tag = dd.find('a')
                    if a_tag and a_tag.get('href'):
                        value_text = a_tag.get('href')
                    
                    if '지도교수' in field_name:
                        lab_info['지도교수'] = value_text
                    elif '연구내용' in field_name:
                        lab_info['연구내용'] = value_text
                    elif '연구실' in field_name:
                        lab_info['연구실위치'] = value_text
                    elif '연락처' in field_name:
                        lab_info['연락처'] = value_text
                    elif '이메일' in field_name:
                        lab_info['이메일'] = value_text
                    elif '웹사이트' in field_name:
                        lab_info['웹사이트'] = value_text
            
            labs_data.append(lab_info)
        
        df = pd.DataFrame(labs_data)
        print(f"✅ {len(df)}개 연구실 발견\n")
        
        # 각 연구실 크롤링
        return self.crawl_labs(df)
    
    def crawl_labs(self, labs_df: pd.DataFrame) -> pd.DataFrame:
        """
        연구실 데이터프레임 크롤링
        """
        print("="*80)
        print("2단계: 각 연구실 상세 크롤링 & 임베딩")
        print("="*80)
        
        # 결과 컬럼 추가
        labs_df['lab_id'] = None
        labs_df['pages_visited'] = 0
        labs_df['chunks_created'] = 0
        labs_df['chunks_saved'] = 0
        labs_df['crawl_status'] = ''
        labs_df['quality_score'] = 0
        labs_df['crawl_timestamp'] = ''
        labs_df['error'] = ''
        
        if USE_LOCAL:
            # 로컬 저장소 사용 (with 문 불필요)
            crawler = LabCrawler(self.db, self.embedding_pipeline)
            
            for idx, row in labs_df.iterrows():
                print(f"\n{'='*80}")
                print(f"[{idx+1}/{len(labs_df)}] {row['연구실명(한글)']}")
                print(f"{'='*80}")
                
                result = crawler.crawl_lab(row.to_dict())
                
                # 결과 기록
                labs_df.at[idx, 'lab_id'] = result['lab_id']
                labs_df.at[idx, 'pages_visited'] = result['pages_visited']
                labs_df.at[idx, 'chunks_created'] = result['chunks_created']
                labs_df.at[idx, 'chunks_saved'] = result['chunks_saved']
                labs_df.at[idx, 'crawl_status'] = 'SUCCESS' if result['success'] else 'FAILED'
                labs_df.at[idx, 'crawl_timestamp'] = datetime.now().isoformat()
                
                if result['error']:
                    labs_df.at[idx, 'error'] = result['error']
                
                # 출력
                print(f"  결과:")
                print(f"    - Lab ID: {result['lab_id']}")
                print(f"    - 방문 페이지: {result['pages_visited']}")
                print(f"    - 생성 청크: {result['chunks_created']}")
                print(f"    - 저장 청크: {result['chunks_saved']}")
                print(f"    - 상태: {labs_df.at[idx, 'crawl_status']}")
                
                if result['error']:
                    print(f"    - 오류: {result['error']}")
        
        else:
            # PostgreSQL 사용 (주석처리 - 나중에 복원 가능)
            # with VectorDatabase(self.db_config) as db:
            #     crawler = LabCrawler(db, self.embedding_pipeline)
            #     
            #     for idx, row in labs_df.iterrows():
            #         ... (기존 코드와 동일)
            pass
        
        return labs_df
    
    def print_summary(self, df: pd.DataFrame):
        """결과 요약 출력"""
        print("\n" + "="*80)
        print("크롤링 결과 요약")
        print("="*80)
        
        print(f"\n📊 전체 통계:")
        print(f"  총 연구실: {len(df)}")
        print(f"  성공: {(df['crawl_status'] == 'SUCCESS').sum()}")
        print(f"  실패: {(df['crawl_status'] == 'FAILED').sum()}")
        print(f"  웹사이트 없음: {(df['error'] == 'NO_WEBSITE').sum()}")
        
        print(f"\n📄 문서 통계:")
        print(f"  총 방문 페이지: {df['pages_visited'].sum()}")
        print(f"  총 생성 청크: {df['chunks_created'].sum()}")
        print(f"  총 저장 청크: {df['chunks_saved'].sum()}")
        print(f"  평균 청크/연구실: {df['chunks_saved'].mean():.1f}")
        
        # DB 통계
        if USE_LOCAL:
            # 로컬 저장소 통계
            stats = self.db.get_stats()
            
            print(f"\n💾 로컬 저장소 통계:")
            print(f"  총 문서: {stats['total_docs']}")
            print(f"  평균 품질: {stats.get('avg_quality_score', 0):.1f}")
            
            if 'section_distribution' in stats:
                print(f"\n📂 섹션 분포:")
                for section, count in stats['section_distribution'].items():
                    print(f"    {section}: {count}")
            
            if 'language_distribution' in stats:
                print(f"\n🌐 언어 분포:")
                for lang, count in stats['language_distribution'].items():
                    print(f"    {lang}: {count}")
        
        else:
            # PostgreSQL 통계 (주석처리 - 나중에 복원 가능)
            # with VectorDatabase(self.db_config) as db:
            #     stats = db.get_stats()
            #     ... (기존 코드와 동일)
            pass


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    """메인 함수"""
    print("🚀 인하대 전기컴퓨터공학과 연구실 크롤러 v2.0")
    print("   - 청킹 & 본문 추출")
    print("   - 텍스트 정규화")
    print("   - 멀티링궐 임베딩")
    if USE_LOCAL:
        print("   - 로컬 JSON 파일 저장")
    else:
        print("   - PostgreSQL + pgvector 저장")
    print()
    
    # 오케스트레이터 초기화
    if USE_LOCAL:
        # 로컬 저장소 사용
        orchestrator = CrawlOrchestrator(
            embedding_model='multilingual-mpnet',
            device='cpu',
            local_data_dir='./crawl_data'
        )
    else:
        # PostgreSQL 사용 (주석처리 - 나중에 복원 가능)
        # db_config = DatabaseConfig(
        #     host='localhost',
        #     port=5432,
        #     database='labsearch',
        #     user='postgres',
        #     password='postgres'
        # )
        # orchestrator = CrawlOrchestrator(
        #     db_config=db_config,
        #     embedding_model='multilingual-mpnet',
        #     device='cpu'
        # )
        print("❌ PostgreSQL 모드는 주석을 해제하고 설정을 입력하세요")
        return
    
    # 크롤링 실행
    url = "https://inhaece.co.kr/page/labs05"
    df_result = orchestrator.crawl_from_url(url)
    
    # 결과 저장
    print("\n" + "="*80)
    print("결과 저장")
    print("="*80)
    
    df_result.to_csv('crawl_results.csv', index=False, encoding='utf-8-sig')
    print("✅ crawl_results.csv 저장 완료")
    
    # 요약 출력
    orchestrator.print_summary(df_result)
    
    print("\n" + "="*80)
    print("🎉 크롤링 완료!")
    print("="*80)
    
    if USE_LOCAL:
        print("\n💡 검색 테스트:")
        print("   python -c \"from local_storage import LocalVectorStore; from embedding import EmbeddingPipeline; store = LocalVectorStore('./crawl_data'); pipeline = EmbeddingPipeline(); q = pipeline.embed('컴퓨터 비전'); results = store.search_vector(q.embedding, limit=5); [print(f'{i+1}. [{r.lab_name}] {r.text[:50]}... (점수: {r.score:.3f})') for i, r in enumerate(results)]\"")
    else:
        print("\n💡 다음 단계:")
        print("   uvicorn search_api:app --reload")


if __name__ == "__main__":
    main()
