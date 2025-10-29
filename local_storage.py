"""
로컬 파일 기반 벡터 저장소 (PostgreSQL 없이 사용)
================================================

PostgreSQL 대신 JSON 파일로 데이터를 저장하고 검색합니다.

장점:
    - 데이터베이스 설치 불필요
    - 설정이 간단함
    - 파일로 저장되어 백업이 쉬움
    - 작은 규모 프로젝트에 적합

단점:
    - 대용량 데이터에는 느릴 수 있음
    - 동시 접속 처리 어려움
    - PostgreSQL의 고급 기능 사용 불가

파일 구조:
    ./crawl_data/
    ├── labs.json           # 연구실 기본 정보
    ├── documents.json      # 문서 + 임베딩 벡터
    └── stats.json          # 통계 정보

주요 기능:
1. 연구실 정보 저장/조회
2. 문서 저장 (텍스트 + 768차원 임베딩 벡터)
3. 벡터 검색 (코사인 유사도)
4. 중복 체크 (MD5 해시)

사용 예:
    store = LocalVectorStore('./crawl_data')
    lab_id = store.insert_lab({'kor_name': 'AI 연구실', ...})
    doc_id = store.insert_document(lab_id, {...})
    results = store.search_vector(query_embedding, limit=5)
"""

import json
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import os
from datetime import datetime


@dataclass
class LocalDocument:
    """
    로컬 문서 데이터 클래스
    
    하나의 문서(청크)를 나타냅니다.
    PostgreSQL의 lab_docs 테이블과 동일한 구조입니다.
    
    속성:
        doc_id (int): 문서 고유 ID
        lab_id (int): 소속 연구실 ID
        lab_name (str): 연구실 이름 (검색 결과 표시용)
        section (str): 섹션 종류 (about, research, publication 등)
        title (str): 문서 제목
        text (str): 실제 텍스트 내용
        lang (str): 언어 (ko, en, mixed)
        tokens (int): 토큰 수
        source_url (str): 출처 URL
        md5 (str): 텍스트 MD5 해시 (중복 체크용)
        embedding (List[float]): 임베딩 벡터 (768개 숫자)
            ※ JSON 저장을 위해 리스트로 저장
        emb_model (str): 임베딩 모델 이름
        emb_ver (int): 임베딩 버전
        quality_score (int): 품질 점수 (0-100)
        created_at (str): 생성 시각
    """
    doc_id: int
    lab_id: int
    lab_name: str
    section: str
    title: Optional[str]
    text: str
    lang: str
    tokens: int
    source_url: str
    md5: str
    embedding: List[float]  # numpy array를 list로 저장 (JSON 호환성)
    emb_model: str
    emb_ver: int
    quality_score: int
    created_at: str


@dataclass
class LocalLab:
    """로컬 연구실 데이터"""
    lab_id: int
    kor_name: str
    eng_name: Optional[str]
    professor: Optional[str]
    homepage: Optional[str]
    location: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    description: Optional[str]


@dataclass
class SearchResult:
    """검색 결과"""
    doc_id: int
    lab_id: int
    lab_name: str
    section: str
    title: Optional[str]
    text: str
    score: float


