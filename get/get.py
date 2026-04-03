import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text, inspect
from glob import glob
import json
import geopandas as gpd
from shapely.geometry import Point, Polygon
from shapely import wkt



def create_db():
    """

    데이터베이스를 완전히 삭제하고 설정된 기본 인코딩으로 새로 생성한다.

    st.secrets에 정의된 MySQL 정보를 바탕으로 서버에 접속하며,
    기존 DB가 존재할 경우 삭제 후 다시 생성하여 초기 상태로 만든다.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    None
    """
    db = st.secrets["mysql"]

    # 특정 DB를 지정하지 않고 서버 자체에 연결 (관리자 권한)
    base_url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/?charset={db['charset']}"
    )

    # CREATE/DROP DATABASE는 트랜잭션 밖에서 즉시 실행해야 하므로 AUTOCOMMIT 필수
    temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")

    try:
        with temp_engine.connect() as conn:
            # 새 DB 생성
            conn.execute(text(f"CREATE DATABASE {db['database']} IF NOT EXISTS CHARACTER SET {db['charset']}"))

    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose()    # 임시 엔진 연결 해제



# ────────────────────────────────────────────────────────────────────────────────
# DB 초기화 (삭제 후 재생성)
# ────────────────────────────────────────────────────────────────────────────────

def create_db():
    """
    데이터베이스를 완전히 삭제하고 설정된 기본 인코딩으로 새로 생성한다.

    st.secrets에 정의된 MySQL 정보를 바탕으로 서버에 접속하며,
    기존 DB가 존재할 경우 삭제 후 다시 생성하여 초기 상태로 만든다.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    None
    """
    db = st.secrets["mysql"]

    # 특정 DB를 지정하지 않고 서버 자체에 연결 (관리자 권한)
    base_url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/?charset={db['charset']}"
    )

    # CREATE/DROP DATABASE는 트랜잭션 밖에서 즉시 실행해야 하므로 AUTOCOMMIT 필수
    temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")

    try:
        with temp_engine.connect() as conn:
            # 새 DB 생성
            conn.execute(text(f"CREATE DATABASE {db['database']} IF NOT EXISTS CHARACTER SET {db['charset']}"))

    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose()  # 임시 엔진 연결 해제




# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 엔진 생성
# ────────────────────────────────────────────────────────────────────────────────
def get_engine(db_name=None):
    """
    SQLAlchemy 엔진을 생성하여 반환한다.

    Parameters
    ----------------------
    db_name : str, optional
        연결할 데이터베이스의 이름. 지정하지 않으면 st.secrets의 
        기본 database 설정을 사용한다.

    Returns
    ----------------------
    sqlalchemy.engine.base.Engine
        생성된 SQLAlchemy 데이터베이스 엔진 객체.
    """
    db = st.secrets["mysql"]
    database = db_name if db_name else db['database']
    url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{database}"
        f"?charset={db['charset']}"
    )
    engine = create_engine(url, pool_pre_ping=True)
    return engine



# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 상태 확인
# ────────────────────────────────────────────────────────────────────────────────
def test_connection(engine):
    """
    단순 쿼리(SELECT 1)를 실행하여 DB 연결 상태를 확인한다.

    Parameters
    ----------------------
    engine : sqlalchemy.engine.base.Engine
        상태를 확인할 데이터베이스 엔진.

    Returns
    ----------------------
    int
        연결 성공 시 1을 반환한다.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar()


# ────────────────────────────────────────────────────────────────────────────────
# 데이터 세팅
# ────────────────────────────────────────────────────────────────────────────────
def set_data():
    """
    로컬의 CSV 및 GeoJSON 파일을 읽어 DB 테이블로 적재한다.

    final_data 폴더 내의 파일들을 검색하여, DB에 존재하지 않는 
    테이블일 경우에만 새로 생성하고 데이터를 임포트한다.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    None
    """
    # DATABASE 세팅
    db = st.secrets["mysql"]
    base_url = f"mysql+pymysql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/"
    base_engine = create_engine(base_url)

    with base_engine.connect() as conn:
        result = conn.execute(text("SHOW DATABASES"))
        existing_dbs = [row[0] for row in result]
        if db['database'] not in existing_dbs:
            conn.execute(text(f'CREATE SCHEMA {db['database']} CHARACTER SET {db['charset']}'))
        else:
            print(f"'{db['database']}' 데이터베이스가 이미 존재한다.")
    disconnect_db(base_engine)

    # IMPORT data
    engine = get_engine(db['database'])
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 2. CSV 파일 처리
    print("--- CSV 데이터 확인 및 적재 시작 ---")
    file_list = glob('final_data/*.csv')

    for file in file_list:
        file_basename = os.path.basename(file)
        raw_name = os.path.splitext(file_basename)[0]
        
        table_name = raw_name[3:] if raw_name.startswith('df_') else raw_name
        
        # 기존 DB에 테이블이 없는 경우에만 적재 진행
        if table_name not in existing_tables:
            print(f"'{table_name}' 테이블 생성 및 데이터 임포트 중...")
            df = pd.read_csv(file)
            df.to_sql(name=table_name, con=engine, if_exists='fail', index=False)
        else:
            print(f"'{table_name}' 테이블은 이미 존재하여 건너뜀.")

    # 3. GeoJSON 파일 처리
    print("\n--- GeoJSON 데이터 확인 및 적재 시작 ---")
    json_list = glob('final_data/*.geojson')

    for json_file in json_list:
        raw_name = os.path.splitext(os.path.basename(json_file))[0]
        json_name = raw_name.split('_')[-1]

        # 기존 DB에 테이블이 없는 경우에만 적재 진행
        if json_name not in existing_tables:
            print(f"'{json_name}' 테이블 생성 및 데이터 임포트 중...")
            gdf = gpd.read_file(json_file)
            
            # geometry 컬럼 문자열 변환
            gdf['geometry'] = gdf['geometry'].apply(lambda x: str(x))
            gdf.to_sql(name=json_name, con=engine, if_exists='fail', index=False)
        else:
            print(f"'{json_name}' 테이블은 이미 존재하여 건너뜀.")
            
    disconnect_db(engine)



# ────────────────────────────────────────────────────────────────────────────────
# DB에서 데이터 조회
# ────────────────────────────────────────────────────────────────────────────────
def get_all_data(engine, data_list):
    """
    지정된 테이블 목록의 모든 데이터를 조회하여 딕셔너리로 반환한다.

    Parameters
    ----------------------
    engine : sqlalchemy.engine.base.Engine
        조회할 데이터베이스 엔진.
    data_list : list of str
        데이터를 가져올 테이블 이름들의 리스트.

    Returns
    ----------------------
    dict
        {테이블명: pandas.DataFrame} 형태의 딕셔너리.
    """
    dfs = {}
    for data in data_list:
        query = f"SELECT * FROM {data}"
        dfs[data] = pd.read_sql(query, engine)
    return dfs

# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 해제
# ────────────────────────────────────────────────────────────────────────────────
def disconnect_db(engine):
    """
    데이터베이스 엔진 연결 풀을 해제하고 리소스를 정리한다.

    Parameters
    ----------------------
    engine : sqlalchemy.engine.base.Engine
        해제할 데이터베이스 엔진.

    Returns
    ----------------------
    None
    """
    engine.dispose()


# ────────────────────────────────────────────────────────────────────────────────
# dfs1 데이터 로드 파이프라인
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data
def get_dfs1():
    
    # Set data
    set_data()
    
    # Connect
    engine = get_engine()

    # Check Connection
    try:
        if test_connection(engine) == 1:
            print("1/2단계: DB 연결 및 체크 성공")
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None

    # dfs1 알고리즘 계산에 들어갈 테이블만 필터링
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    
    exclude_keywords = ['population_raw', 'density', 'users']
    table_names = []

    for table in all_tables:
        if any(keyword in table for keyword in exclude_keywords):
            continue
        table_names.append(table)

    # 필터링된 테이블만 GET
    dfs = get_all_data(engine, table_names)

    # 연결 해제
    disconnect_db(engine)

    return dfs


# ────────────────────────────────────────────────────────────────────────────────
# 최신 격자 CSV + 다각형 JSON 로드
# ────────────────────────────────────────────────────────────────────────────────
def get_latest_grid_data():
    """
    다운로드 폴더에서 가장 최근에 생성된 격자 CSV와 polygon JSON 파일을 로드한다.

    Returns
    ----------------------
    df_grid : pandas.DataFrame or None
        격자 데이터프레임. 파일이 없으면 None.
    polygon_coords : list or None
        다각형 꼭짓점 좌표 리스트. JSON 파일이 없으면 None.
    """
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    # grid로 시작하는 CSV 파일 전체 검색
    csv_files = glob(os.path.join(download_dir, "*.csv"))

    if not csv_files:
        print(" 다운로드 폴더에서 격자 CSV 파일을 찾을 수 없다.")
        return None, None

    # 수정 시간 기준 가장 최근 파일 선택
    latest_csv  = max(csv_files, key=os.path.getmtime)
    base_path   = os.path.splitext(latest_csv)[0]
    latest_json = f"{base_path}_polygon.json"

    try:
        df_grid = pd.read_csv(latest_csv)

        # 대응하는 JSON 파일 로드 (없으면 경고 출력)
        polygon_info = None
        if os.path.exists(latest_json):
            with open(latest_json, 'r', encoding='utf-8') as f:
                polygon_info = json.load(f)
        else:
            print(f"경고: 짝이 되는 JSON({os.path.basename(latest_json)})이 없다.")

        return df_grid, polygon_info['polygon_coords']

    except Exception as e:
        print(f" 데이터 로드 중 오류 발생: {e}")
        return None, None


# ────────────────────────────────────────────────────────────────────────────────
# 인구밀집도 격자 매핑
# ────────────────────────────────────────────────────────────────────────────────
def get_df_population(df_pop_raw, df_grid):
    """
    인구 원시 데이터를 격자 좌표에 조인하여 매핑한다.

    Parameters
    ----------------------
    df_pop_raw : pandas.DataFrame
        'center_lng', 'center_lat', '밀집도' 컬럼을 포함한 원시 데이터.
    df_grid : pandas.DataFrame
        기준이 되는 격자 데이터.

    Returns
    ----------------------
    pandas.DataFrame
        grid_id별 인구밀집도(population_density)가 매핑된 데이터프레임.
    """
    # 격자 / 인구 데이터를 GeoDataFrame으로 변환 (EPSG:4326)
    gdf_grid = gpd.GeoDataFrame(
        df_grid,
        geometry=[Point(xy) for xy in zip(df_grid['center_lng'], df_grid['center_lat'])],
        crs="EPSG:4326"
    )
    gdf_pop = gpd.GeoDataFrame(
        df_pop_raw,
        geometry=[Point(xy) for xy in zip(df_pop_raw['center_lng'], df_pop_raw['center_lat'])],
        crs="EPSG:4326"
    )

    # 거리 계산을 위해 투영 좌표계(EPSG:5179)로 변환
    gdf_grid = gdf_grid.to_crs(epsg=5179)
    gdf_pop  = gdf_pop.to_crs(epsg=5179)

    # 격자 중심 기준 최근접 인구 격자 조인
    gdf_pop_join = gpd.sjoin_nearest(gdf_grid, gdf_pop[['밀집도', 'geometry']], how='left')
    gdf_pop_join = gdf_pop_join.rename(columns={'밀집도': 'population_density'})

    if 'index_right' in gdf_pop_join.columns:
        gdf_pop_join.drop(columns='index_right', inplace=True)

    # 다시 위경도 좌표계로 복원
    gdf_pop_join = gdf_pop_join.to_crs(epsg=4326)

    df_population = pd.DataFrame(gdf_pop_join.drop(columns='geometry'))
    df_population = df_population[['grid_id', 'center_lat', 'center_lng', 'population_density']]
    df_population = df_population.fillna(0)

    return df_population


# ────────────────────────────────────────────────────────────────────────────────
# 면적밀집도 격자 매핑
# ────────────────────────────────────────────────────────────────────────────────
def get_df_area_density(df_den_raw, df_grid):
    """
    면적밀집도 폴리곤 데이터를 격자 중심 좌표에 공간 조인하여 매핑한다.

    격자 중심점(Point)이 면적 폴리곤(Polygon) 내부에 포함되는지(within)를
    기준으로 공간 조인을 수행한다.

    Parameters
    ----------------------
    df_den_raw : pandas.DataFrame
        'geometry'(WKT 형식), 'value' 컬럼을 포함한 원시 데이터.
    df_grid : pandas.DataFrame
        기준이 되는 격자 데이터.

    Returns
    ----------------------
    pandas.DataFrame
        grid_id별 면적밀집도(area_density)가 매핑된 데이터프레임.
    """
    # WKT 문자열 → shapely geometry 객체 변환
    df_den_raw['geometry'] = df_den_raw['geometry'].apply(wkt.loads)

    # 격자는 EPSG:4326, 밀집도 폴리곤은 EPSG:5179로 GeoDataFrame 생성
    gdf_grid    = gpd.GeoDataFrame(
        df_grid,
        geometry=[Point(xy) for xy in zip(df_grid['center_lng'], df_grid['center_lat'])],
        crs="EPSG:4326"
    )
    gdf_den_raw = gpd.GeoDataFrame(df_den_raw, geometry='geometry', crs="EPSG:5179")

    # 격자를 밀집도 폴리곤과 같은 좌표계로 변환
    gdf_grid = gdf_grid.to_crs(epsg=5179)

    # 격자 중심이 폴리곤 내부에 포함되는지 공간 조인 (within)
    gdf_area_density = gpd.sjoin(gdf_grid, gdf_den_raw[['value', 'geometry']], how='left', predicate='within')
    gdf_area_density = gdf_area_density.rename(columns={'value': 'area_density'})

    if 'index_right' in gdf_area_density.columns:
        gdf_area_density.drop(columns='index_right', inplace=True)

    # 다시 위경도 좌표계로 복원
    gdf_area_density = gdf_area_density.to_crs(epsg=4326)

    df_area_density = pd.DataFrame(gdf_area_density.drop(columns='geometry'))
    df_area_density = df_area_density[['grid_id', 'center_lat', 'center_lng', 'area_density']]
    df_area_density = df_area_density.fillna(0)

    return df_area_density


# ────────────────────────────────────────────────────────────────────────────────
# 메인 데이터 로드 파이프라인 (2단계: 인구 / 면적밀집도 데이터)
# ────────────────────────────────────────────────────────────────────────────────
def get_dfs2(df_grid):
    """
    DB에서 원시 데이터를 호출하여 격자 기준의 인구/면적밀집도 데이터프레임을 생성한다.

    Parameters
    ----------------------
    df_grid : pandas.DataFrame
        공간 조인의 기준이 되는 격자 데이터프레임.

    Returns
    ----------------------
    dict
        {'population': df_population, 'area_density': df_area_density} 형태의 딕셔너리.
    """
    engine    = get_engine()
    data_list = ['population_raw', 'density']
    dfs2      = get_all_data(engine, data_list)

    # 불필요한 인덱스 컬럼 제거 후 밀집도 계산
    df_pop_raw = dfs2['population_raw'].drop(columns='Unnamed: 0')
    df_den_raw = dfs2['density']

    df_population   = get_df_population(df_pop_raw, df_grid)
    df_area_density = get_df_area_density(df_den_raw, df_grid)

    disconnect_db(engine)

    return {
        'population'  : df_population,
        'area_density': df_area_density
    }