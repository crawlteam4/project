import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from glob import glob
import streamlit as st
import json
import geopandas as gpd

def reset_and_create_db():
    """데이터베이스를 완전히 삭제하고 새로 생성합니다."""
    db = st.secrets["mysql"]
    
    # 1. 특정 DB를 지정하지 않고 서버 자체에 연결 (관리자 권한 연결)
    base_url = f"mysql+pymysql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/?charset={db['charset']}"
    
    # DB 생성/삭제는 트랜잭션 밖에서 즉시 실행되어야 하므로 AUTOCOMMIT 설정이 필수입니다.
    temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    
    try:
        with temp_engine.connect() as conn:
            # [기존 DB 삭제] 있으면 지우고, 없으면 무시합니다.
            conn.execute(text(f"DROP DATABASE IF EXISTS {db['database']}"))
            
            # [새 DB 생성] 지정된 이름과 인코딩으로 새로 만듭니다.
            conn.execute(text(f"CREATE DATABASE {db['database']} CHARACTER SET {db['charset']}"))
            
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose() # 임시 엔진 연결 해제

# 1. DB 연결
@st.cache_resource
def get_engine():
    db = st.secrets["mysql"]
    url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['database']}"
        f"?charset={db['charset']}"
    )
    engine = create_engine(url, pool_pre_ping=True)
    return engine

# 2. DB 연결 테스트
def test_connection():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar()

# 3. 데이터 넣기
def import_data():

    engine = get_engine()
    file_list = glob('final_data/*.csv')
    
    for file in file_list:
        df = pd.read_csv(file)
        
        # 1. 확장자(.csv) 제거 (예: df_area_density.csv -> df_area_density)
        raw_name = os.path.splitext(os.path.basename(file))[0]
        
        # 2. 맨 앞이 'df_'로 시작하면 해당 부분만 제거 (예: df_area_density -> area_density)
        file_name = raw_name[3:] if raw_name.startswith('df_') else raw_name
        
        df.to_sql(name=file_name, con=engine, if_exists='replace', index=False)
        print(f"[{file_name}] 테이블 적재 완료")

# 4. 데이터 가져오기 (Select)
def get_all_data(data_list):
    engine = get_engine()
    dfs = {}
    for data in data_list:
        query = f"""
            SELECT *
            FROM {data}
        """
        dfs[data] = pd.read_sql(query, engine)

    
    return dfs

# 5. 연결 해제 (Disconnect)
def disconnect_db(engine):
    engine.dispose()



# ---------------------------------------------------------
# 메인 실행 파이프라인 (Run)
# ---------------------------------------------------------
@st.cache_data
def get_dfs():
    reset_and_create_db()
    # 1단계: 연결
    engine = get_engine()
    
    # 2단계: 연결 상태 체크
    try:
        if test_connection() == 1:
            print("1/2단계: DB 연결 및 체크 성공")
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None  # 연결 실패 시 파이프라인 중단
        
    # 3단계: 데이터 적재
    import_data()
   
    # 4단계: 적재된 데이터 다시 가져오기
    file_list = glob('final_data/*.csv')
    table_names = []

    # 제외하고 싶은 테이블 키워드
    exclude_keywords = ['population_raw', 'area_density_raw']
    
    for file in file_list:
        file_basename = os.path.basename(file)
        
        # 파일명에 제외 키워드가 포함되어 있으면 table_names 리스트에 넣지 않음
        if any(keyword in file_basename for keyword in exclude_keywords):
            print(f"➖ [{file_basename}]은 DB에는 있지만 가져오기 목록에서 제외")
            continue
            
        raw_name = os.path.splitext(file_basename)[0]
        table_name = raw_name[3:] if raw_name.startswith('df_') else raw_name
        table_names.append(table_name)
    
    # 필터링된 목록만 DB에서 Select해서 가져옴
    dfs = get_all_data(table_names)
    print(f"4단계: 최종 {len(dfs)}개 데이터 가져오기 완료")
    
    # 5단계: 연결 해제
    disconnect_db(engine)
    
    return dfs


