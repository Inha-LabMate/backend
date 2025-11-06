"""
후보군 생성 (Candidate Generation) - 1단계
학생의 희망 연구 분야를 기반으로 관련 랩실 10~20개 추출
"""

from typing import List, Dict, Set
from dataclasses import dataclass
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import json
import os
from collections import defaultdict


@dataclass
class Lab:
    """연구실 정보 데이터 클래스"""
    id: str
    name: str
    professor: str
    description: str  # labs.json의 description 필드
    homepage: str = ""
    location: str = ""
    
    # documents.json에서 섹션별로 통합된 텍스트
    research_text: str = ""  # section='research' 문서들
    about_text: str = ""     # section='about' 문서들
    project_text: str = ""   # section='project' 문서들
    
    def get_search_text(self) -> str:
        """검색용 텍스트 통합"""
        return f"{self.description} {self.about_text} {self.research_text} {self.project_text}"


@dataclass
class Student:
    """학생 정보 데이터 클래스"""
    research_interests: str  # 희망 연구 분야 (핵심!)
    

class CandidateGenerator:
    """
    키워드 검색(BM25) + 의미 검색(E5-small)을 결합하여 후보 랩실 추출
    """
    
    def __init__(
        self, 
        labs_json_path: str = "./data/crawl_data/labs.json",
        docs_json_path: str = "./data/crawl_data/documents.json",
        embedding_model_name: str = "intfloat/e5-small-v2"
    ):
        """
        Args:
            labs_json_path: labs.json 파일 경로
            docs_json_path: documents.json 파일 경로
            embedding_model_name: E5 임베딩 모델명
        """
        print("📂 데이터 로딩 중...")
        self.labs = self._load_labs_from_json(labs_json_path, docs_json_path)
        print(f"✅ {len(self.labs)}개 연구실 로드 완료")
        
        print("🤖 임베딩 모델 로딩 중...")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        print("✅ 모델 로드 완료")
        
        # BM25 인덱스 준비
        print("🔍 BM25 인덱스 준비 중...")
        self._prepare_bm25_index()
        
        # E5 임베딩 벡터 사전 계산
        print("🧠 임베딩 벡터 사전 계산 중...")
        self._prepare_embeddings()
        print("✅ 초기화 완료!\n")
    
    def _load_labs_from_json(self, labs_path: str, docs_path: str) -> List[Lab]:
        """
        labs.json과 documents.json을 읽어서 Lab 객체 리스트 생성
        """
        # labs.json 로드
        with open(labs_path, 'r', encoding='utf-8') as f:
            labs_data = json.load(f)
        
        # documents.json 로드
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
        
        # lab_id별로 문서들 그룹화
        lab_docs = defaultdict(lambda: {"research": [], "about": [], "project": []})
        
        for doc in docs_data.values():
            lab_id = str(doc['lab_id'])
            section = doc.get('section', 'general')
            text = doc.get('text', '')
            
            if section in ['research', 'about', 'project']:
                lab_docs[lab_id][section].append(text)
        
        # Lab 객체 생성
        labs = []
        for lab_id, lab_info in labs_data.items():
            lab = Lab(
                id=lab_id,
                name=lab_info.get('kor_name', ''),
                professor=lab_info.get('professor', ''),
                description=lab_info.get('description', ''),
                homepage=lab_info.get('homepage', ''),
                location=lab_info.get('location', ''),
                research_text=' '.join(lab_docs[lab_id]['research'][:3]),  # 상위 3개만
                about_text=' '.join(lab_docs[lab_id]['about'][:2]),        # 상위 2개만
                project_text=' '.join(lab_docs[lab_id]['project'][:2])     # 상위 2개만
            )
            labs.append(lab)
        
        return labs
    
    def _prepare_bm25_index(self):
        """BM25 키워드 검색을 위한 인덱스 준비"""
        corpus = [lab.get_search_text() for lab in self.labs]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
    
    def _prepare_embeddings(self):
        """E5-small 임베딩 벡터 사전 계산 및 저장"""
        lab_texts = [lab.get_search_text() for lab in self.labs]
        # E5 모델은 "query: " 또는 "passage: " 프리픽스 필요
        lab_texts_with_prefix = [f"passage: {text}" for text in lab_texts]
        self.lab_embeddings = self.embedding_model.encode(
            lab_texts_with_prefix, 
            normalize_embeddings=True,
            show_progress_bar=True
        )
    
    def _keyword_search(self, query: str, top_k: int = 10) -> List[str]:
        """
        키워드 매칭 (BM25) - 정확성(Precision) 담당
        
        Args:
            query: 학생의 희망 연구 분야
            top_k: 상위 k개 추출
            
        Returns:
            랩실 ID 리스트
        """
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # 상위 k개 인덱스 추출
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        return [self.labs[idx].id for idx in top_indices]
    
    def _semantic_search(self, query: str, top_k: int = 10) -> List[str]:
        """
        E5-small 임베딩 벡터 검색 - 발견(Recall) 담당
        
        Args:
            query: 학생의 희망 연구 분야
            top_k: 상위 k개 추출
            
        Returns:
            랩실 ID 리스트
        """
        # E5 쿼리 인코딩
        query_with_prefix = f"query: {query}"
        query_embedding = self.embedding_model.encode(
            query_with_prefix,
            normalize_embeddings=True
        )
        
        # 코사인 유사도 계산 (정규화된 벡터이므로 내적으로 계산 가능)
        similarities = np.dot(self.lab_embeddings, query_embedding)
        
        # 상위 k개 인덱스 추출
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [self.labs[idx].id for idx in top_indices]
    
    def generate_candidates(
        self, 
        student: Student, 
        keyword_top_k: int = 10,
        semantic_top_k: int = 10
    ) -> List[str]:
        """
        후보군 생성 메인 함수
        키워드 검색 + 의미 검색 결과를 합침 (Union)
        
        Args:
            student: 학생 정보
            keyword_top_k: 키워드 검색 상위 k개
            semantic_top_k: 의미 검색 상위 k개
            
        Returns:
            최종 후보 랩실 ID 리스트 (10~20개, 중복 제거됨)
        """
        query = student.research_interests
        
        # 1. 키워드 검색 Top K
        keyword_results = self._keyword_search(query, keyword_top_k)
        
        # 2. 의미 검색 Top K
        semantic_results = self._semantic_search(query, semantic_top_k)
        
        # 3. 합집합 (중복 제거)
        candidates = list(set(keyword_results + semantic_results))
        
        print(f"🔍 키워드 검색: {len(keyword_results)}개")
        print(f"🔎 의미 검색: {len(semantic_results)}개")
        print(f"✅ 최종 후보: {len(candidates)}개")
        
        return candidates
    
    def get_candidates_with_scores(
        self,
        student: Student,
        keyword_top_k: int = 10,
        semantic_top_k: int = 10
    ) -> Dict[str, Dict]:
        """
        후보군과 함께 각 검색 방식의 점수도 반환
        
        Returns:
            {lab_id: {"keyword_score": float, "semantic_score": float, "sources": List[str]}}
        """
        query = student.research_interests
        
        # 키워드 검색
        tokenized_query = query.lower().split()
        keyword_scores = self.bm25.get_scores(tokenized_query)
        keyword_top_indices = np.argsort(keyword_scores)[-keyword_top_k:][::-1]
        
        # 의미 검색
        query_with_prefix = f"query: {query}"
        query_embedding = self.embedding_model.encode(query_with_prefix, normalize_embeddings=True)
        semantic_scores = np.dot(self.lab_embeddings, query_embedding)
        semantic_top_indices = np.argsort(semantic_scores)[-semantic_top_k:][::-1]
        
        # 결과 통합
        results = {}
        
        for idx in keyword_top_indices:
            lab_id = self.labs[idx].id
            results[lab_id] = {
                "keyword_score": float(keyword_scores[idx]),
                "semantic_score": 0.0,
                "sources": ["keyword"]
            }
        
        for idx in semantic_top_indices:
            lab_id = self.labs[idx].id
            if lab_id in results:
                results[lab_id]["semantic_score"] = float(semantic_scores[idx])
                results[lab_id]["sources"].append("semantic")
            else:
                results[lab_id] = {
                    "keyword_score": 0.0,
                    "semantic_score": float(semantic_scores[idx]),
                    "sources": ["semantic"]
                }
        
        return results


