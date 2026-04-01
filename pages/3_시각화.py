import streamlit as st
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap
from sklearn.neighbors import BallTree
from calculate.calculate import building_cover
import plotly.graph_objects as go
import plotly.express as px


st.set_page_config(layout="wide")


def building_cover(coords_grid, coords_building, RANGE_KM): # 모듈화시 제거 예정
    grid_rad     = np.deg2rad(coords_grid)
    building_rad = np.deg2rad(coords_building)
    tree         = BallTree(building_rad, metric='haversine')
    indices      = tree.query_radius(grid_rad, r=RANGE_KM / 6371)
    return pd.DataFrame({
        'grid_id':          range(len(coords_grid)),
        'building_count':   [len(idx) for idx in indices],
        'building_indices': indices,
    })


def get_cover_info(dfs: dict, df_rank: pd.DataFrame, range_km: float):

    # dfs의 모든 시설을 어느 카테고리인지 컬럼 추가하면서 합치기 
    df_all = pd.concat(
        [df.assign(category=cat) for cat, df in dfs.items()],
        ignore_index=True,
    )

# 각 후보지의 building cover 계산하여 몇 개 후보지의 값을 가지는지 나타내기 
    candidate_coords = df_rank[['lat', 'lng']].values
    building_coords  = df_all[['latitude', 'longitude']].values  # (M, 2)

    df_result = building_cover(candidate_coords, building_coords, range_km)

    return df_all, df_result['building_indices'].tolist()



def show_score_chart(df_rank: pd.DataFrame):
    """후보지 순위별 점수 엘보우 그래프"""
    ranks  = df_rank['rank'].tolist()
    scores = df_rank['score'].tolist()

    if len(scores) >= 2:
        drops     = [scores[i] - scores[i + 1] for i in range(len(scores) - 1)]
        elbow_idx = drops.index(max(drops))
    else:
        elbow_idx = 0

    colors = ['#f97316' if i == elbow_idx else '#8d8d8d' for i in range(len(ranks))]
    sizes  = [16 if i == elbow_idx else 10 for i in range(len(ranks))]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ranks, y=scores,
        mode='lines',
        line=dict(color='#94a3b8', width=2),
        showlegend=False,
        hoverinfo='skip',
    ))

    fig.add_trace(go.Scatter(
        x=ranks, y=scores,
        mode='markers+text',
        marker=dict(color=colors, size=sizes, line=dict(color='white', width=2)),
        text=[f"{s:.4f}" for s in scores],
        textposition='top center',
        textfont=dict(size=11, color='#475569'),
        hovertemplate='%{x}순위<br>점수: %{y:.5f}<extra></extra>',
        showlegend=False,
    ))

    fig.update_layout(
        xaxis=dict(
            title='후보지 순위',
            tickmode='array',
            tickvals=ranks,
            ticktext=[f"{r}순위" for r in ranks],
        ),
        yaxis=dict(title='점수'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=40, l=60, r=30),
        height=380,
    )

    st.plotly_chart(fig, use_container_width=True)

    if len(scores) >= 2:
        drop_data = [{
            '구간':      f"{ranks[i]}순위 → {ranks[i+1]}순위",
            '점수 차이': round(scores[i] - scores[i+1], 5),
            '비율':      f"{(scores[i] - scores[i+1]) / scores[0] * 100:.1f}%",
        } for i in range(len(scores) - 1)]
        st.markdown("#### 구간별 점수 차이")
        st.dataframe(
            pd.DataFrame(drop_data).style.apply(
                lambda row: ['background-color: #fff7ed; color: #f97316'
                             if row.name == elbow_idx else '' for _ in row],
                axis=1,
            ),
            hide_index=True, use_container_width=True,
        )


