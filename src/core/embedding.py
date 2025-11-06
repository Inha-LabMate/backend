"""
임베딩 생성 모듈
===============

이 모듈은 텍스트를 벡터(숫자 배열)로 변환합니다.
벡터로 변환하면 텍스트 간의 유사도를 계산할 수 있습니다.

핵심 개념:
    임베딩(Embedding): 텍스트 → 숫자 벡터 변환
    예) "인공지능 연구" → [0.123, -0.456, 0.789, ...] (768개 숫자)
    
    비슷한 의미의 텍스트는 비슷한 벡터를 갖습니다:
    "AI 연구"와 "인공지능 연구"의 벡터는 가까움
    "AI 연구"와 "요리 레시피"의 벡터는 멀리 떨어짐

주요 기능:
1. 다국어 지원 (한글, 영어 등 50개 이상 언어)
2. 배치 처리 (여러 텍스트를 한번에)
3. 캐싱 (같은 텍스트는 재계산 안함)
4. L2 정규화 (코사인 유사도 최적화)

사용 예:
    pipeline = EmbeddingPipeline()
    result = pipeline.embed("인공지능 연구")
    print(result.embedding.shape)  # (768,)
    # → 768개의 숫자로 이루어진 벡터
"""

import numpy as np
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import hashlib
import json


@dataclass
class EmbeddingResult:
    """
    임베딩 결과 데이터 클래스
    
    텍스트를 벡터로 변환한 결과를 담습니다.
    
    속성:
        embedding (np.ndarray): 실제 벡터 (numpy 배열)
            예) array([0.123, -0.456, ...])  # 768개 숫자
        model_name (str): 사용한 모델 이름
            예) 'multilingual-mpnet'
        model_version (int): 모델 버전 (추후 모델 변경 시 구분용)
        dimension (int): 벡터 차원 (기본 768)
        normalized (bool): L2 정규화 여부
            True면 벡터 길이가 1로 정규화됨 (코사인 유사도 계산에 유리)
    
    예시:
        result = EmbeddingResult(
            embedding=np.array([0.1, 0.2, ...]),
            model_name='multilingual-mpnet',
            model_version=1,
            dimension=768,
            normalized=True
        )
    """
    embedding: np.ndarray
    model_name: str
    model_version: int
    dimension: int
    normalized: bool


class EmbeddingConfig:
    """임베딩 설정"""
    
    # 지원 모델 목록
    SUPPORTED_MODELS = {
        'multilingual-mpnet': {
            'full_name': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'dimension': 768,
            'max_seq_length': 512,
            'description': '다국어 지원 (50+ languages)'
        },
        'multilingual-e5-large': {
            'full_name': 'intfloat/multilingual-e5-large',
            'dimension': 1024,
            'max_seq_length': 512,
            'description': '고성능 다국어 모델'
        },
        'multilingual-e5-base': {
            'full_name': 'intfloat/multilingual-e5-base',
            'dimension': 768,
            'max_seq_length': 512,
            'description': '균형잡힌 다국어 모델'
        },
        'ko-sbert-multitask': {
            'full_name': 'jhgan/ko-sbert-multitask',
            'dimension': 768,
            'max_seq_length': 512,
            'description': '한국어 특화 모델'
        }
    }
    
    # 기본 설정
    DEFAULT_MODEL = 'multilingual-e5-large'
    DEFAULT_BATCH_SIZE = 32
    NORMALIZE = True  # L2 정규화 (코사인 유사도용)