class LocalVectorStore:
    """
    로컬 벡터 저장소
    
    JSON 파일을 사용하여 데이터를 저장하고 검색합니다.
    PostgreSQL의 VectorDatabase와 동일한 인터페이스를 제공합니다.
    
    파일 구조:
        data_dir/
        ├── labs.json        - 연구실 정보
        ├── documents.json   - 문서 + 임베딩
        └── stats.json       - 통계 (ID 카운터 등)
    
    주요 메서드:
        insert_lab()         - 연구실 추가
        insert_document()    - 문서 추가
        search_vector()      - 벡터 검색
        get_stats()          - 통계 조회
    
    사용 예:
        store = LocalVectorStore('./data')
        lab_id = store.insert_lab({...})
        doc_id = store.insert_document(lab_id, {...})
        results = store.search_vector(query_vec, limit=5)
    """
    
    def __init__(self, data_dir: str = './local_data'):
        """
        초기화
        
        Args:
            data_dir: 데이터를 저장할 디렉토리 경로
                기본값은 './local_data'
        
        동작:
            1. 디렉토리가 없으면 자동 생성
            2. 기존 데이터가 있으면 로드
            3. 없으면 빈 상태로 시작
        """
        self.data_dir = data_dir
        self.labs_file = os.path.join(data_dir, 'labs.json')
        self.docs_file = os.path.join(data_dir, 'documents.json')
        self.stats_file = os.path.join(data_dir, 'stats.json')
        
        # 디렉토리 생성 (없으면)
        os.makedirs(data_dir, exist_ok=True)
        
        # 기존 데이터 로드
        self.labs = self._load_labs()        # {lab_id: LocalLab}
        self.documents = self._load_documents()  # {doc_id: LocalDocument}
        self.stats = self._load_stats()      # {total_labs, total_docs, ...}
    
    def _load_labs(self) -> Dict[int, LocalLab]:
        """연구실 데이터 로드"""
        if not os.path.exists(self.labs_file):
            return {}
        
        with open(self.labs_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {int(k): LocalLab(**v) for k, v in data.items()}
    
    def _load_documents(self) -> Dict[int, LocalDocument]:
        """문서 데이터 로드"""
        if not os.path.exists(self.docs_file):
            return {}
        
        with open(self.docs_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {int(k): LocalDocument(**v) for k, v in data.items()}
    
    def _load_stats(self) -> Dict:
        """통계 데이터 로드"""
        if not os.path.exists(self.stats_file):
            return {
                'total_labs': 0,
                'total_docs': 0,
                'last_lab_id': 0,
                'last_doc_id': 0
            }
        
        with open(self.stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_labs(self):
        """연구실 데이터 저장"""
        data = {k: asdict(v) for k, v in self.labs.items()}
        with open(self.labs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_documents(self):
        """문서 데이터 저장"""
        data = {k: asdict(v) for k, v in self.documents.items()}
        with open(self.docs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_stats(self):
        """통계 데이터 저장"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
    
    def insert_lab(self, lab_data: Dict) -> int:
        """연구실 추가"""
        # 중복 체크
        for lab_id, lab in self.labs.items():
            if lab.kor_name == lab_data.get('kor_name'):
                return lab_id
        
        # 새 ID 생성
        lab_id = self.stats['last_lab_id'] + 1
        
        # 연구실 생성
        lab = LocalLab(
            lab_id=lab_id,
            kor_name=lab_data.get('kor_name', ''),
            eng_name=lab_data.get('eng_name'),
            professor=lab_data.get('professor'),
            homepage=lab_data.get('homepage'),
            location=lab_data.get('location'),
            contact_email=lab_data.get('contact_email'),
            contact_phone=lab_data.get('contact_phone'),
            description=lab_data.get('description')
        )
        
        self.labs[lab_id] = lab
        self.stats['last_lab_id'] = lab_id
        self.stats['total_labs'] = len(self.labs)
        
        self._save_labs()
        self._save_stats()
        
        return lab_id
    
    def check_duplicate(self, lab_id: int, md5: str) -> bool:
        """중복 문서 체크"""
        for doc in self.documents.values():
            if doc.lab_id == lab_id and doc.md5 == md5:
                return True
        return False
    
    def insert_document(self, lab_id: int, doc_data: Dict) -> int:
        """문서 추가"""
        # 중복 체크
        md5 = doc_data.get('md5', '')
        if self.check_duplicate(lab_id, md5):
            print(f"  ⚠️  중복 문서 스킵 (MD5: {md5[:8]}...)")
            return -1
        
        # 새 ID 생성
        doc_id = self.stats['last_doc_id'] + 1
        
        # 연구실 이름 가져오기
        lab_name = self.labs[lab_id].kor_name if lab_id in self.labs else "Unknown"
        
        # 문서 생성
        doc = LocalDocument(
            doc_id=doc_id,
            lab_id=lab_id,
            lab_name=lab_name,
            section=doc_data.get('section', 'general'),
            title=doc_data.get('title'),
            text=doc_data.get('text', ''),
            lang=doc_data.get('lang', 'unknown'),
            tokens=doc_data.get('tokens', 0),
            source_url=doc_data.get('source_url', ''),
            md5=md5,
            embedding=doc_data.get('embedding', []),
            emb_model=doc_data.get('emb_model', ''),
            emb_ver=doc_data.get('emb_ver', 1),
            quality_score=doc_data.get('quality_score', 0),
            created_at=datetime.now().isoformat()
        )
        
        self.documents[doc_id] = doc
        self.stats['last_doc_id'] = doc_id
        self.stats['total_docs'] = len(self.documents)
        
        self._save_documents()
        self._save_stats()
        
        return doc_id
    
    def insert_documents_batch(self, lab_id: int, docs_data: List[Dict]) -> List[int]:
        """문서 배치 추가"""
        doc_ids = []
        
        for doc_data in docs_data:
            doc_id = self.insert_document(lab_id, doc_data)
            if doc_id > 0:
                doc_ids.append(doc_id)
        
        return doc_ids
    
    def search_vector(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        min_quality: int = 0,
        section_filter: Optional[str] = None,
        lang_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """
        벡터 검색 - 쿼리와 유사한 문서 찾기
        
        Args:
            query_embedding: 검색 쿼리의 임베딩 벡터 (768차원)
            limit: 최대 결과 개수 (기본 10개)
            min_quality: 최소 품질 점수 (0-100, 기본 0)
            section_filter: 특정 섹션만 검색 (예: 'research')
            lang_filter: 특정 언어만 검색 (예: 'ko')
        
        Returns:
            SearchResult 리스트 (유사도 높은 순으로 정렬)
        
        동작 원리:
            1. 모든 문서를 순회
            2. 필터 조건 확인 (품질, 섹션, 언어)
            3. 각 문서와 쿼리의 코사인 유사도 계산
            4. 유사도 순으로 정렬
            5. 상위 limit개 반환
        
        예시:
            query_emb = pipeline.embed("AI 연구")
            results = store.search_vector(
                query_emb.embedding, 
                limit=5, 
                min_quality=50
            )
            for r in results:
                print(f"{r.lab_name}: {r.score:.3f}")
        """
        results = []
        
        # 모든 문서를 순회하며 검색
        for doc in self.documents.values():
            # 필터 적용
            if doc.quality_score < min_quality:
                continue  # 품질 점수가 낮으면 스킵
            if section_filter and doc.section != section_filter:
                continue  # 섹션이 다르면 스킵
            if lang_filter and doc.lang != lang_filter:
                continue  # 언어가 다르면 스킵
            
            # 코사인 유사도 계산
            doc_embedding = np.array(doc.embedding)  # 리스트 → numpy 배열
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            
            # 결과 추가
            results.append(SearchResult(
                doc_id=doc.doc_id,
                lab_id=doc.lab_id,
                lab_name=doc.lab_name,
                section=doc.section,
                title=doc.title,
                text=doc.text,
                score=float(similarity)  # 유사도 점수 (0~1)
            ))
        
        # 점수 순으로 정렬 (높은 것부터)
        results.sort(key=lambda x: x.score, reverse=True)
        
        # 상위 limit개만 반환
        return results[:limit]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """코사인 유사도 계산"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def get_stats(self) -> Dict:
        """통계 정보"""
        stats = self.stats.copy()
        
        # 섹션별 분포
        section_dist = {}
        lang_dist = {}
        quality_scores = []
        
        for doc in self.documents.values():
            section_dist[doc.section] = section_dist.get(doc.section, 0) + 1
            lang_dist[doc.lang] = lang_dist.get(doc.lang, 0) + 1
            quality_scores.append(doc.quality_score)
        
        stats['section_distribution'] = section_dist
        stats['language_distribution'] = lang_dist
        stats['avg_quality_score'] = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return stats
    
    def update_lab_crawl_status(self, lab_id: int, status: str, quality_score: int = 0):
        """크롤링 상태 업데이트 (로컬에서는 아무것도 하지 않음)"""
        pass
    
    def log_crawl(self, **kwargs):
        """크롤링 로그 (로컬에서는 아무것도 하지 않음)"""
        pass
    
    def log_search(self, **kwargs):
        """검색 로그 (로컬에서는 아무것도 하지 않음)"""
        pass
    
    def close(self):
        """종료 (로컬에서는 아무것도 하지 않음)"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("로컬 벡터 저장소 테스트")
    print("="*80)
    
    # 저장소 초기화
    store = LocalVectorStore('./test_local_data')
    
    # 연구실 추가
    lab_id = store.insert_lab({
        'kor_name': 'AI 연구실',
        'eng_name': 'AI Lab',
        'professor': '홍길동',
        'homepage': 'https://ailab.example.com'
    })
    print(f"\n연구실 추가: ID={lab_id}")
    
    # 문서 추가 (임베딩 포함)
    from embedding import EmbeddingPipeline
    
    pipeline = EmbeddingPipeline(model_name='multilingual-mpnet', device='cpu')
    
    texts = [
        "우리 연구실은 인공지능과 머신러닝을 연구합니다.",
        "컴퓨터 비전과 이미지 처리 기술을 개발합니다.",
        "자연어 처리와 대화 시스템을 연구합니다."
    ]
    
    print("\n문서 추가 중...")
    for i, text in enumerate(texts):
        emb_result = pipeline.embed(text)
        
        doc_id = store.insert_document(lab_id, {
            'section': 'research',
            'title': f'연구 주제 {i+1}',
            'text': text,
            'lang': 'ko',
            'tokens': len(text),
            'source_url': 'https://example.com',
            'md5': f'md5_{i}',
            'embedding': emb_result.embedding.tolist(),
            'emb_model': emb_result.model_name,
            'emb_ver': emb_result.model_version,
            'quality_score': 80
        })
        print(f"  문서 {i+1} 추가: ID={doc_id}")
    
    # 검색 테스트
    print("\n검색 테스트:")
    query = "딥러닝과 neural network"
    query_emb = pipeline.embed(query)
    
    results = store.search_vector(query_emb.embedding, limit=3)
    
    print(f"\n쿼리: '{query}'")
    for i, result in enumerate(results):
        print(f"\n{i+1}. [{result.lab_name}] {result.title}")
        print(f"   점수: {result.score:.3f}")
        print(f"   텍스트: {result.text[:50]}...")
    
    # 통계
    print("\n통계:")
    stats = store.get_stats()
    print(f"  총 연구실: {stats['total_labs']}")
    print(f"  총 문서: {stats['total_docs']}")
    print(f"  평균 품질: {stats['avg_quality_score']:.1f}")
    
    print("\n✅ 테스트 완료!")
