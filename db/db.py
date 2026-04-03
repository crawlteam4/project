from get.get import get_engine, disconnect_db
from sqlalchemy import text
import streamlit as st



def upload_result(df):
    """
    DataFrame 데이터를 DB 내 새로운 케이스 테이블로 업로드한다.

    'result' 데이터베이스가 존재하지 않으면 생성하고, 기존에 존재하는 'case' 
    테이블들의 인덱스를 확인하여 그 다음 번호로 새 테이블을 생성해 데이터를 저장한다.

    Parameters
    ----------------------
    df : pandas.DataFrame
        데이터베이스에 저장하고자 하는 결과 데이터셋. 
        비어있지 않은 데이터프레임이어야 한다.

    Returns
    ----------------------
    None
        이 함수는 값을 반환하지 않으며, 작업 완료 메시지를 출력한다.
    """
 
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
    """
    지정한 이름의 결과 테이블을 데이터베이스에서 삭제한다.

    Parameters
    ----------
    case_name : str
        삭제할 테이블의 이름 (예: 'case1', 'case10').
        존재하지 않는 테이블 이름을 입력해도 오류가 발생하지 않도록 처리됨.

    Returns
    ----------
    None

    Raises
    ---------
    sqlalchemy.exc.SQLAlchemyError
        데이터베이스 접속에 실패하거나 SQL 실행 중 예외가 발생할 경우 전달된다.
    """
    engine = get_engine(db_name='result')
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{case_name}`"))  # 없는 테이블 삭제 시 오류 방지
        conn.commit()

    disconnect_db(engine)



