"""
개별 모듈 테스트용 스크립트
"""

import sys
from pathlib import Path

# src 경로 추가
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

print("="*80)
print("🧪 Scorer 모듈 테스트")
print("="*80)

# Config 테스트
print("\n1️⃣ Config 모듈 테스트")
from similarity.config import ScorerConfig, DEFAULT_CONFIG, RESEARCH_CONFIG

config = ScorerConfig.create_default()
print(f"✅ 기본 설정 로드 완료")
print(f"   대분류 가중치: 문장={config.sentence_weight}, "
      f"키워드={config.keyword_weight}, 정량={config.numeric_weight}")

config.validate()
print("✅ 설정 유효성 검증 통과")

# Scorer 테스트
print("\n2️⃣ Scorer 모듈 테스트")
from similarity.scorer import RerankingScorer, StudentProfile
from similarity.candidate_generator import Lab

print("스코어러 초기화 중...")
scorer = RerankingScorer(DEFAULT_CONFIG)

# 테스트용 학생 프로필
student = StudentProfile(
    intro1="컴퓨터 비전과 딥러닝 연구에 관심이 있습니다",
    intro2="Python, PyTorch를 사용한 프로젝트 경험이 있습니다",
    intro3="Vision Transformer 연구를 하고 싶습니다",
    portfolio="YOLO, GAN, Transformer 프로젝트 경험",
    major="컴퓨터공학",
    certifications="정보처리기사",
    awards="AI 해커톤 우수상",
    tech_stack="Python, PyTorch, TensorFlow",
    toeic_score="850",
    english_proficiency="상",
    gpa="4.0"
)

# 테스트용 연구실
lab = Lab(
    id="TEST001",
    name="컴퓨터비전 연구실",
    professor="테스트교수",
    description="딥러닝 기반 컴퓨터 비전 연구",
    department="컴퓨터공학",
    sections={
        "research": "딥러닝 기반 컴퓨터 비전 연구",
        "about": "Vision Transformer 연구",
        "methods": "PyTorch, TensorFlow 활용",
        "projects": "YOLO, GAN 프로젝트",
    }
)

print(f"\n3️⃣ 연구실 점수 계산: {lab.name}")
score = scorer.score_lab(student, lab)

print(f"\n📊 결과:")
print(f"최종 점수: {score.final_score:.4f}")
print(f"  - 문장형: {score.sentence_score:.4f}")
print(f"    · intro1: {score.intro1_score:.4f}")
print(f"    · intro2: {score.intro2_score:.4f}")
print(f"    · intro3: {score.intro3_score:.4f}")
print(f"    · portfolio: {score.portfolio_score:.4f}")
print(f"  - 키워드형: {score.keyword_score:.4f}")
print(f"    · major: {score.major_score:.4f}")
print(f"    · certification: {score.certification_score:.4f}")
print(f"    · award: {score.award_score:.4f}")
print(f"    · tech_stack: {score.tech_stack_score:.4f}")
print(f"  - 정량형: {score.numeric_score:.4f}")
print(f"    · language: {score.language_score:.4f}")
print(f"    · proficiency: {score.proficiency_score:.4f}")
print(f"    · gpa: {score.gpa_score:.4f}")

print("\n" + "="*80)
print("✅ Scorer 테스트 완료!")
print("="*80)
