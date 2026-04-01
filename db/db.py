from get_data.get import get_engine, disconnect_db, get_engine_server
from sqlalchemy import text

def upload_result(df):
 
    # DB 생성 
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE DATABASE IF NOT EXISTS result CHARACTER SET utf8mb4"))
    disconnect_db(engine)

    # result DB에 연결
    engine = get_engine(db_name='result')

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'result' 
            AND table_name LIKE 'case%'
        """))
        tables = [str(row[0]) for row in result]
        if tables:
            max_index = max(int(t.replace('case', '')) for t in tables)
        else:
            max_index = 0

        next_index = max_index + 1

    table_name = f"case{next_index}"
    df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
    print(f"저장 완료: {table_name}")

    disconnect_db(engine)


def delete_result(case_name):
    engine = get_engine(db_name='result')
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{case_name}`"))  # 없는 테이블 삭제 시 오류 방지
        conn.commit()

    disconnect_db(engine)



######## SERVER ###########

from sqlalchemy import text, create_engine

def upload_result_server(df):
    """
    SQL Server에 'result' DB 존재 여부를 확인하고, 없으면 생성 후 데이터를 저장한다.
    """
    # 1. master DB에 접속하여 'result' DB 존재 여부 확인
    # 엔진 생성 단계에서 isolation_level을 AUTOCOMMIT으로 설정하여 트랜잭션 문제를 원천 차단함
    engine_master = get_engine_server() # 기존 엔진 생성 함수 호출
    
    # 별도의 자동 커밋용 엔진을 임시로 생성 (이게 가장 확실함)
    autocommit_engine = engine_master.execution_options(isolation_level="AUTOCOMMIT")
    
    try:
        with autocommit_engine.connect() as conn:
            # DB 존재 여부 조회
            exists_query = text("SELECT COUNT(*) FROM sys.databases WHERE name = 'result'")
            db_exists = conn.execute(exists_query).scalar()
            
            if not db_exists:
                print("🆕 'result' 데이터베이스가 없어 생성 중...")
                # 이미 엔진이 AUTOCOMMIT 모드이므로 바로 실행 가능
                conn.execute(text("CREATE DATABASE result"))
                print("✅ 'result' 데이터베이스 생성 완료")
    finally:
        engine_master.dispose()

    # 2. 'result' DB에 접속하여 데이터 적재
    # (주의: get_engine_server 함수가 db_name='result'를 반영하도록 수정되어 있어야 함)
    engine_result = get_engine_server(db_name='result') 
    
    try:
        with engine_result.connect() as conn:
            # 테이블 목록 확인
            result = conn.execute(text("SELECT name FROM sys.tables WHERE name LIKE 'case%'"))
            tables = [row[0] for row in result]
            
            indices = []
            for t in tables:
                try:
                    indices.append(int(t.replace('case', '')))
                except ValueError:
                    continue
            
            next_index = max(indices) + 1 if indices else 1
            table_name = f"case{next_index}"

            # 3. 데이터 저장
            df.to_sql(name=table_name, con=engine_result, if_exists='replace', index=False)
            print(f"🚀 [{table_name}] 테이블에 데이터 저장 성공!")
            
            # MSSQL은 명시적 커밋이 필요한 경우가 있음
            conn.commit()

    except Exception as e:
        print(f"❌ 데이터 저장 중 오류 발생: {e}")
    finally:
        engine_result.dispose()