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
# 1. 사전 설정 함수
# ================================
DATA_PATH = 'D:/workspaces/00_Project/crawlProject/project/data/'


def get_all_data(data_list):
    '''
    Put all data in dictionary
    '''
    dfs = {}

    for data_name in data_list:
        df = pd.read_csv(DATA_PATH + f"{data_name}/df_{data_name}.csv")
        dfs[data_name] = df
    return dfs


def get_df_grid(data_name):
    df_grid = pd.read_csv(DATA_PATH + f'grid/{data_name}.csv')
    return df_grid


def set_score(df, alpha):
    df['score'] = [alpha] * len(df) 



# ================================
# 2. 계산 함수
# ================================
def grid_cover(coords, range_km=3, include_self=False):
    """
    coords: (n,2) array [lat, lng] (degree)
    range_km: 커버 반경 (km)
    include_self: 자기 자신 포함 여부
    """

    if len(coords) == 0:
        return pd.DataFrame()

    # degree → rad
    coords_rad = np.deg2rad(coords)

    # BallTree 생성
    tree = BallTree(coords_rad, metric='haversine')

    # km → rad
    radius = range_km / 6371

    # 이웃 찾기
    indices = tree.query_radius(coords_rad, r=radius)

    # 자기 자신 처리
    if include_self:
        cover_indices = indices
    else:
        cover_indices = [idx[idx != i] for i, idx in enumerate(indices)]

    # 커버 개수
    cover_count = [len(idx) for idx in cover_indices]

    # 결과
    df_coverage = pd.DataFrame({
        'jammer_id': range(len(coords)),
        'cover_count': cover_count,
        'covered_points': cover_indices
    })

    return df_coverage


def building_cover(coords_grid, coords_building, RANGE_KM=1):
    """
    격자 좌표를 기준으로 반경 내 포함되는 건물 정보를 계산하는 함수

    Parameters
    ----------
    coords_grid : array-like (n, 2)
        격자 중심 좌표 (위도, 경도, degree)

    coords_building : array-like (m, 2)
        건물 좌표 (위도, 경도, degree)

    range_km : float, optional
        탐색 반경 (km 단위), 기본값 1km

    Returns
    -------
    df_result : pandas.DataFrame
        각 격자별 포함된 건물 개수와 인덱스 정보를 담은 데이터프레임
        - grid_id : 격자 인덱스
        - building_count : 포함된 건물 개수
        - building_indices : 포함된 건물 인덱스 리스트
    """

    # rad 변환
    grid_rad = np.deg2rad(coords_grid)
    building_rad = np.deg2rad(coords_building)

    # BallTree (건물 기준)
    tree = BallTree(building_rad, metric='haversine')

    # 반경 (km → rad)
    radius = RANGE_KM / 6371

    # 각 grid 기준 건물 찾기
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


def calc_score(dfs, df_grid, RANGE_KM):
    '''
    격자 점수 산출
    dfs : 데이터 딕셔너리
    RANGE_KM : 레이더 사정거리
    '''

    grid_lat_min = df_grid["sw_lat"].min()
    grid_lat_max = df_grid["ne_lat"].max()
    grid_lon_min = df_grid["sw_lng"].min()
    grid_lon_max = df_grid["ne_lng"].max()
   
    # 격자 내부에 있는 데이터만 필터링
    filtered_list = []

    for key, df in dfs.items():
        filtered = df[
            (df['latitude'] >= grid_lat_min) &
            (df['latitude'] <= grid_lat_max) &
            (df['longitude'] >= grid_lon_min) &
            (df['longitude'] <= grid_lon_max)
        ].copy()

        filtered_list.append(filtered)

    df_building = pd.concat(filtered_list, ignore_index=True)

    coords_building = df_building[['latitude', 'longitude']].values
    coords_grid = df_grid[['center_lat', 'center_lng']].values


    # 점수 산정
    df_result = building_cover(coords_grid, coords_building, RANGE_KM)

    scores = []
    for cover in df_result['building_indices'].values:
        sc = 0
        for grid_no in cover:
            sc += df_building.iloc[grid_no]['score']
        scores.append(sc)

    df_result['score'] = scores
    return df_result


def grid_cover_single(center_coord, all_coords, RANGE_KM=3):
    """
    center_coord: [lat, lng] - 기준이 되는 단일 좌표
    all_coords: (n,2) array - 전체 격자 좌표들
    range_km: 커버 반경 (km)
    """

    # degree → radian
    all_coords_rad = np.deg2rad(all_coords)
    center_rad = np.deg2rad(center_coord).reshape(1, -1)

    # BallTree 생성
    tree = BallTree(all_coords_rad, metric='haversine')

    # 반경 내 이웃 탐색
    radius = RANGE_KM / 6371
    indices = tree.query_radius(center_rad, r=radius)[0]

    # 자기 자신 제외 (center_coord와 동일한 좌표)
    indices = indices[~np.all(all_coords[indices] == center_coord, axis=1)]

    return indices  # 주변 격자의 인덱스 배열



