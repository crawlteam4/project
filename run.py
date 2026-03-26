import os
import subprocess
import sys
import importlib

REQUIRED_PACKAGES = [
    "numpy",
    "pandas",
    "folium",
    "scikit-learn",
    "ipykernel"
]

def install_missing_packages(env_name=None):
    """
    필요한 패키지가 없으면 자동으로 설치하는 함수

    env_name:
        None → 현재 환경에 설치
        str  → 해당 conda 환경에 설치
    """
    for package in REQUIRED_PACKAGES:
        import_name = 'bs4' if package == 'beautifulsoup4' else package

        try:
            importlib.import_module(import_name)

        except ImportError:
            print(f"--- {package} 설치 중... ---")

            if env_name:  # conda 환경 지정
                subprocess.check_call(
                    f"conda run -n {env_name} pip install {package}",
                    shell=True
                )
            else:  # 현재 환경
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package]
                )

    print("✅ 패키지 설치 완료")

install_missing_packages(env_name=None)

import numpy as np
import pandas as pd
import folium
from sklearn.neighbors import BallTree


# ================================
# 1. 데이터 로드
# ================================
DATA_PATH = "data"

def load_grid_data(default_file='grid_50m_4328cells.csv'):
    """
    data/ 폴더 기준으로 파일 이름만 입력받아 grid 데이터를 로드한다.
    """

    file_name = input(f"파일 이름 입력 (기본: {default_file}): ").strip()

    # 입력 없으면 기본값
    if not file_name:
        file_name = default_file

    # 전체 경로 생성
    file_path = os.path.join(DATA_PATH, file_name)

    # 존재 확인
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일 없음: {file_path}")

    df_grid = pd.read_csv(file_path)
    print(f"✅ 로드 완료: {file_name} (행 수: {len(df_grid)})")

    return df_grid

df_grid = load_grid_data()

# ================================
# 2. 격자 간 커버 관계 계산 함수
# ================================
def make_cover_df(coords, RANGE_KM=3, include_self=False):
    """
    coords: (n,2) array [lat, lng] (degree)
    range_km: 커버 반경 (km)
    include_self: 자기 자신 포함 여부
    """

    # 입력이 비어있으면 빈 데이터프레임 반환
    if len(coords) == 0:
        return pd.DataFrame()

    # degree → radian 변환 (haversine 계산 필수)
    coords_rad = np.deg2rad(coords)

    # BallTree 생성 (거리 계산 최적화 구조)
    tree = BallTree(coords_rad, metric='haversine')

    # 반경 km → radian 변환
    radius = RANGE_KM / 6371

    # 각 점 기준 반경 내 이웃 탐색
    indices = tree.query_radius(coords_rad, r=radius)

    # 자기 자신 포함 여부 처리
    if include_self:
        cover_indices = indices
    else:
        cover_indices = [idx[idx != i] for i, idx in enumerate(indices)]

    # 커버 개수 계산
    cover_count = [len(idx) for idx in cover_indices]

    # 결과 데이터프레임 생성
    df_coverage = pd.DataFrame({
        'jammer_id': range(len(coords)),
        'cover_count': cover_count,
        'covered_points': cover_indices
    })

    return df_coverage


# ================================
# 3. 병원 데이터 전처리 함수
# ================================
def get_df_hospital():
    df_hospital = pd.read_csv('data/서울시 병의원 위치 정보.csv', encoding='utf-8')
    print(f'총 병원 수: {len(df_hospital)}')

    # 약국 제거 (기타 + 기관명에 "약국" 포함)
    condition = (df_hospital['병원분류명'] == '기타') & (df_hospital['기관명'].str.contains('약국'))
    df_hospital = df_hospital[~condition]

    # 중요 병원 필터링
    df_hospital_filtered = df_hospital[
        df_hospital['병원분류명'].isin(['병원','종합병원','보건소','기타'])
    ]

    # 분석용 building 데이터 생성
    df_building = pd.DataFrame()
    df_building['name'] = df_hospital_filtered['기관명']
    df_building['latitude'] = df_hospital_filtered['병원위도']
    df_building['longitude'] = df_hospital_filtered['병원경도']

    # index 정리
    df_building = df_building.reset_index()
    df_building = df_building.drop(columns='index')

    # 태그 및 점수 (추후 확장용)
    df_building['tag'] = pd.Series(['병원'] * len(df_hospital_filtered))
    df_building['score'] = pd.Series([10] * len(df_hospital_filtered))
    print(f'전처리 + 필터링 후 병원 수: {len(df_hospital)}')

    return df_building


# ================================
# 4. 격자 기준 건물 커버 계산
# ================================
def building_cover(coords_grid, coords_building, RANGE_KM=1):
    """
    격자 좌표를 기준으로 반경 내 포함되는 건물 정보를 계산하는 함수
    """

    # 좌표 → radian 변환
    grid_rad = np.deg2rad(coords_grid)
    building_rad = np.deg2rad(coords_building)

    # BallTree 생성 (건물 기준으로 생성)
    tree = BallTree(building_rad, metric='haversine')

    # 반경 km → radian 변환
    radius = RANGE_KM / 6371

    # 각 grid 기준 포함된 건물 탐색
    indices = tree.query_radius(grid_rad, r=radius)

    # 결과 정리
    building_indices = indices
    building_count = [len(idx) for idx in building_indices]

    df_result = pd.DataFrame({
        'grid_id': range(len(coords_grid)),
        'building_count': building_count,
        'building_indices': building_indices,
    })

    return df_result


# ================================
# 5. 데이터 준비
# ================================


def get_range_km(default=1.0):
    """
    반경(km)을 입력받는 함수 (입력 없으면 기본값 사용)
    """

    user_input = input(f"반경(km) 입력 (기본: {default}): ").strip()

    # 입력 없으면 기본값
    if not user_input:
        return default

    try:
        value = float(user_input)

        if value <= 0:
            raise ValueError

        return value

    except ValueError:
        print("❌ 잘못된 입력 → 기본값 사용")
        return default
    

# 재머(레이더) 반경 설정
RANGE_KM = get_range_km()
df_building = get_df_hospital()

# 좌표 추출
coords_building = df_building[['latitude', 'longitude']].values
coords_grid = df_grid[['center_lat', 'center_lng']].values


# ================================
# 6. 커버 계산 및 점수 산정
# ================================
df_result = building_cover(coords_grid, coords_building, RANGE_KM)

# 단순 점수: 포함 건물 수 × 10
df_result['score'] = df_result['building_count'] * 10

# 최대 점수
max_score = df_result['score'].max()

# 최고 점수 격자 선택 (현재는 1순위만)
best_points = df_result[df_result['score'] == max_score].index


# ================================
# 7. 지도 시각화
# ================================
m = folium.Map(location=[37.5, 127.04], zoom_start=7)

# 재머 아이콘 (안테나)
icon_radar = folium.Icon(color='red', icon='broadcast-tower', prefix='fa')

# 모든 병원 표시
for loca in coords_building:
    folium.Marker(location=loca).add_to(m)

# 최적 격자 위치 + 커버 범위 표시
for point in best_points:
    loca = df_grid.iloc[point][['center_lat','center_lng']].values

    # 재머 위치 마커
    folium.Marker(location=loca).add_to(m)

    # 커버 반경 (원)
    folium.Circle(
        location=loca,
        radius=RANGE_KM * 1000,  # km → m
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=0.2
    ).add_to(m)

# 결과 저장
m.save('test.html')