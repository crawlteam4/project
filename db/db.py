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



