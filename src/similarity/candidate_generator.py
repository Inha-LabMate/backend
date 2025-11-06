"""
후보군 생성 (Candidate Generation) - 1단계 [최종 개선 버전]
name + description만 사용하여 정확도 향상

주요 개선사항:
1. name + description만 사용 (노이즈 제거)
2. 모든 랩실 점수 계산 (Top-K 선택 문제 해결)
3. 도메인 키워드 사전 추가
4. 점수 정규화 및 가중치 적용
"""

from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import json
import re
from collections import defaultdict

# 🔧 도메인 키워드 사전
RESEARCH_KEYWORDS = {
    'AI/ML': {
        'terms': ['ai', '인공지능', 'artificial intelligence', 
                  'machine learning', '머신러닝', '기계학습',
                  'deep learning', '딥러닝', '심층학습',
                  'neural network', '신경망', 'deep neural'],
        'weight': 0.5
    },
    '컴퓨터비전': {
        'terms': ['computer vision', '컴퓨터 비전', '컴퓨터비전',
                  'cv', '영상처리', 'image processing', '이미지 처리',
                  'object detection', '객체 탐지', '객체 검출',
                  'image recognition', '이미지 인식', '영상 인식',
                  'visual', '비전'],
        'weight': 0.5
    },
    '로봇/자율주행': {
        'terms': ['robot', '로봇', 'robotics', '로보틱스',
                  'autonomous', '자율주행', 'self-driving', '자율 주행',
                  'slam', 'navigation', '내비게이션', 'spatial'],
        'weight': 0.5
    },
    'NLP': {
        'terms': ['nlp', 'natural language', '자연어', '자연어처리',
                  'language model', '언어 모델', 'text', '텍스트',
                  'chatbot', '챗봇', 'dialogue', '대화'],
        'weight': 0.5
    },
    '제어': {
        'terms': ['control', '제어', 'control system', '제어시스템',
                  'optimization', '최적화', 'fuzzy'],
        'weight': 0.5
    },
    '전력/에너지': {
        'terms': ['power', '전력', 'energy', '에너지',
                  'smart grid', '스마트 그리드', '스마트그리드',
                  'power system', '전력 시스템', '전력망',
                  'microgrid', '마이크로그리드'],
        'weight': 0.5
    },
    '반도체': {
        'terms': ['semiconductor', '반도체', 'device', '소자',
                  'vlsi', 'ic', 'integrated circuit', '집적회로',
                  'transistor', '트랜지스터'],
        'weight': 0.5
    },
    '통신/네트워크': {
        'terms': ['communication', '통신', 'network', '네트워크',
                  '5g', '6g', 'wireless', '무선', 'iot'],
        'weight': 0.5
    },
    '신호처리': {
        'terms': ['signal processing', '신호처리', '신호 처리',
                  'dsp', 'filtering', '필터링'],
        'weight': 0.5
    }
}


@dataclass
class Lab:
    """연구실 정보 데이터 클래스"""
    id: str
    name: str
    professor: str
    description: str
    homepage: str = ""
    location: str = ""
    
    def get_search_text(self) -> str:
        """🔧 [NEW] name + description만 사용"""
        return f"{self.name} {self.description}"


@dataclass
class Student:
    """학생 정보 데이터 클래스"""
    research_interests: str


def keyword_match_score(query: str, lab_text: str) -> float:
    """
    🔧 [NEW] 도메인 키워드 기반 매칭 점수
    
    Returns:
        0.0 ~ 1.0 점수
    """
    query_lower = query.lower()
    lab_lower = lab_text.lower()
    
    total_score = 0.0
    matched_categories = []
    
    for category, data in RESEARCH_KEYWORDS.items():
        # 쿼리에서 카테고리 키워드 확인
        query_matches = [term for term in data['terms'] if term in query_lower]
        
        if query_matches:
            # 랩실에서도 같은 카테고리 키워드 확인
            lab_matches = [term for term in data['terms'] if term in lab_lower]
            
            if lab_matches:
                # 매칭 강도 계산
                match_ratio = len(lab_matches) / len(data['terms'])
                category_score = min(match_ratio * 3, 1.0) * data['weight']
                total_score += category_score
                matched_categories.append(category)
    
    # 정규화
    if matched_categories:
        return min(total_score / len(matched_categories), 1.0)
    return 0.0


