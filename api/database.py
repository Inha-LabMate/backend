"""
PostgreSQL 데이터베이스 연결 설정
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 데이터베이스 설정
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", "5432"))
}


@contextmanager
def get_db_connection():
    """데이터베이스 연결 컨텍스트 매니저"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_cursor(conn):
    """딕셔너리 커서 반환"""
    return conn.cursor(cursor_factory=RealDictCursor)