def show_category_composition(df_rank: pd.DataFrame, df_all: pd.DataFrame,
                               cover_indices: list):
    st.markdown("#### 후보지별 커버 시설 구성")
    st.caption("각 후보지 반경 내 어떤 카테고리 시설이 몇 개 포함되는지 보여줍니다.")

    # 후보지마다 카테고리별 시설 개수 집계
    categories = df_all['category'].unique().tolist()
    rank_labels = [f"{int(row['rank'])}순위" for _, row in df_rank.iterrows()]

    fig = go.Figure()

    for cat in categories:
        cat_indices = df_all[df_all['category'] == cat].index  # 해당 카테고리 행 인덱스

        counts = []
        for covered in cover_indices:
            # 커버된 인덱스 중 이 카테고리에 해당하는 것만 카운트
            count = len(set(covered) & set(cat_indices))
            counts.append(count)

        # 하나라도 커버된 순위가 있을 때만 레이어 추가
        if any(c > 0 for c in counts):
            fig.add_trace(go.Bar(
                name=cat,
                x=rank_labels,
                y=counts,
                hovertemplate=f'{cat}<br>%{{x}}: %{{y}}개<extra></extra>',
            ))

    fig.update_layout(
        barmode='stack',
        xaxis_title='후보지 순위',
        yaxis_title='커버 시설 수',
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=40, l=60, r=30),
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def show_cumulative_coverage(df_rank: pd.DataFrame, df_all: pd.DataFrame,
                              cover_indices: list):
    st.markdown("#### 후보지 추가 시 누적 커버율")
    st.caption("후보지를 늘릴수록 전체 시설 중 몇 %가 커버되는지 보여줍니다.")

    total = len(df_all)
    covered_set = set()
    cumulative  = []

    for indices in cover_indices:
        covered_set.update(indices)               # 집합 합집합으로 중복 제거
        cumulative.append(len(covered_set) / total * 100)

    ranks       = df_rank['rank'].tolist()
    rank_labels = [f"{r}순위" for r in ranks]

    fig = go.Figure()

    # 연결선
    fig.add_trace(go.Scatter(
        x=ranks, y=cumulative,
        mode='lines',
        line=dict(color='#94a3b8', width=2),
        showlegend=False,
        hoverinfo='skip',
    ))

    # 점 + 수치 표시
    fig.add_trace(go.Scatter(
        x=ranks, y=cumulative,
        mode='markers+text',
        marker=dict(color='#3b82f6', size=10, line=dict(color='white', width=2)),
        text=[f"{c:.1f}%" for c in cumulative],
        textposition='top center',
        textfont=dict(size=11, color='#475569'),
        hovertemplate='%{x}순위까지<br>누적 커버율: %{y:.1f}%<extra></extra>',
        showlegend=False,
    ))

    fig.update_layout(
        xaxis=dict(
            title='후보지 수',
            tickmode='array',
            tickvals=ranks,
            ticktext=rank_labels,
        ),
        yaxis=dict(title='누적 커버율 (%)', range=[0, 105]),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=40, l=60, r=30),
        height=380,
    )

    st.plotly_chart(fig, use_container_width=True)


def show_heatmap(dfs: dict, df_rank: pd.DataFrame, range_km: float):
    """시설 분포 히트맵"""
    st.markdown("#### 시설 분포 히트맵")

    center_lat = df_rank['lat'].mean() if not df_rank.empty else 37.5
    center_lng = df_rank['lng'].mean() if not df_rank.empty else 127.04
    m = folium.Map(location=[center_lat, center_lng], zoom_start=11)

    all_buildings = pd.concat(dfs.values(), ignore_index=True) if dfs else pd.DataFrame()
    if not all_buildings.empty:
        heat_data = all_buildings[['latitude', 'longitude']].dropna().values.tolist()
        HeatMap(heat_data, radius=15, blur=10, min_opacity=0.4).add_to(m)

    palette = ['red', 'blue', 'green', 'purple', 'orange']
    for _, row in df_rank.iterrows():
        color = palette[(int(row['rank']) - 1) % len(palette)]
        rank  = int(row['rank'])

        folium.Marker(
            location=[row['lat'], row['lng']],
            tooltip=f"{rank}순위  |  점수: {row['score']:.4f}",
            icon=folium.DivIcon(
                html=f"""<div style="
                    background:{color}; color:white; font-weight:bold;
                    width:26px; height:26px; border-radius:50%;
                    border:2px solid white; display:flex;
                    align-items:center; justify-content:center;
                    font-size:13px; box-shadow:2px 2px 4px rgba(0,0,0,0.4);">
                    {rank}</div>""",
                icon_size=(26, 26), icon_anchor=(13, 13),
            ),
        ).add_to(m)

        folium.Circle(
            location=[row['lat'], row['lng']],
            radius=range_km * 1000,
            color=color, fill=True, fill_color=color, fill_opacity=0.12,
            tooltip=f"{rank}순위 커버 범위 ({range_km} km)",
        ).add_to(m)

    st.components.v1.html(m._repr_html_(), height=520)



def main():
    st.title("시각화")

    results = st.session_state.get('calc_results')
    if results is None:
        st.info("계산 페이지에서 계산을 먼저 실행해주세요.")
        return

    df_rank  = results['df_rank']
    dfs      = results['dfs']
    range_km = results['range_km']

    if df_rank.empty:
        st.warning("계산 결과가 없습니다. 선택된 카테고리 데이터를 확인하세요.")
        return

    # 커버 정보는 탭 2·3에서 공통으로 사용하므로 한 번만 계산
    df_all, cover_indices = get_cover_info(dfs, df_rank, range_km)

    tab1, tab2, tab3, tab4 = st.tabs(["점수 분포", "카테고리 구성", "누적 커버율", "히트맵"])

    with tab1:
        show_score_chart(df_rank)
    with tab2:
        show_category_composition(df_rank, df_all, cover_indices)
    with tab3:
        show_cumulative_coverage(df_rank, df_all, cover_indices)
    with tab4:
        show_heatmap(dfs, df_rank, range_km)


main()
