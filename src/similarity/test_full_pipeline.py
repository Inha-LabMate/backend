"""
전체 추천 시스템 통합 테스트
1단계: 후보군 생성 (candidate_generator)
2단계: 재랭킹 (scorer)
"""

import sys
from pathlib import Path

# src 경로 추가
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from similarity import (
    CandidateGenerator,
    Student,
    RerankingScorer,
    StudentProfile,
    DEFAULT_CONFIG,
    RESEARCH_CONFIG,
    SKILL_CONFIG
)


def test_full_pipeline():
    """전체 파이프라인 테스트"""
    print("="*80)
    print("🚀 전체 추천 시스템 테스트")
    print("="*80)
    
    # ========================================================================
    # 학생 프로필 정의 (1단계 + 2단계 통합)
    # ========================================================================
    
    # 옵션 1: 컴퓨터 비전 전공자 (현재 비활성)
    # student_profile = StudentProfile(
    #     # 1단계: 후보군 생성용
    #     research_interests="이미지 분류",
        
    #     # 2단계: 재랭킹용 문장형 데이터
    #     intro1="컴퓨터 비전과 딥러닝을 활용한 이미지 인식 연구에 관심이 있습니다. "
    #            "특히 객체 탐지와 이미지 분류 분야에서 최신 딥러닝 모델을 연구하고 싶습니다.",
    #     intro2="Python, PyTorch, TensorFlow를 사용하여 YOLO 기반 실시간 객체 탐지 시스템을 구현한 경험이 있습니다. "
    #            "OpenCV를 활용한 영상 처리와 데이터 전처리에도 익숙합니다.",
    #     intro3="Vision Transformer와 같은 차세대 비전 모델을 연구하여, "
    #            "실시간 영상 분석 시스템의 성능을 향상시키는 것이 목표입니다.",
    #     portfolio="[프로젝트 1] YOLO v5 기반 실시간 객체 탐지 시스템 (정확도 92%) "
    #               "[프로젝트 2] GAN을 이용한 이미지 생성 및 스타일 변환 "
    #               "[프로젝트 3] Vision Transformer 모델 성능 최적화 연구",
    #     major="컴퓨터공학",
    #     certifications="정보처리기사, 빅데이터분석기사",
    #     awards="AI 해커톤 대회 우수상, 캡스톤 디자인 금상",
    #     tech_stack="Python, PyTorch, TensorFlow, OpenCV, scikit-learn, NumPy, Pandas",
    #     toeic_score="850",
    #     english_proficiency="중상",
    #     gpa="4.0"
    # )
    
    # 옵션 2: 네트워크/보안 전공자 (현재 활성)
    student_profile = StudentProfile(
        research_interests="네트워크 보안, 무선 통신, IoT 시스템",
        intro1="네트워크 보안과 무선 통신 프로토콜에 관심이 있습니다. "
               "특히 IoT 환경에서의 경량 암호화, 침입 탐지 시스템, 5G/6G 네트워크 보안 연구를 하고 싶습니다.",
        intro2="Python과 C를 사용하여 SDN 기반 DDoS 탐지 시스템을 구축한 경험이 있습니다. "
               "Wireshark, Scapy를 활용한 패킷 분석과 Mininet으로 네트워크 시뮬레이션을 진행했습니다.",
        intro3="차세대 무선 네트워크에서 AI 기반 이상 트래픽 탐지와 "
               "경량 블록체인을 활용한 IoT 보안 프레임워크를 연구하는 것이 목표입니다.",
        portfolio="[프로젝트 1] OpenFlow 기반 SDN 컨트롤러 DDoS 탐지 시스템 (탐지율 94%) "
                  "[프로젝트 2] LoRaWAN IoT 네트워크 보안 분석 및 취약점 진단 "
                  "[프로젝트 3] 머신러닝 기반 네트워크 침입 탐지 모델 (Random Forest, 정확도 96%) "
                  "[프로젝트 4] AES-GCM 경량 암호화 라이브러리 STM32 포팅",
        major="컴퓨터공학",
        certifications="정보처리기사, 정보보안기사",
        awards="네트워크 보안 경진대회 우수상, 사이버 보안 해커톤 장려상",
        tech_stack="Python, C, Wireshark, Scapy, Mininet, OpenFlow, NS-3, Docker, Kali Linux, Metasploit",
        toeic_score="880",
        english_proficiency="상",
        gpa="3.9"
    )
    
    # ========================================================================
    # 1단계: 후보군 생성 (10~20개)
    # ========================================================================
    print("\n" + "="*80)
    print("1단계: 후보군 생성")
    print("="*80)
    
    # StudentProfile에서 research_interests 추출하여 후보군 생성
    student_query = Student(research_interests=student_profile.research_interests)
    
    # 후보군 생성기 초기화
    generator = CandidateGenerator()
    
    # 후보군 생성
    result = generator.get_candidates_with_scores(
        student_query,
        final_top_k=10
    )
    
    # 결과에서 연구실 리스트 추출
    candidates = []
    for lab_id, lab_info in result.items():
        # 연구실 객체는 generator.labs에서 id로 찾기
        lab = next((l for l in generator.labs if l.id == lab_id), None)
        if lab:
            candidates.append(lab)
    
    print(f"\n✅ 후보군 생성 완료: {len(candidates)}개 연구실")
    for i, lab in enumerate(candidates[:5], 1):
        print(f"{i}. {lab.name} ({lab.professor})")
    
    # ========================================================================
    # 2단계: 재랭킹 (모든 유사도 계산)
    # ========================================================================
    print("\n" + "="*80)
    print("2단계: 재랭킹")
    print("="*80)
    # 기본 설정 스코어러
    print("\n📊 기본 설정으로 재랭킹")
    scorer_default = RerankingScorer(DEFAULT_CONFIG)
    results_default = scorer_default.rerank_candidates(student_profile, candidates, top_k=5)
    
    print("\n🏆 최종 추천 결과 (기본 설정):")
    for i, result in enumerate(results_default, 1):
        print(f"\n{i}위. {result.lab_name}")
        print(f"   최종 점수: {result.final_score:.4f}")
        print(f"   - 문장형: {result.sentence_score:.4f} "
              f"(intro1:{result.intro1_score:.2f}, intro2:{result.intro2_score:.2f}, "
              f"intro3:{result.intro3_score:.2f}, portfolio:{result.portfolio_score:.2f})")
        print(f"   - 키워드형: {result.keyword_score:.4f} "
              f"(major:{result.major_score:.2f}, cert:{result.certification_score:.2f}, "
              f"award:{result.award_score:.2f}, tech:{result.tech_stack_score:.2f})")
        print(f"   - 정량형: {result.numeric_score:.4f} "
              f"(language:{result.language_score:.2f}, proficiency:{result.proficiency_score:.2f}, "
              f"gpa:{result.gpa_score:.2f})")
    
    # 결과 저장
    scorer_default.save_results(results_default, "test_final_results_default.json")
    
    # ========================================================================
    # 다양한 설정으로 재랭킹 비교
    # ========================================================================
    print("\n" + "="*80)
    print("3단계: 다양한 설정 비교")
    print("="*80)
    
    # 연구 중심 설정
    print("\n📚 연구 중심 설정으로 재랭킹")
    scorer_research = RerankingScorer(RESEARCH_CONFIG)
    results_research = scorer_research.rerank_candidates(student_profile, candidates, top_k=3)
    
    print("\n🏆 최종 추천 결과 (연구 중심):")
    for i, result in enumerate(results_research, 1):
        print(f"{i}위. {result.lab_name} - {result.final_score:.4f}점")
    
    # 기술 중심 설정
    print("\n💻 기술 중심 설정으로 재랭킹")
    scorer_skill = RerankingScorer(SKILL_CONFIG)
    results_skill = scorer_skill.rerank_candidates(student_profile, candidates, top_k=3)
    
    print("\n🏆 최종 추천 결과 (기술 중심):")
    for i, result in enumerate(results_skill, 1):
        print(f"{i}위. {result.lab_name} - {result.final_score:.4f}점")
    
    # ========================================================================
    # 설정별 순위 변화 비교
    # ========================================================================
    print("\n" + "="*80)
    print("4단계: 설정별 순위 변화 분석")
    print("="*80)
    
    print("\n📊 상위 3개 연구실 순위 변화:")
    print(f"{'순위':<5} {'기본 설정':<25} {'연구 중심':<25} {'기술 중심':<25}")
    print("-"*80)
    
    for i in range(min(3, len(results_default))):
        default_name = results_default[i].lab_name if i < len(results_default) else "-"
        research_name = results_research[i].lab_name if i < len(results_research) else "-"
        skill_name = results_skill[i].lab_name if i < len(results_skill) else "-"
        
        print(f"{i+1}위   {default_name:<25} {research_name:<25} {skill_name:<25}")
    
    print("\n" + "="*80)
    print("✅ 전체 테스트 완료!")
    print("="*80)
    
    print("\n💾 저장된 파일:")
    print("  - test_final_results_default.json")
    
    return results_default


if __name__ == "__main__":
    results = test_full_pipeline()
