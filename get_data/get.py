import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from glob import glob
import json
import geopandas as gpd
from shapely.geometry import Point, Polygon
from shapely import wkt
import urllib

# ────────────────────────────────────────────────────────────────────────────────
# DB 초기화 (삭제 후 재생성)
# ────────────────────────────────────────────────────────────────────────────────

def reset_and_create_db():
    """데이터베이스를 완전히 삭제하고 새로 생성합니다."""
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
            # 기존 DB 삭제 (없으면 무시)
            conn.execute(text(f"DROP DATABASE IF EXISTS {db['database']}"))
            # 새 DB 생성
            conn.execute(text(f"CREATE DATABASE {db['database']} CHARACTER SET {db['charset']}"))

    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose()  # 임시 엔진 연결 해제

def reset_and_create_db_server():
    """서버에 데이터베이스를 완전히 삭제하고 새로 생성한다."""
    db = st.secrets["dbserver"]
    
    # ── 1. 마스터(master) DB로 접속 ──────────────────────
    # 존재하지 않는 DB(projectdb)에 접속하려 하면 에러가 나므로,
    # 시스템 기본 DB인 'master'에 접속하여 생성 명령을 내린다.
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={db['server']};"
        f"DATABASE=master;"  # <--- 여기가 핵심: master로 접속
        f"UID={db['username']};"
        f"PWD={db['password']};"
        f"TrustServerCertificate=yes;"
    )
    
    # isolation_level="AUTOCOMMIT" 설정이 반드시 필요함 (CREATE DATABASE용)
    temp_engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        isolation_level="AUTOCOMMIT" 
    )
    
    try:
        with temp_engine.connect() as conn:
            # ── 2. 기존 DB 삭제 ──────────────────────────
            # 다른 연결이 있을 경우 삭제가 안 될 수 있으므로 SINGLE_USER 모드로 전환 후 삭제
            print(f"🔄 기존 데이터베이스({db['database']}) 삭제 중...")
            conn.execute(text(f"""
                IF EXISTS (SELECT * FROM sys.databases WHERE name = '{db['database']}')
                BEGIN
                    ALTER DATABASE [{db['database']}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                    DROP DATABASE [{db['database']}];
                END
            """))
            
            # ── 3. 새 DB 생성 ────────────────────────────
            # SQL Server는 MySQL과 달리 'CHARACTER SET' 구문이 다르다. 
            # 보통 설치 시 정해진 기본값을 따르거나 COLLATE를 사용한다.
            print(f"🆕 새 데이터베이스({db['database']}) 생성 중...")
            conn.execute(text(f"CREATE DATABASE [{db['database']}]"))
            
            print(f"✅ '{db['database']}' 초기화 및 생성 완료!")

    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose()


# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 엔진 생성
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine(db_name=None):
    """
    SQLAlchemy 엔진을 생성하여 반환합니다.
    db_name을 지정하면 해당 DB로 연결, 없으면 secrets의 기본 DB 사용
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

@st.cache_resource
def get_engine_server(db_name=None):
    db = st.secrets["dbserver"]

    database = db_name if db_name else db['database']
    
    params = urllib.parse.quote_plus(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={db['server']};'
        f'DATABASE={database};'
        f'UID={db['username']};'
        f'PWD={db['password']};'
        f'TrustServerCertificate=yes;' # 인증서 오류 방지용 (필수)
    )

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine

# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 상태 확인
# ────────────────────────────────────────────────────────────────────────────────
def test_connection(engine):
    """SELECT 1 쿼리로 DB 연결 상태를 확인합니다. 성공 시 1 반환"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar()


# ────────────────────────────────────────────────────────────────────────────────
# 로컬 데이터 파일 → DB 적재
# ────────────────────────────────────────────────────────────────────────────────
def import_data(engine):
    """
    final_data/ 폴더의 CSV 및 GeoJSON 파일을 DB에 적재합니다.
    - CSV  : df_ 접두어 제거 후 테이블명으로 사용 (예: df_grid.csv → grid)
    - GeoJSON : 파일명의 마지막 단어를 테이블명으로 사용 (예: grid5_polygon.geojson → polygon)
    """

    # ── CSV 파일 적재 ─────────────────────────────────────────────
    file_list = glob('final_data/*.csv')
    for file in file_list:
        df = pd.read_csv(file)

        # 확장자 제거 후 df_ 접두어 제거
        raw_name  = os.path.splitext(os.path.basename(file))[0]
        file_name = raw_name[3:] if raw_name.startswith('df_') else raw_name

        df.to_sql(name=file_name, con=engine, if_exists='replace', index=False)

    # ── GeoJSON 파일 적재 ─────────────────────────────────────────
    json_list = glob('final_data/*.geojson')
    for json_file in json_list:
        gdf = gpd.read_file(json_file)

        # 파일명의 마지막 단어를 테이블명으로 사용 (예: grid5_polygon → polygon)
        raw_name  = os.path.splitext(os.path.basename(json_file))[0]
        json_name = raw_name.split('_')[-1]

        # geometry 컬럼을 문자열(WKT)로 변환 후 저장
        if 'geometry' in gdf.columns:
            gdf['geometry'] = gdf['geometry'].apply(lambda x: str(x))

        gdf.to_sql(name=json_name, con=engine, if_exists='replace', index=False)


