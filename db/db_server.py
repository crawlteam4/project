from get_data.get import get_engine, disconnect_db
from get_data.get_server import get_engine_server
from sqlalchemy import text

def upload_result_server(df):
    # 1. DB 생성을 위해 'master'에 직접 연결 (캐시를 타지 않거나 명시적 인자 전달)

    engine_master = get_engine_server(db_name='master')
    
    autocommit_engine = engine_master.execution_options(isolation_level="AUTOCOMMIT")
    
    with autocommit_engine.connect() as conn:
        # DB 존재 확인
        db_exists = conn.execute(text("SELECT COUNT(*) FROM sys.databases WHERE name = 'result'")).scalar()
        
        if not db_exists:
            print("'result' 데이터베이스가 없어 생성을 시도한다...")
            conn.execute(text("CREATE DATABASE result"))
            print("'result' 데이터베이스 생성 완료!")
        else:
            print("'result' 데이터베이스가 이미 존재한다.")
            

    # 2. 데이터 적재를 위해 'result' DB에 연결
    engine_result = get_engine_server(db_name='result')
    
    try:
        with engine_result.connect() as conn:

            res = conn.execute(text("SELECT name FROM sys.tables WHERE name LIKE 'case%'"))
            tables = [row[0] for row in res]
            
            indices = [int(t.replace('case', '')) for t in tables if t.replace('case', '').isdigit()]
            next_index = max(indices) + 1 if indices else 1
            table_name = f"case{next_index}"

            # 데이터 저장
            df.to_sql(name=table_name, con=engine_result, if_exists='replace', index=False)
            conn.commit()
            print(f"[{table_name}] 테이블에 저장 성공!")
    except Exception as e:
        print(f"데이터 적재 실패: {e}")
    finally:
        engine_master.dispose()


def delete_result_server(case_name):
    """
    result 데이터베이스에서 특정 결과 테이블(caseN)을 삭제한다.
    """
    # 1. result DB에 연결 (인자로 'result' 전달)
    engine = get_engine_server(db_name='result')
    
    try:
        with engine.connect() as conn:
            print(f" [{case_name}] 테이블 삭제 시도 중...")

            query = text(f"DROP TABLE IF EXISTS [{case_name}]")
            conn.execute(query)
            
            conn.commit()
            print(f"[{case_name}] 삭제 완료!")
            
    except Exception as e:
        print(f"삭제 중 오류 발생: {e}")
        
    finally:
        engine.dispose()