def get_latest_grid_data():
    """
    다운로드 폴더에서 가장 최근에 생성된 격자 CSV와 
    그에 대응하는 폴더 정보를 담은 JSON 파일을 동시에 읽어온다.
    """
    # 1. 다운로드 경로 설정
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    
    # 2. 'grid'로 시작하는 모든 CSV 파일 검색
    csv_files = glob(os.path.join(download_dir, "grid*.csv"))
    
    if not csv_files:
        print("❌ 다운로드 폴더에서 격자 CSV 파일을 찾을 수 없다.")
        return None, None

    # 3. 가장 최근 파일(수정 시간 기준) 선택
    latest_csv = max(csv_files, key=os.path.getmtime)
    
    # 4. 파일명 규칙에 따라 대응하는 JSON 경로 생성
    # 예: grid5.csv -> grid5_polygon.json
    base_path = os.path.splitext(latest_csv)[0]
    latest_json = f"{base_path}_polygon.json"

    try:
        # --- CSV 로드 ---
        df_grid = pd.read_csv(latest_csv)
        print(f"✅ CSV 로드 성공: {os.path.basename(latest_csv)} ({len(df_grid)}행)")

        # --- JSON 로드 ---
        polygon_info = None
        if os.path.exists(latest_json):
            with open(latest_json, 'r', encoding='utf-8') as f:
                polygon_info = json.load(f)
            print(f"✅ JSON 로드 성공: {os.path.basename(latest_json)}")
        else:
            print(f"⚠️ 경고: 짝이 되는 JSON({os.path.basename(latest_json)})이 없다.")

        return df_grid, polygon_info['polygon_coords']

    except Exception as e:
        print(f"❌ 데이터 로드 중 오류 발생: {e}")
        return None, None
    


def get_df_population(df_grid):
    
    # 1. 데이터 불러오기
    df_pop = pd.read_csv(DATA_PATH + 'population/df_population_raw.csv')
    
    gdf_grid = gpd.GeoDataFrame(df_grid, geometry=[Point(xy) for xy in zip(df_grid['center_lng'], df_grid['center_lat'])], crs="EPSG:4326")
    gdf_pop = gpd.GeoDataFrame(df_pop, geometry=[Point(xy) for xy in zip(df_pop['center_lng'], df_pop['center_lat'])], crs="EPSG:4326")

    # 3. grid 미터좌표계 변환
    gdf_grid = gdf_grid.to_crs(epsg=5179)
    gdf_pop = gdf_pop.to_crs(epsg=5179)
    
    # 4. 인구 밀집도 조인 
    gdf_pop_join = gpd.sjoin_nearest(gdf_grid, gdf_pop[['밀집도', 'geometry']], how='left')
    gdf_pop_join = gdf_pop_join.rename(columns={'밀집도': 'population_density'})
    if 'index_right' in gdf_pop_join.columns: gdf_pop_join.drop(columns='index_right', inplace=True)

    # 5. 결과는 다시 위경도(4326)로 복구하여 데이터프레임화
    gdf_pop_join = gdf_pop_join.to_crs(epsg=4326)
    
    # 6. 최종 출력용 DF 정리 및 csv export
    df_population = pd.DataFrame(gdf_pop_join.drop(columns='geometry'))
    df_population = df_population[['grid_id', 'center_lat', 'center_lng', 'population_density']]
    df_population = df_population.fillna(0)
    df_population.to_csv('data/population/df_population.csv', encoding = 'utf-8', index=False)

    return df_population

def get_df_area_density(df_grid):
    
    # 1. 데이터 불러오기 (수정: pd.read_json -> gpd.read_file)
    gdf_area_density = gpd.read_file(DATA_PATH + 'area_density/area_density.geojson')
    
    gdf_grid = gpd.GeoDataFrame(df_grid, geometry=[Point(xy) for xy in zip(df_grid['center_lng'], df_grid['center_lat'])], crs="EPSG:4326")

    # 3. grid 미터좌표계 변환
    gdf_grid = gdf_grid.to_crs(epsg=5179)
    
    # 4. 공간 조인 (Spatial Join)
    gdf_area_density = gpd.sjoin(gdf_grid, gdf_area_density[['value', 'geometry']], how='left', predicate='within')
    
    # 수정: 아래에서 area_density로 호출하므로 통일시켜 줍니다.
    gdf_area_density = gdf_area_density.rename(columns={'value': 'area_density'})
    
    if 'index_right' in gdf_area_density.columns: 
        gdf_area_density.drop(columns='index_right', inplace=True)
    
    gdf_area_density = gdf_area_density.to_crs(epsg=4326)

    # 6. 최종 출력용 DF 정리 및 csv export
    df_area_density = pd.DataFrame(gdf_area_density.drop(columns='geometry'))
    df_area_density = df_area_density[['grid_id', 'center_lat', 'center_lng', 'area_density']]
    df_area_density = df_area_density.fillna(0)
    
    # (선택 사항) 저장 파일명이 df_population.csv로 되어 있어 df_area_density.csv로 수정했습니다.
    df_area_density.to_csv('data/area_density/df_area_density.csv', encoding='utf-8', index=False)

    return df_area_density