class CandidateGenerator:
    """
    키워드 검색 + 의미 검색을 결합하여 후보 랩실 추출
    [최종 개선 버전]
    """
    
    def __init__(
        self, 
        labs_json_path: str = "./data/crawl_data/labs.json",
        embedding_model_name: str = "intfloat/e5-small-v2",
        keyword_weight: float = 0.6,  # 키워드 비중 높임
        semantic_weight: float = 0.4,
        use_domain_keywords: bool = True  # 도메인 키워드 사용 여부
    ):
        """
        Args:
            labs_json_path: labs.json 파일 경로
            embedding_model_name: E5 임베딩 모델명
            keyword_weight: 키워드 검색 가중치
            semantic_weight: 의미 검색 가중치
            use_domain_keywords: 도메인 키워드 사용 여부
        """
        print("📂 데이터 로딩 중...")
        self.labs = self._load_labs_from_json(labs_json_path)
        print(f"✅ {len(self.labs)}개 연구실 로드 완료")
        
        print("🤖 임베딩 모델 로딩 중...")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        print("✅ 모델 로드 완료")
        
        # 설정
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        self.use_domain_keywords = use_domain_keywords
        print(f"⚖️  가중치 설정 - 키워드: {keyword_weight:.1f}, 의미: {semantic_weight:.1f}")
        
        if use_domain_keywords:
            print("🎯 도메인 키워드 사전 활성화")
        
        # BM25 인덱스 준비
        print("🔍 BM25 인덱스 준비 중...")
        self._prepare_bm25_index()
        
        # E5 임베딩 벡터 사전 계산
        print("🧠 임베딩 벡터 사전 계산 중...")
        self._prepare_embeddings()
        print("✅ 초기화 완료!\n")
    
    def _load_labs_from_json(self, labs_path: str) -> List[Lab]:
        """
        🔧 [SIMPLIFIED] labs.json만 로드 (documents.json 불필요)
        """
        with open(labs_path, 'r', encoding='utf-8') as f:
            labs_data = json.load(f)
        
        labs = []
        for lab_id, lab_info in labs_data.items():
            lab = Lab(
                id=lab_id,
                name=lab_info.get('kor_name', ''),
                professor=lab_info.get('professor', ''),
                description=lab_info.get('description', ''),
                homepage=lab_info.get('homepage', ''),
                location=lab_info.get('location', '')
            )
            labs.append(lab)
        
        return labs
    
    def _prepare_bm25_index(self):
        """BM25 키워드 검색을 위한 인덱스 준비"""
        corpus = [lab.get_search_text() for lab in self.labs]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
    
    def _prepare_embeddings(self):
        """E5-small 임베딩 벡터 사전 계산"""
        lab_texts = [lab.get_search_text() for lab in self.labs]
        lab_texts_with_prefix = [f"passage: {text}" for text in lab_texts]
        self.lab_embeddings = self.embedding_model.encode(
            lab_texts_with_prefix, 
            normalize_embeddings=True,
            show_progress_bar=True
        )
    
    def _normalize_keyword_scores(self, scores: np.ndarray) -> np.ndarray:
        """키워드 점수 정규화 (0~1)"""
        log_scores = np.log1p(scores)
        min_score = np.min(log_scores)
        max_score = np.max(log_scores)
        
        if max_score - min_score < 1e-8:
            return np.zeros_like(scores)
        
        normalized = (log_scores - min_score) / (max_score - min_score)
        return normalized
    
    def _rescale_semantic_scores(self, scores: np.ndarray, threshold: float = 0.65) -> np.ndarray:
        """
        🔧 [ADJUSTED] 의미 점수 재조정 (threshold 낮춤: 0.7 → 0.65)
        """
        scores_filtered = np.where(scores >= threshold, scores, 0.0)
        
        nonzero_mask = scores_filtered > 0
        if not np.any(nonzero_mask):
            return scores_filtered
        
        min_score = np.min(scores_filtered[nonzero_mask])
        max_score = np.max(scores_filtered[nonzero_mask])
        
        if max_score - min_score < 1e-8:
            scores_filtered[nonzero_mask] = 0.5
        else:
            scores_filtered[nonzero_mask] = (
                (scores_filtered[nonzero_mask] - min_score) / (max_score - min_score)
            )
        
        return scores_filtered
    
    def get_candidates_with_scores(
        self,
        student: Student,
        final_top_k: int = 15
    ) -> Dict[str, Dict]:
        """
        🔧 [IMPROVED] 모든 랩실 점수 계산 후 Top-K 선택
        
        Returns:
            {lab_id: {
                "keyword_score": float,
                "semantic_score": float,
                "domain_score": float (도메인 키워드 점수),
                "combined_score": float,
                "sources": List[str]
            }}
        """
        query = student.research_interests
        
        # ===== 1. BM25 키워드 점수 (모든 랩실) =====
        tokenized_query = query.lower().split()
        keyword_scores_raw = self.bm25.get_scores(tokenized_query)
        keyword_scores_norm = self._normalize_keyword_scores(keyword_scores_raw)
        
        # ===== 2. 의미 점수 (모든 랩실) =====
        query_with_prefix = f"query: {query}"
        query_embedding = self.embedding_model.encode(
            query_with_prefix, normalize_embeddings=True
        )
        semantic_scores_raw = np.dot(self.lab_embeddings, query_embedding)
        semantic_scores_rescaled = self._rescale_semantic_scores(semantic_scores_raw)
        
        # ===== 3. 도메인 키워드 점수 (선택적) =====
        domain_scores = np.zeros(len(self.labs))
        if self.use_domain_keywords:
            for idx, lab in enumerate(self.labs):
                lab_text = lab.get_search_text()
                domain_scores[idx] = keyword_match_score(query, lab_text)
        
        # ===== 4. Combined score 계산 =====
        results = {}
        for idx, lab in enumerate(self.labs):
            keyword_score = float(keyword_scores_norm[idx])
            semantic_score = float(semantic_scores_rescaled[idx])
            domain_score = float(domain_scores[idx])
            
            # 가중치 적용
            if self.use_domain_keywords:
                # 도메인 키워드가 있으면 BM25 대신 사용
                effective_keyword = max(keyword_score, domain_score)
            else:
                effective_keyword = keyword_score
            
            combined_score = (
                effective_keyword * self.keyword_weight +
                semantic_score * self.semantic_weight
            )
            
            # 최소 임계값 (완전히 무관한 랩실 제외)
            if combined_score > 0.05:
                results[lab.id] = {
                    "keyword_score": keyword_score,
                    "semantic_score": semantic_score,
                    "domain_score": domain_score,
                    "combined_score": combined_score,
                    "sources": []
                }
                
                if effective_keyword > 0.1:
                    results[lab.id]["sources"].append("keyword")
                if semantic_score > 0.1:
                    results[lab.id]["sources"].append("semantic")
        
        # ===== 5. Combined score 기준 Top-K 선택 =====
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1]['combined_score'],
            reverse=True
        )
        
        return dict(sorted_results[:final_top_k])


