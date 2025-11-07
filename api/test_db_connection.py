"""
PostgreSQL 연결 테스트
"""

import sys
from pathlib import Path

# api 폴더를 경로에 추가
api_path = Path(__file__).parent
sys.path.insert(0, str(api_path))

from database import get_db_connection, get_cursor, DB_CONFIG


def test_connection():
    """데이터베이스 연결 테스트"""
    print("="*80)
    print("🔌 PostgreSQL 연결 테스트")
    print("="*80)
    
    try:
        # 연결 시도
        print("\n⏳ 연결 시도 중...")
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            
            # PostgreSQL 버전 확인
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"\n✅ 연결 성공!")
            print(f"\n📦 PostgreSQL 버전:")
            print(f"   {version['version']}")
            
            # student_profiles 테이블 존재 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'student_profiles'
                );
            """)
            table_exists = cursor.fetchone()['exists']
            
            if table_exists:
                print(f"\n✅ student_profiles 테이블 존재")
                
                # 테이블 구조 확인
                cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = 'student_profiles'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                print(f"\n📊 테이블 구조 ({len(columns)}개 컬럼):")
                for col in columns:
                    col_info = f"   - {col['column_name']}: {col['data_type']}"
                    if col['character_maximum_length']:
                        col_info += f"({col['character_maximum_length']})"
                    print(col_info)
                
                # 데이터 개수 확인
                cursor.execute("SELECT COUNT(*) as count FROM student_profiles;")
                count = cursor.fetchone()['count']
                print(f"\n📈 저장된 데이터: {count}개")
                
                # 샘플 데이터 조회
                if count > 0:
                    cursor.execute("SELECT student_id, research_interests, major FROM student_profiles LIMIT 3;")
                    samples = cursor.fetchall()
                    print(f"\n🎯 샘플 데이터:")
                    for sample in samples:
                        print(f"   - {sample['student_id']}: {sample['research_interests']} ({sample['major']})")
            else:
                print(f"\n⚠️  student_profiles 테이블이 존재하지 않습니다.")
                print(f"\n💡 테이블 생성 SQL:")
                print("""
CREATE TABLE IF NOT EXISTS student_profiles (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) UNIQUE,
    research_interests TEXT NOT NULL,
    intro1 TEXT,
    intro2 TEXT,
    intro3 TEXT,
    portfolio TEXT,
    major VARCHAR(100),
    certifications TEXT,
    awards TEXT,
    tech_stack TEXT,
    toeic_score INTEGER,
    english_proficiency VARCHAR(20),
    gpa DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
                """)
            
    except Exception as e:
        print(f"\n❌ 연결 실패!")
        print(f"   에러: {type(e).__name__}")
        print(f"   메시지: {str(e)}")
        return False
    
    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
    return True


if __name__ == "__main__":
    test_connection()