# ────────────────────────────────────────────────────────────────────────────────
# DB에서 데이터 조회
# ────────────────────────────────────────────────────────────────────────────────
def get_all_data(engine, data_list):
    """
    지정된 테이블 목록을 SELECT하여 딕셔너리로 반환합니다.
    Returns: {테이블명: DataFrame}
    """
    dfs = {}
    for data in data_list:
        query = f"SELECT * FROM {data}"
        dfs[data] = pd.read_sql(query, engine)
    return dfs

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

# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 해제
# ────────────────────────────────────────────────────────────────────────────────
def disconnect_db(engine):
    """엔진 연결 풀을 해제합니다."""
    engine.dispose()


# ────────────────────────────────────────────────────────────────────────────────
# 메인 데이터 로드 파이프라인 (1단계: 건물/격자 데이터)
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data
def get_dfs1():
    """
    DB 초기화 → 연결 → 데이터 적재 → 조회 → 연결 해제 순서로 실행합니다.
    population_raw, density 등 중간 처리용 테이블은 제외하고 반환합니다.
    """
    reset_and_create_db()

    # 1단계: DB 연결
    engine = get_engine()

    # 2단계: 연결 상태 확인
    try:
        if test_connection(engine) == 1:
            print("1/2단계: DB 연결 및 체크 성공")
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None

    # 3단계: CSV / GeoJSON 파일 DB 적재
    import_data(engine)

    # 4단계: 제외 키워드 필터링 후 테이블 목록 구성
    file_list        = glob('final_data/*.csv')
    exclude_keywords = ['population_raw', 'density']  # 중간 처리용 테이블 제외
    table_names      = []

    for file in file_list:
        file_basename = os.path.basename(file)

        # 제외 키워드가 파일명에 포함되면 스킵
        if any(keyword in file_basename for keyword in exclude_keywords):
            continue

        raw_name   = os.path.splitext(file_basename)[0]
        table_name = raw_name[3:] if raw_name.startswith('df_') else raw_name
        table_names.append(table_name)

    # 5단계: 필터링된 테이블만 SELECT
    dfs = get_all_data(engine, table_names)

    # 6단계: 연결 해제
    disconnect_db(engine)

    return dfs

def get_dfs1_server():
    """
    DB 초기화 → 연결 → 데이터 적재 → 조회 → 연결 해제 순서로 실행합니다.
    population_raw, density 등 중간 처리용 테이블은 제외하고 반환합니다.
    """
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

    # 3단계: CSV / GeoJSON 파일 DB 적재
    import_data(engine)

    # 4단계: 제외 키워드 필터링 후 테이블 목록 구성
    file_list        = glob('final_data/*.csv')
    exclude_keywords = ['population_raw', 'density']  # 중간 처리용 테이블 제외
    table_names      = []

    for file in file_list:
        file_basename = os.path.basename(file)

        # 제외 키워드가 파일명에 포함되면 스킵
        if any(keyword in file_basename for keyword in exclude_keywords):
            continue

        raw_name   = os.path.splitext(file_basename)[0]
        table_name = raw_name[3:] if raw_name.startswith('df_') else raw_name
        table_names.append(table_name)

    # 5단계: 필터링된 테이블만 SELECT
    dfs = get_all_data_server(engine, table_names)

    # 6단계: 연결 해제
    disconnect_db(engine)

    return dfs

# ────────────────────────────────────────────────────────────────────────────────
# 최신 격자 CSV + 다각형 JSON 로드
# ────────────────────────────────────────────────────────────────────────────────
def get_latest_grid_data():
    """
    다운로드 폴더에서 가장 최근에 생성된 격자 CSV와
    대응하는 polygon JSON 파일을 함께 읽어옵니다.
    (예: grid5.csv ↔ grid5_polygon.json)

    Returns
    -------
    df_grid        : 격자 DataFrame
    polygon_coords : 다각형 꼭짓점 좌표 리스트 (JSON 없으면 None)
    """
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    # grid로 시작하는 CSV 파일 전체 검색
    csv_files = glob(os.path.join(download_dir, "grid*.csv"))

    if not csv_files:
        print("❌ 다운로드 폴더에서 격자 CSV 파일을 찾을 수 없다.")
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
            print(f"⚠️ 경고: 짝이 되는 JSON({os.path.basename(latest_json)})이 없다.")

        return df_grid, polygon_info['polygon_coords']

    except Exception as e:
        print(f"❌ 데이터 로드 중 오류 발생: {e}")
        return None, None


# ────────────────────────────────────────────────────────────────────────────────
# 인구밀집도 격자 매핑
# ────────────────────────────────────────────────────────────────────────────────
def get_df_population(df_pop_raw, df_grid):
    """
    인구 원시 데이터를 격자 중심 좌표에 최근접 조인하여
    격자별 인구밀집도 DataFrame을 반환합니다.
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
    면적밀집도 폴리곤 데이터를 격자 중심 좌표에 공간 조인하여
    격자별 면적밀집도 DataFrame을 반환합니다.
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
    DB에서 population_raw, density 테이블을 불러와
    격자 기준으로 인구밀집도·면적밀집도를 계산하여 반환합니다.

    Returns
    -------
    dfs2 : {'population': df_population, 'area_density': df_area_density}
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


def get_dfs2_server(df_grid):
    """
    DB에서 population_raw, density 테이블을 불러와
    격자 기준으로 인구밀집도·면적밀집도를 계산하여 반환합니다.

    Returns
    -------
    dfs2 : {'population': df_population, 'area_density': df_area_density}
    """
    engine    = get_engine_server()
    data_list = ['population_raw', 'density']
    dfs2      = get_all_data_server(engine, data_list)

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