def calc_rank(dfs, df_grid, RANGE_KM, radar_num):
    rank_dic = {}
    dfs_temp = {key: df.copy() for key, df in dfs.items()}  # ★ dfs만 복사

    for _ in range(radar_num):
        df_result = calc_score(dfs_temp, df_grid, RANGE_KM)  # ★ df_grid 고정

        max_score = df_result['score'].max()
        best_points = list(df_result[df_result['score'] == max_score].index)

        if len(best_points) != 1:
            cover_list = []
            for point in best_points:
                center_coord = df_grid.loc[point, ['center_lat', 'center_lng']].values
                all_coords = df_grid[['center_lat', 'center_lng']].values
                pos_indices = grid_cover_single(center_coord, all_coords, RANGE_KM)
                label_indices = df_grid.index[pos_indices]
                cover_list.append(label_indices)

            best_idx = max(range(len(cover_list)), key=lambda x: len(cover_list[x]))
            position_grid = best_points[best_idx]
            rank_dic[position_grid] = cover_list[best_idx]
            pos = df_grid.loc[position_grid, ['center_lat', 'center_lng']].values

        else:
            pos = df_grid.loc[best_points[0], ['center_lat', 'center_lng']].values
            all_coords = df_grid[['center_lat', 'center_lng']].values
            pos_indices = grid_cover_single(pos, all_coords, RANGE_KM)
            label_indices = df_grid.index[pos_indices]
            rank_dic[best_points[0]] = label_indices

        # ★ dfs_temp에서 커버된 시설물만 제거
        all_building_coords = pd.concat(dfs_temp.values())[['latitude', 'longitude']].values
        building_pos_indices = grid_cover_single(pos, all_building_coords, RANGE_KM)
        covered_set = set(map(tuple, all_building_coords[building_pos_indices]))

        for key in dfs_temp:
            dfs_temp[key] = dfs_temp[key][
                ~dfs_temp[key].apply(
                    lambda r: (r['latitude'], r['longitude']) in covered_set, axis=1
                )
            ]

    return rank_dic


def visualize(df_grid, dfs, rank_dic, ICON_MAP):
    # MAP 객체 생성
    m = folium.Map(location=[37.5, 127.04], zoom_start=10)

    # 격자 경계점
    grid_lat_min = df_grid["sw_lat"].min()
    grid_lat_max = df_grid["ne_lat"].max()
    grid_lon_min = df_grid["sw_lng"].min()
    grid_lon_max = df_grid["ne_lng"].max()


    # 격자 구역 표시
    folium.Rectangle(
        bounds=[[grid_lat_min, grid_lon_min], [grid_lat_max, grid_lon_max]],
        color="blue",
        weight=2,
        fill=True,
        fill_opacity=0.05,
        tooltip="격자 전체 영역"
    ).add_to(m)


    for key, df in dfs.items():

        layer = folium.FeatureGroup(name=key)

        filtered = df[
            (df['latitude'] >= grid_lat_min) &
            (df['latitude'] <= grid_lat_max) &
            (df['longitude'] >= grid_lon_min) &
            (df['longitude'] <= grid_lon_max)
        ].copy()

        for _, row in filtered.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                tooltip=row['name'],
                popup=folium.Popup(row['name'], max_width=200),
                icon=ICON_MAP.get(key, folium.Icon(color="gray", icon="question", prefix="fa"))
            ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)  # 레이어 패널 기본으로 열어둠

    # 레이더 위치 표시
    import random

    def random_color():
        r = random.randint(50, 200)
        g = random.randint(50, 200)
        b = random.randint(50, 200)
        return f"#{r:02x}{g:02x}{b:02x}"

    for rank, point in enumerate(rank_dic.keys(), start=1):
        loca = df_grid.loc[point, ['center_lat', 'center_lng']].values
        color = random_color()

        # 숫자 아이콘
        folium.Marker(
            location=loca,
            tooltip=f"{rank}순위 레이더",
            popup=folium.Popup(f"{rank}순위 레이더 (grid_id: {point})", max_width=200),
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        background-color: {color};
                        color: white;
                        font-size: 13px;
                        font-weight: bold;
                        width: 28px;
                        height: 28px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 2px solid white;
                        box-shadow: 2px 2px 4px rgba(0,0,0,0.4);
                    ">{rank}</div>
                """,
                icon_size=(28, 28),
                icon_anchor=(14, 14)  # 아이콘 중심이 좌표에 오도록
            )
        ).add_to(m)

        folium.Circle(
            location=loca,
            radius=RANGE_KM * 1000,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.15,
            tooltip=f"{rank}순위 커버 범위"
        ).add_to(m)

    m.save("map.html")
    print("저장 완료: map.html")



def run():
    data_list = ['hospital',
                'factory',
                'bridge',
                'electricity',
                'infra',
                'public',
                'telecommunication',
                'transportation',
                'water']

    dfs = get_all_data(data_list)
    df_grid = get_df_grid('grid_50m_18417cells')

    RANGE_KM = 1.5
    radar_num = 3
    rank_dic = calc_rank(dfs, df_grid, RANGE_KM, radar_num)

    ICON_MAP = {
            "hospital":   folium.Icon(color="red",     icon="hospital",        prefix="fa"),
            "factory":    folium.Icon(color="blue",    icon="industry",        prefix="fa"),
            "substation": folium.Icon(color="green",   icon="bolt",            prefix="fa"),
            "bridge":     folium.Icon(color="purple",  icon="road",            prefix="fa"),
            "core":       folium.Icon(color="darkred", icon="broadcast-tower", prefix="fa"),
        }

    visualize(df_grid, dfs, rank_dic, ICON_MAP)