if __name__ == "__main__":
    print("="*80)
    print("🎯 연구실 후보군 생성 시스템 [최종 개선 버전]")
    print("   - name + description만 사용")
    print("   - 도메인 키워드 사전 추가")
    print("   - 모든 랩실 점수 계산")
    print("="*80)
    print()
    
    # CandidateGenerator 초기화
    generator = CandidateGenerator(
        labs_json_path="./data/crawl_data/labs.json",
        keyword_weight=0.6,
        semantic_weight=0.4,
        use_domain_keywords=True
    )
    
    # 테스트 학생 정보
    test_queries = [
        "컴퓨터 비전과 딥러닝을 활용한 이미지 인식 연구",
        "자연어처리와 대화형 AI 시스템 개발",
        "로봇 제어 및 자율주행 기술",
        "전력 시스템과 스마트 그리드",
        "무선 통신 및 5G 네트워크"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print("\n" + "="*80)
        print(f"📝 테스트 {i}: {query}")
        print("="*80)
        
        student = Student(research_interests=query)
        
        # 후보군 생성
        candidates_with_scores = generator.get_candidates_with_scores(
            student,
            final_top_k=5  # 상위 5개만
        )
        
        # 출력
        print(f"\n🏆 상위 5개 후보 연구실:\n")
        for rank, (lab_id, scores) in enumerate(candidates_with_scores.items(), 1):
            lab = next(lab for lab in generator.labs if lab.id == lab_id)
            sources = ', '.join(scores['sources']) if scores['sources'] else 'combined'
            
            print(f"{rank}. [{lab.professor}] {lab.name}")
            print(f"   총점: {scores['combined_score']:.4f}")
            print(f"   세부: 키워드={scores['keyword_score']:.4f}, "
                  f"의미={scores['semantic_score']:.4f}, "
                  f"도메인={scores['domain_score']:.4f}")
            print(f"   매칭: {sources}")
            print(f"   설명: {lab.description[:80]}...")
            print()
    
    print("="*80)
    print("✅ 테스트 완료!")
    print("="*80)