import numpy as np
import pandas as pd
import folium
from sklearn.neighbors import BallTree
import requests
from tqdm import tqdm
import time
import json
import random
from shapely.geometry import Point, Polygon
import geopandas as gpd


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


def calc_score(df_building_filtered, df_grid, RANGE_KM):
    '''
    격자 점수 산출
    dfs : 데이터 딕셔너리
    RANGE_KM : 레이더 사정거리
    '''

    coords_building = df_building_filtered[['latitude', 'longitude']].values
    coords_grid = df_grid[['center_lat', 'center_lng']].values

        
    # 점수 산정
    df_result = building_cover(coords_grid, coords_building, RANGE_KM)

    scores = []
    for cover in df_result['building_indices'].values:
        sc = 0
        for grid_no in cover:
            sc += df_building_filtered.iloc[grid_no]['score']
        scores.append(sc)

    df_result['score'] = scores
    return df_result


def calc_rank(dfs, df_grid, RANGE_KM, radar_num=50, polygon_coords=None):
    """
    최적 레이더 설치 위치를 순위별로 계산하는 함수
    
    Args:
        dfs            : 건물 데이터프레임 딕셔너리 {key: DataFrame}
        df_grid        : 격자 정보 데이터프레임
        RANGE_KM       : 레이더 커버 반경 (km)
        radar_num      : 선정할 최대 레이더 수 (기본값 50)
        polygon_coords : 격자를 만들 때 사용한 꼭짓점 리스트
                         [(lat1, lng1), (lat2, lng2), ...] 형태
                         None 이면 기존 bounding box 방식으로 동작
    
    Returns:
        rank_dic      : {격자 인덱스: 점수} 순위별 레이더 위치
        max_radar_num : 실제 사용된 레이더 수
    """

    rank_dic = {}

    # ── 1. 격자 범위 계산 ──────────────────────────────────────────
    grid_lat_min = df_grid["sw_lat"].min()
    grid_lat_max = df_grid["ne_lat"].max()
    grid_lon_min = df_grid["sw_lng"].min()
    grid_lon_max = df_grid["ne_lng"].max()

    # ── 2. 격자 범위 내 건물만 필터링 ─────────────────────────────
    if polygon_coords is not None:
        poly = Polygon([(lng, lat) for lat, lng in polygon_coords])
        lat_list = [c[0] for c in polygon_coords]
        lng_list = [c[1] for c in polygon_coords]
        bb_lat_min, bb_lat_max = min(lat_list), max(lat_list)
        bb_lng_min, bb_lng_max = min(lng_list), max(lng_list)
    else:
        poly = None

    filtered_list = []

    for key, df in dfs.items():
        # 1차: bounding box로 빠르게 후보 추림
        if polygon_coords is not None:
            filtered = df[
                (df['latitude']  >= bb_lat_min) &
                (df['latitude']  <= bb_lat_max) &
                (df['longitude'] >= bb_lng_min) &
                (df['longitude'] <= bb_lng_max)
            ].copy()
            # 2차: 실제 다각형 내부만 남김
            mask = filtered.apply(
                lambda r: poly.contains(Point(r['longitude'], r['latitude'])), axis=1
            )
            filtered = filtered[mask]
        else:
            # 기존 bounding box 방식
            filtered = df[
                (df['latitude']  >= grid_lat_min) &
                (df['latitude']  <= grid_lat_max) &
                (df['longitude'] >= grid_lon_min) &
                (df['longitude'] <= grid_lon_max)
            ].copy()

        filtered_list.append(filtered)
    
    df_building_filtered = pd.concat(filtered_list, ignore_index=True)

    # 1. 필터링된 구역 내의 tag(건물 종류)별 총 개수 계산
    tag_counts = df_building_filtered['tag'].value_counts()
    
    # 2. 기존 score(원본 가중치)를 구역 내 해당 건물의 총 개수로 나누어 단위 점수로 덮어쓰기
    df_building_filtered['score'] = df_building_filtered.apply(
        lambda row: row['score'] / tag_counts[row['tag']] if tag_counts[row['tag']] > 0 else 0.0, 
        axis=1
    )
    
    # 가중치가 0인 중요건물은 계산에서 제외
    df_building_filtered = df_building_filtered[df_building_filtered['score'] > 0]
    
    # 건물 소거용 임시 복사본 (반복마다 커버된 건물을 제거해나감)
    df_building_temp = df_building_filtered.copy()

    # ── 3. 순위별 최적 위치 선정 ───────────────────────────────────
    max_radar_num = radar_num  # 조기 종료 없을 경우 대비 기본값

    for i in range(radar_num):

        # 현재 남은 건물 기준으로 각 격자의 점수 계산
        df_result = calc_score(df_building_temp, df_grid, RANGE_KM)

        # 최고 점수 및 해당 격자 인덱스 추출
        max_score = df_result['score'].max()
        best_points = list(df_result[df_result['score'] == max_score].index)

        # ── 3-1. 동점 격자가 여러 개인 경우 → 커버 범위가 가장 넓은 격자 선택
        if len(best_points) != 1:
            cover_list = []
            for point in best_points:
                center_coord = df_grid.loc[point, ['center_lat', 'center_lng']].values
                all_coords   = df_grid[['center_lat', 'center_lng']].values
                pos_indices  = grid_cover_single(center_coord, all_coords, RANGE_KM)
                label_indices = df_grid.index[pos_indices]
                cover_list.append(label_indices)

            best_idx      = max(range(len(cover_list)), key=lambda x: len(cover_list[x]))
            position_grid = best_points[best_idx]

        # ── 3-2. 최고 점수 격자가 하나인 경우 → 바로 선택
        else:
            position_grid = best_points[0]

        # 선택된 격자 저장
        rank_dic[position_grid] = max_score
        pos = df_grid.loc[position_grid, ['center_lat', 'center_lng']].values

        # ── 4. 선택된 위치 기준으로 커버된 건물 제거 ──────────────
        all_building_coords  = df_building_temp[['latitude', 'longitude']].values
        building_pos_indices = grid_cover_single(pos, all_building_coords, RANGE_KM)

        covered_set = set(map(tuple, all_building_coords[building_pos_indices]))
        df_building_temp = df_building_temp[
            ~df_building_temp.apply(
                lambda r: (r['latitude'], r['longitude']) in covered_set, axis=1
            )
        ]

        # ── 5. 진행 상황 출력 ──────────────────────────────────────
        print('-' * 30)
        print(f'{i+1}순위')
        print(f'위치 : {pos}')
        print(f'점수 : {rank_dic[position_grid]}')
        print(f'남은 시설물 : {len(df_building_temp)}개')

        # 모든 건물이 커버되면 조기 종료
        if len(df_building_temp) == 0:
            max_radar_num = i + 1
            print('-' * 30)
            print(f'최대 radar 개수: {max_radar_num}')
            break

    return rank_dic, max_radar_num