if __name__ == "__main__":
    # 실제 데이터 사용 테스트
    print("="*80)
    print("🎯 연구실 후보군 생성 시스템")
    print("="*80)
    print()
    
    # CandidateGenerator 초기화 (실제 데이터 로드)
    generator = CandidateGenerator(
        labs_json_path="./data/crawl_data/labs.json",
        docs_json_path="./data/crawl_data/documents.json"
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
        
        # 후보군 생성 (점수 포함)
        candidates_with_scores = generator.get_candidates_with_scores(
            student,
            keyword_top_k=10,
            semantic_top_k=10
        )
        
        # 점수 기준 정렬
        sorted_candidates = sorted(
            candidates_with_scores.items(),
            key=lambda x: x[1]['keyword_score'] + x[1]['semantic_score'],
            reverse=True
        )
        
        # 상위 5개 출력
        print(f"\n🏆 상위 5개 후보 연구실:\n")
        for rank, (lab_id, scores) in enumerate(sorted_candidates[:5], 1):
            lab = next(lab for lab in generator.labs if lab.id == lab_id)
            total_score = scores['keyword_score'] + scores['semantic_score']
            sources = ', '.join(scores['sources'])
            
            print(f"{rank}. [{lab.professor}] {lab.name}")
            print(f"   총점: {total_score:.4f} (키워드: {scores['keyword_score']:.4f}, 의미: {scores['semantic_score']:.4f})")
            print(f"   매칭: {sources}")
            print(f"   설명: {lab.description[:100]}...")
            print()
    
    print("="*80)
    print("✅ 테스트 완료!")
    print("="*80)