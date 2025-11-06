"""
크롤링 실행 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# src 디렉토리 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 메인 파이프라인 실행
from core.main_pipeline import main

if __name__ == "__main__":
    main()