def get_grid_bd_points(data_name):
   
    with open(f'C:/Users/user2/Downloads/{data_name}_polygon.json') as f:
        data = json.load(f)
    return data['polygon_coords']


def get_radar_population_coverage(rank_dic, df_grid, df_population, df_area_density, RANGE_KM):
    """
    각 레이더 위치별 커버되는 격자의 인구밀집도 및 면적밀집도 합 계산
    
    Args:
        rank_dic        : {격자 인덱스: 점수} — calc_rank 반환값
        df_grid         : 격자 정보 데이터프레임
        df_population   : grid_id, population_density 포함 데이터프레임
        df_area_density : grid_id, area_density 포함 데이터프레임
        RANGE_KM        : 레이더 커버 반경 (km)
    
    Returns:
        df_coverage : 레이더 순위별 커버 인구밀집도 및 면적밀집도 합 데이터프레임
    """

    all_coords = df_grid[['center_lat', 'center_lng']].values
    results = []

    for rank, (grid_idx, score) in enumerate(rank_dic.items(), start=1):
        center_coord = df_grid.loc[grid_idx, ['center_lat', 'center_lng']].values

        # 커버되는 격자 인덱스 추출
        pos_indices   = grid_cover_single(center_coord, all_coords, RANGE_KM)
        covered_grids = df_grid.index[pos_indices]

        # 커버된 격자들의 인구밀집도 합
        covered_population = df_population[
            df_population['grid_id'].isin(covered_grids)
        ]['population_density'].sum() / len(covered_grids)
        
        # 커버된 격자들의 면적밀집도 합
        covered_area_density = df_area_density[
            df_area_density['grid_id'].isin(covered_grids)
        ]['area_density'].sum() / len(covered_grids)

        results.append({
            'rank'                : rank,
            'grid_idx'            : grid_idx,
            'center_lat'          : center_coord[0],
            'center_lng'          : center_coord[1],
            'radar_score'         : score,
            'covered_population'  : covered_population,
            'covered_area_density': covered_area_density
        })

    df_coverage = pd.DataFrame(results)
    return df_coverage

def set_score(dfs, weight_dic):
    for tag in dfs.keys():
        dfs[tag]['score'] = [weight_dic[tag]] * len(dfs[tag]) 