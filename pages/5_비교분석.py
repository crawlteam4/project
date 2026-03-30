import streamlit as st
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("시나리오 비교")


def building_cover(coords_grid, coords_building, RANGE_KM):
    grid_rad     = np.deg2rad(coords_grid)
    building_rad = np.deg2rad(coords_building)
    tree         = BallTree(building_rad, metric='haversine')
    indices      = tree.query_radius(grid_rad, r=RANGE_KM / 6371)
    return pd.DataFrame({
        'grid_id':          range(len(coords_grid)),
        'building_count':   [len(idx) for idx in indices],
        'building_indices': indices,
    })


def get_cumulative_coverage(dfs, df_rank, range_km):
    """후보지별 누적 커버율(%)"""
    df_all = pd.concat(dfs.values(), ignore_index=True)
    cover_result = building_cover(
        df_rank[['lat', 'lng']].values,
        df_all[['latitude', 'longitude']].values,
        range_km,
    )

    total       = len(df_all)
    covered_set = set()
    cumulative  = []
    for indices in cover_result['building_indices']:
        covered_set.update(indices)
        cumulative.append(round(len(covered_set) / total * 100, 1))
    return cumulative



def show_conditions(s):
    """입력 조건"""
    weights = s['weights']
    top3    = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]

    st.metric("사정 거리", f"{s['range_km']} km")
    st.metric("후보지 수", f"{s['radar_num']} 개")
    st.caption("Top 3 카테고리")
    for cat, w in top3:
        st.markdown(f"- **{cat}** `{w:.5f}`")


def show_score_comparison(s1, s2):
    #두 시나리오 점수를 한 차트에 겹쳐서 표시
    st.markdown("#### 후보지 순위별 점수 비교")

    fig = go.Figure()

    for s, dash in [(s1, 'solid'), (s2, 'dot')]:
        ranks  = s['df_rank']['rank'].tolist()
        scores = s['df_rank']['score'].tolist()
        fig.add_trace(go.Scatter(
            x=ranks, y=scores,
            mode='lines+markers+text',
            name=s['name'],
            line=dict(width=2, dash=dash),
            marker=dict(size=8),
            text=[f"{v:.4f}" for v in scores],
            textposition='top center',
            textfont=dict(size=10),
            hovertemplate=f"{s['name']}<br>%{{x}}순위: %{{y:.5f}}<extra></extra>",
        ))

    # x축 눈금은 두 시나리오의 순위를 합친 범위로
    all_ranks = sorted(set(
        s1['df_rank']['rank'].tolist() + s2['df_rank']['rank'].tolist()
    ))
    fig.update_layout(
        xaxis=dict(
            title='후보지 순위',
            tickmode='array',
            tickvals=all_ranks,
            ticktext=[f"{r}순위" for r in all_ranks],
        ),
        yaxis=dict(title='점수'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=10, b=40, l=60, r=30),
        height=360,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_coverage_comparison(s1, s2):
    #두 시나리오 누적 커버율을 한 차트에 표시
    st.markdown("#### 누적 커버율 비교")

    fig = go.Figure()

    for s, dash in [(s1, 'solid'), (s2, 'dot')]:
        ranks      = s['df_rank']['rank'].tolist()
        cumulative = get_cumulative_coverage(s['dfs'], s['df_rank'], s['range_km'])
        fig.add_trace(go.Scatter(
            x=ranks, y=cumulative,
            mode='lines+markers+text',
            name=s['name'],
            line=dict(width=2, dash=dash),
            marker=dict(size=8),
            text=[f"{v}%" for v in cumulative],
            textposition='top center',
            textfont=dict(size=10),
            hovertemplate=f"{s['name']}<br>%{{x}}순위까지: %{{y}}%<extra></extra>",
        ))

    all_ranks = sorted(set(
        s1['df_rank']['rank'].tolist() + s2['df_rank']['rank'].tolist()
    ))
    fig.update_layout(
        xaxis=dict(
            title='후보지 수',
            tickmode='array',
            tickvals=all_ranks,
            ticktext=[f"{r}순위" for r in all_ranks],
        ),
        yaxis=dict(title='누적 커버율 (%)', range=[0, 105]),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=10, b=40, l=60, r=30),
        height=360,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_rank_table_comparison(s1, s2):
    st.markdown("#### 후보지 상세 비교")
    col1, col2 = st.columns(2)

    for col, s in [(col1, s1), (col2, s2)]:
        with col:
            st.markdown(f"**{s['name']}**")
            df = s['df_rank'][['rank', 'score', 'lat', 'lng']].copy()
            df.columns = ['순위', '점수', '위도', '경도']
            st.dataframe(df, hide_index=True, use_container_width=True)


# ── 메인 ──────────────────────────────────────────────────────────────

def main():
    scenarios = st.session_state.get('scenarios', [])

    if len(scenarios) < 2:
        st.info(f"시나리오가 {len(scenarios)}개 저장되어 있습니다. "
                "계산 페이지에서 최소 2개를 저장해주세요.")
        if scenarios:
            st.caption(f"저장된 시나리오: {', '.join(s['name'] for s in scenarios)}")
        return

    names = [s['name'] for s in scenarios]

    # 비교할 시나리오 2개 선택
    col1, col2 = st.columns(2)
    with col1:
        name_a = st.selectbox("시나리오 A", names, index=0)
    with col2:
        name_b = st.selectbox("시나리오 B", names, index=min(1, len(names) - 1))

    if name_a == name_b:
        st.warning("서로 다른 시나리오를 선택해주세요.")
        return

    s1 = next(s for s in scenarios if s['name'] == name_a)
    s2 = next(s for s in scenarios if s['name'] == name_b)

    # 입력 조건 나란히
    st.markdown("#### 입력 조건 비교")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(f"**{s1['name']}**")
            show_conditions(s1)
    with col2:
        with st.container(border=True):
            st.markdown(f"**{s2['name']}**")
            show_conditions(s2)

    st.divider()
    show_score_comparison(s1, s2)

    st.divider()
    show_coverage_comparison(s1, s2)

    st.divider()
    show_rank_table_comparison(s1, s2)

    # 저장된 시나리오 목록 및 삭제
    with st.expander("저장된 시나리오 관리"):
        for s in scenarios:
            c1, c2 = st.columns([4, 1])
            c1.write(s['name'])
            if c2.button("삭제", key=f"del_{s['name']}"):
                st.session_state['scenarios'] = [
                    x for x in scenarios if x['name'] != s['name']
                ]
                st.rerun()


main()
