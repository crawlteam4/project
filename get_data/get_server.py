from get_data.get import * 
import streamlit as st
from sqlalchemy import create_engine, text
from glob import glob
import urllib

def reset_and_create_db_server():
    """서버에 데이터베이스를 완전히 삭제하고 새로 생성한다."""
    db = st.secrets["dbserver"]
    
    # ── 1. 마스터(master) DB로 접속 ──────────────────────
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={db['server']};"
        f"DATABASE=master;"  # <--- 여기가 핵심: master로 접속
        f"UID={db['username']};"
        f"PWD={db['password']};"
        f"TrustServerCertificate=yes;"
    )
    
    temp_engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        isolation_level="AUTOCOMMIT" 
    )
    
    try:
        with temp_engine.connect() as conn:
            # ── 2. 기존 DB 삭제 ──────────────────────────
            print(f"🔄 기존 데이터베이스({db['database']}) 삭제 중...")
            conn.execute(text(f"""
                IF EXISTS (SELECT * FROM sys.databases WHERE name = '{db['database']}')
                BEGIN
                    ALTER DATABASE [{db['database']}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                    DROP DATABASE [{db['database']}];
                END
            """))
            
            # ── 3. 새 DB 생성 ────────────────────────────
            print(f"🆕 새 데이터베이스({db['database']}) 생성 중...")
            conn.execute(text(f"CREATE DATABASE [{db['database']}]"))
            
            print(f"✅ '{db['database']}' 초기화 및 생성 완료!")

    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose()


def get_engine_server(db_name=None):
    db = st.secrets["dbserver"]

    database = db_name if db_name else db['database']
    
    params = urllib.parse.quote_plus(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={db['server']};'
        f'DATABASE={database};'
        f'UID={db['username']};'
        f'PWD={db['password']};'
        f'TrustServerCertificate=yes;'
    )

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine

def get_all_data_server(engine, data_list):
    """
    지정된 테이블 목록을 SELECT하여 딕셔너리로 반환합니다.
    Returns: {테이블명: DataFrame}
    """
    dfs = {}
    for data in data_list:
        query = f"SELECT * FROM [{data}]"
        dfs[data] = pd.read_sql(query, engine)
    return dfs


def reset_server_data():

    # 0단계: Reset database
    reset_and_create_db_server()
    # 1단계: DB 연결
    engine = get_engine_server()

    # 2단계: 연결 상태 확인
    try:
        if test_connection(engine) == 1:
            print("1/2단계: DB 연결 및 체크 성공")
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None

    # 3단계: 적재
    import_data(engine)

    # 4단계: 연결 해제
    disconnect_db(engine)
    
@st.cache_data
def load_data(data_list):
    engine = get_engine_server(db_name=None)
    dfs1 = get_all_data_server(engine, data_list)
    disconnect_db(engine)
    return dfs1