class EmbeddingModel:
    """임베딩 모델 래퍼"""
    
    def __init__(
        self, 
        model_name: str = 'multilingual-e5-large',
        device: str = 'cpu',
        normalize: bool = True,
        version: int = 1
    ):
        """
        Args:
            model_name: 모델 이름 (EmbeddingConfig.SUPPORTED_MODELS 참조)
            device: 'cpu' or 'cuda'
            normalize: L2 정규화 여부
            version: 임베딩 버전 (모델 변경 시 증가)
        """
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self.version = version
        
        if model_name not in EmbeddingConfig.SUPPORTED_MODELS:
            raise ValueError(f"지원하지 않는 모델: {model_name}")
        
        self.config = EmbeddingConfig.SUPPORTED_MODELS[model_name]
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """모델 로드"""
        try:
            from sentence_transformers import SentenceTransformer
            
            print(f"임베딩 모델 로딩: {self.config['full_name']}")
            self.model = SentenceTransformer(
                self.config['full_name'],
                device=self.device
            )
            print(f"✅ 모델 로드 완료 (차원: {self.config['dimension']})")
            
        except ImportError:
            raise ImportError(
                "sentence-transformers 라이브러리가 필요합니다.\n"
                "설치: pip install sentence-transformers --break-system-packages"
            )
    
    def embed_single(self, text: str) -> EmbeddingResult:
        """단일 텍스트 임베딩"""
        embeddings = self.embed_batch([text])
        return embeddings[0]
    
    def embed_batch(
        self, 
        texts: List[str],
        batch_size: int = EmbeddingConfig.DEFAULT_BATCH_SIZE,
        show_progress: bool = False
    ) -> List[EmbeddingResult]:
        """
        배치 임베딩
        
        Args:
            texts: 텍스트 리스트
            batch_size: 배치 크기
            show_progress: 진행률 표시
        """
        if not texts:
            return []
        
        # 빈 텍스트 필터링
        valid_texts = [text if text else " " for text in texts]
        
        # 임베딩 생성
        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize
        )
        
        # EmbeddingResult 객체로 변환
        results = []
        for emb in embeddings:
            results.append(EmbeddingResult(
                embedding=emb,
                model_name=self.model_name,
                model_version=self.version,
                dimension=self.config['dimension'],
                normalized=self.normalize
            ))
        
        return results
    
    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            'model_name': self.model_name,
            'full_name': self.config['full_name'],
            'version': self.version,
            'dimension': self.config['dimension'],
            'max_seq_length': self.config['max_seq_length'],
            'normalized': self.normalize,
            'device': self.device,
            'description': self.config['description']
        }


class EmbeddingCache:
    """임베딩 캐시 (중복 계산 방지)"""
    
    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.max_size = max_size
    
    def _get_key(self, text: str, model_name: str, version: int) -> str:
        """캐시 키 생성"""
        content = f"{model_name}_{version}_{text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, model_name: str, version: int) -> Optional[np.ndarray]:
        """캐시에서 임베딩 가져오기"""
        key = self._get_key(text, model_name, version)
        return self.cache.get(key)
    
    def put(self, text: str, model_name: str, version: int, embedding: np.ndarray):
        """캐시에 임베딩 저장"""
        if len(self.cache) >= self.max_size:
            # LRU 방식으로 제거 (간단한 구현)
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        key = self._get_key(text, model_name, version)
        self.cache[key] = embedding
    
    def clear(self):
        """캐시 초기화"""
        self.cache.clear()
    
    def size(self) -> int:
        """캐시 크기"""
        return len(self.cache)


class EmbeddingPipeline:
    """임베딩 생성 파이프라인"""
    
    def __init__(
        self,
        model_name: str = 'multilingual-mpnet',
        device: str = 'cpu',
        use_cache: bool = True,
        version: int = 1
    ):
        self.model = EmbeddingModel(
            model_name=model_name,
            device=device,
            normalize=True,
            version=version
        )
        
        self.cache = EmbeddingCache() if use_cache else None
    
    def embed(
        self, 
        texts: Union[str, List[str]],
        batch_size: int = 32,
        use_cache: bool = True
    ) -> Union[EmbeddingResult, List[EmbeddingResult]]:
        """
        텍스트 임베딩 (캐시 지원)
        
        Args:
            texts: 단일 텍스트 또는 리스트
            batch_size: 배치 크기
            use_cache: 캐시 사용 여부
        """
        # 단일 텍스트 처리
        if isinstance(texts, str):
            if use_cache and self.cache:
                cached = self.cache.get(
                    texts, 
                    self.model.model_name, 
                    self.model.version
                )
                if cached is not None:
                    return EmbeddingResult(
                        embedding=cached,
                        model_name=self.model.model_name,
                        model_version=self.model.version,
                        dimension=self.model.config['dimension'],
                        normalized=self.model.normalize
                    )
            
            result = self.model.embed_single(texts)
            
            if use_cache and self.cache:
                self.cache.put(
                    texts,
                    self.model.model_name,
                    self.model.version,
                    result.embedding
                )
            
            return result
        
        # 배치 처리
        results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if use_cache and self.cache:
                cached = self.cache.get(
                    text,
                    self.model.model_name,
                    self.model.version
                )
                if cached is not None:
                    results.append(EmbeddingResult(
                        embedding=cached,
                        model_name=self.model.model_name,
                        model_version=self.model.version,
                        dimension=self.model.config['dimension'],
                        normalized=self.model.normalize
                    ))
                    continue
            
            uncached_texts.append(text)
            uncached_indices.append(i)
            results.append(None)  # placeholder
        
        # 캐시되지 않은 텍스트 임베딩
        if uncached_texts:
            new_embeddings = self.model.embed_batch(
                uncached_texts,
                batch_size=batch_size
            )
            
            # 결과 채우기
            for idx, embedding_result in zip(uncached_indices, new_embeddings):
                results[idx] = embedding_result
                
                # 캐시에 저장
                if use_cache and self.cache:
                    self.cache.put(
                        texts[idx],
                        self.model.model_name,
                        self.model.version,
                        embedding_result.embedding
                    )
        
        return results
    
    def get_info(self) -> Dict:
        """파이프라인 정보"""
        info = self.model.get_model_info()
        if self.cache:
            info['cache_size'] = self.cache.size()
        return info


