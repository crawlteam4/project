import folium
from folium.plugins import MarkerCluster  # 마커 클러스터 임포트 추가
from shapely.geometry import Point, Polygon
import random

def visualize(df_grid, dfs, rank_dic, RANGE_KM, ICON_MAP,
              show_rank=None, polygon_coords=None,
              df_coverage=None):

    mid_lat = (df_grid["ne_lat"].max() + df_grid["sw_lat"].min()) / 2
    mid_lng = (df_grid["sw_lng"].min() + df_grid["ne_lng"].max()) / 2

    m = folium.Map(location=[mid_lat, mid_lng], zoom_start=14)

    # ── 구역 표시 ───────────────────────────────────────────────────
    if polygon_coords is not None:
        folium.Polygon(
            locations=polygon_coords,
            color="blue", weight=2, fill=True, fill_opacity=0.05,
            tooltip="격자 전체 영역"
        ).add_to(m)
        poly = Polygon([(lng, lat) for lat, lng in polygon_coords])
    else:
        grid_lat_min = df_grid["sw_lat"].min()
        grid_lat_max = df_grid["ne_lat"].max()
        grid_lon_min = df_grid["sw_lng"].min()
        grid_lon_max = df_grid["ne_lng"].max()
        folium.Rectangle(
            bounds=[[grid_lat_min, grid_lon_min], [grid_lat_max, grid_lon_max]],
            color="blue", weight=2, fill=True, fill_opacity=0.05,
            tooltip="격자 전체 영역"
        ).add_to(m)
        poly = None

    # ── 건물 마커 (Marker Cluster 적용) ──────────────────────────────
    for key, df in dfs.items():
        if dfs[key]['score'].iloc[0] == 0:
            continue

        # 레이어 컨트롤을 위한 FeatureGroup 생성
        layer = folium.FeatureGroup(name=key)
        
        # [핵심 변경] 해당 레이어 안에 들어갈 마커 클러스터 객체 생성
        marker_cluster = MarkerCluster().add_to(layer)

        if polygon_coords is not None:
            lat_list = [c[0] for c in polygon_coords]
            lng_list = [c[1] for c in polygon_coords]
            filtered = df[
                (df['latitude']  >= min(lat_list)) &
                (df['latitude']  <= max(lat_list)) &
                (df['longitude'] >= min(lng_list)) &
                (df['longitude'] <= max(lng_list))
            ].copy()
            mask = filtered.apply(
                lambda r: poly.contains(Point(r['longitude'], r['latitude'])), axis=1
            )
            filtered = filtered[mask]
        else:
            filtered = df[
                (df['latitude']  >= grid_lat_min) &
                (df['latitude']  <= grid_lat_max) &
                (df['longitude'] >= grid_lon_min) &
                (df['longitude'] <= grid_lon_max)
            ].copy()

        if filtered.empty:
            continue

        for _, row in filtered.iterrows():
            # [핵심 변경] 생성한 마커를 layer가 아니라 marker_cluster에 추가합니다.
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                tooltip=row['name'],
                popup=folium.Popup(row['name'], max_width=200),
                icon=ICON_MAP.get(key, folium.Icon(color="gray", icon="question", prefix="fa"))
            ).add_to(marker_cluster)

        # 완성된 레이어(클러스터 포함)를 지도에 추가합니다.
        layer.add_to(m)

    # ── 레이더 위치 표시 ────────────────────────────────────────────
    coverage_map = {}
    if df_coverage is not None:
        coverage_map = df_coverage.set_index('grid_idx')[
            ['covered_population', 'covered_area_density']
        ].to_dict('index')

    def random_color():
        r, g, b = random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)
        return f"#{r:02x}{g:02x}{b:02x}"

    rank_items = list(rank_dic.items())
    if show_rank is not None:
        rank_items = rank_items[:show_rank]

    for rank, (key, item) in enumerate(rank_items, start=1):
        loca         = df_grid.loc[key, ['center_lat', 'center_lng']].values
        color        = random_color()
        covered_pop  = coverage_map.get(key, {}).get('covered_population', 0)
        covered_area = coverage_map.get(key, {}).get('covered_area_density', 0)
        pop_text     = f"{covered_pop:,.0f}"
        area_text    = f"{covered_area:,.0f}"

        radar_layer = folium.FeatureGroup(name=f'{rank}순위 레이더')

        folium.Marker(
            location=loca,
            tooltip=f"{rank}순위 레이더 | 점수: {item:.4f} | 커버 인구밀집도: {pop_text} | 커버 면적밀집도: {area_text}",
            popup=folium.Popup(
                f"""
                <b>{rank}순위 레이더</b><br>
                grid_id: {key}<br>
                점수: {item:.4f}<br>
                커버 인구밀집도 합: {pop_text}<br>
                커버 면적밀집도 합: {area_text}
                """,
                max_width=200
            ),
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        background-color: {color}; color: white;
                        font-size: 13px; font-weight: bold;
                        width: 28px; height: 28px; border-radius: 50%;
                        display: flex; align-items: center; justify-content: center;
                        border: 2px solid white; box-shadow: 2px 2px 4px rgba(0,0,0,0.4);
                    ">{rank}</div>
                """,
                icon_size=(28, 28), icon_anchor=(14, 14)
            )
        ).add_to(radar_layer)

        folium.Circle(
            location=loca, radius=RANGE_KM * 1000,
            color=color, fill=True, fill_color=color, fill_opacity=0.15,
            tooltip=f"{rank}순위 커버 범위"
        ).add_to(radar_layer)

        radar_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    m.save("map.html")
    print("저장 완료: map.html")