# ============================================================================
# 유틸리티 함수
# ============================================================================

def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """코사인 유사도 계산"""
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2 정규화"""
    norm = np.linalg.norm(embedding)
    if norm > 0:
        return embedding / norm
    return embedding


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    """임베딩을 bytes로 변환 (DB 저장용)"""
    return embedding.tobytes()


def bytes_to_embedding(data: bytes, dtype=np.float32) -> np.ndarray:
    """bytes를 임베딩으로 변환"""
    return np.frombuffer(data, dtype=dtype)


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("임베딩 파이프라인 테스트")
    print("="*80)
    
    # 파이프라인 초기화
    print("\n1. 파이프라인 초기화")
    pipeline = EmbeddingPipeline(
        model_name='multilingual-mpnet',
        device='cpu',
        use_cache=True,
        version=1
    )
    
    info = pipeline.get_info()
    print(f"모델: {info['full_name']}")
    print(f"차원: {info['dimension']}")
    print(f"버전: {info['version']}")
    
    # 단일 텍스트 임베딩
    print("\n2. 단일 텍스트 임베딩")
    text = "우리 연구실은 인공지능과 컴퓨터 비전을 연구합니다."
    result = pipeline.embed(text)
    print(f"텍스트: {text}")
    print(f"임베딩 shape: {result.embedding.shape}")
    print(f"임베딩 norm: {np.linalg.norm(result.embedding):.4f}")
    print(f"정규화 여부: {result.normalized}")
    
    # 배치 임베딩
    print("\n3. 배치 임베딩")
    texts = [
        "딥러닝과 머신러닝 연구",
        "컴퓨터 비전과 이미지 처리",
        "자연어 처리와 대화 시스템",
        "Deep learning and neural networks",
        "Computer vision and image recognition"
    ]
    
    results = pipeline.embed(texts, batch_size=8)
    print(f"총 {len(results)}개 임베딩 생성")
    
    # 유사도 계산
    print("\n4. 유사도 계산")
    for i in range(len(results)):
        for j in range(i+1, len(results)):
            sim = cosine_similarity(results[i].embedding, results[j].embedding)
            print(f"'{texts[i][:20]}...' <-> '{texts[j][:20]}...': {sim:.4f}")
    
    # 캐시 효과 테스트
    print("\n5. 캐시 테스트")
    import time
    
    # 첫 번째 실행
    start = time.time()
    _ = pipeline.embed(texts[:3])
    first_time = time.time() - start
    
    # 두 번째 실행 (캐시 사용)
    start = time.time()
    _ = pipeline.embed(texts[:3])
    cached_time = time.time() - start
    
    print(f"첫 실행: {first_time:.4f}초")
    print(f"캐시 실행: {cached_time:.4f}초")
    print(f"속도 향상: {first_time/cached_time:.1f}x")
    print(f"캐시 크기: {pipeline.cache.size()}")
    
    print("\n" + "="*80)
    print("테스트 완료!")
    print("="*80)
