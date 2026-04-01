import streamlit as st
import pandas as pd
import numpy as np
import folium
import plotly.graph_objects as go
from calculate.calculate import building_cover



if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("로그인이 필요합니다.")
    st.stop()  # 이 아래 코드는 실행되지 않음
    

    
def show_score_chart(df_rank: pd.DataFrame):
    """후보지 순위별 점수 엘보우 그래프"""
    ranks  = df_rank['rank'].tolist()
    scores = df_rank['score'].tolist()

    if len(scores) >= 2:
        drops     = [scores[i] - scores[i + 1] for i in range(len(scores) - 1)]
        elbow_idx = drops.index(max(drops))
    else:
        elbow_idx = 0

    colors = ["#ffab44" if i == elbow_idx else '#8d8d8d' for i in range(len(ranks))]
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
                lambda row: ['background-color:#FEF9C3; color:#454545; font-weight:bold;'
                             if row.name == elbow_idx else '' for _ in row],
                axis=1,
            ),
            hide_index=True, use_container_width=True,
        )



st.header('후보지 순위별 점수 그래프')
results = st.session_state.get('calc_results')
df_rank  = results['df_rank']


show_score_chart(df_rank)




st.set_page_config(layout="wide")
st.header("후보지별 커버리지 지도")

# ── 세션 상태 확인 ────────────────────────────────────────────────
results    = st.session_state.get('calc_results')
user_input = st.session_state.get('user_input')

if results is None:
    st.info("계산 페이지에서 계산을 먼저 실행해주세요.")
    st.stop()

if user_input is None:
    st.info("사용자 입력 페이지에서 조건을 먼저 입력해주세요.")
    st.stop()

df_rank  = results['df_rank']
dfs      = results['dfs']
range_km = results['range_km']
weights  = results['weights']   # {영문key: float}

# ── 카테고리 매핑 ─────────────────────────────────────────────────
CAT_KR = {
    'broadcast':         '방송시설',
    'electricity':       '전력시설',
    'factory':           '산업 시설',
    'hospital':          '병원',
    'infra':             '지하공동구',
    'prison':            '교정 시설',
    'public':            '국가 공공기관 시설',
    'science':           '과학연구',
    'telecommunication': '정보통신시설',
    'transportation':    '교통 항공 항만 시설',
    'water':             '수원 시설',
    'frequency':         '기지국',
}

CAT_COLORS = {
    'broadcast':         '#F97316',
    'electricity':       '#22C55E',
    'factory':           '#3B82F6',
    'hospital':          '#EF4444',
    'infra':             '#1E3A8A',
    'prison':            '#374151',
    'public':            '#0891B2',
    'science':           '#EC4899',
    'telecommunication': '#A78BFA',
    'transportation':    '#15803D',
    'water':             '#38BDF8',
    'frequency':         '#B91C1C',
}

# ── 가중치 > 0인 카테고리만 사용 ──────────────────────────────────
# user_input의 selected_weights (한글) → weights (영문) 와 대응
selected_weights_kr = user_input.get('selected_weights', {})

# 영문키 기준으로 가중치 > 0인 카테고리 필터
active_cats = [
    cat for cat in dfs.keys()
    if weights.get(cat, 0) > 0
]

if not active_cats:
    st.warning("가중치가 0보다 큰 카테고리가 없습니다. 사용자 입력에서 가중치를 설정해주세요.")
    st.stop()

# ── 가중치 > 0인 카테고리만 합쳐서 df_all 생성 ───────────────────
df_all = pd.concat(
    [dfs[cat].assign(category=cat) for cat in active_cats if cat in dfs],
    ignore_index=True,
)

# ── 모든 후보지에 대해 building_cover 계산 ────────────────────────
@st.cache_data
def compute_coverage(rank_coords, building_coords, range_km):
    return building_cover(rank_coords, building_coords, range_km)

cover_result = compute_coverage(
    df_rank[['lat', 'lng']].values,
    df_all[['latitude', 'longitude']].values,
    range_km,
)

# ── UI: 후보지 선택 ───────────────────────────────────────────────
rank_options = df_rank['rank'].astype(int).tolist()

col_sel1, col_sel2 = st.columns([2, 5])
with col_sel1:
    selected_rank = st.selectbox(
        "후보지 순위 선택",
        rank_options,
        format_func=lambda x: f"{x}순위",
    )

# 선택한 후보지 정보
cand_idx      = selected_rank - 1
candidate     = df_rank.iloc[cand_idx]
covered_idx   = cover_result.iloc[cand_idx]['building_indices']
covered_df    = df_all.iloc[covered_idx].copy()
cat_counts    = covered_df['category'].value_counts()

# ── 지표 요약 ─────────────────────────────────────────────────────
total_covered = len(covered_idx)
weighted_score = sum(
    cat_counts.get(cat, 0) * weights.get(cat, 0)
    for cat in active_cats
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("순위",         f"{selected_rank}위")
m2.metric("커버 건물 수", f"{total_covered}개")
m3.metric("가중치 점수",  f"{weighted_score:.4f}")
m4.metric("반경",         f"{range_km} km")

st.divider()

# ── Folium 지도 생성 ──────────────────────────────────────────────
def build_map(candidate, covered_df, active_cats, range_km):
    m = folium.Map(
        location=[candidate['lat'], candidate['lng']],
        zoom_start=14,
        tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors'

    )


    # 커버리지 원
    folium.Circle(
        location=[candidate['lat'], candidate['lng']],
        radius=range_km * 1000,
        color='#3B82F6',
        weight=2,
        fill=True,
        fill_color='#3B82F6',
        fill_opacity=0.08,
        tooltip=f"{int(candidate['rank'])}순위 반경 {range_km}km",
    ).add_to(m)

    # 후보지 마커
    folium.Marker(
        location=[candidate['lat'], candidate['lng']],
        icon=folium.DivIcon(
            html=f'''
            <div style="
                background:#EF4444;color:white;font-weight:bold;
                border-radius:50%;width:32px;height:32px;
                display:flex;align-items:center;justify-content:center;
                font-size:13px;border:2px solid white;
                box-shadow:0 2px 6px rgba(0,0,0,0.3);">
                {int(candidate['rank'])}
            </div>''',
            icon_size=(32, 32),
            icon_anchor=(16, 16),
        ),
        tooltip=f"{int(candidate['rank'])}순위 후보지 | 위도 {candidate['lat']:.5f}, 경도 {candidate['lng']:.5f}",
    ).add_to(m)

    # 카테고리별 건물 마커 레이어
    for cat in active_cats:
        cat_df = covered_df[covered_df['category'] == cat]
        if cat_df.empty:
            continue

        layer = folium.FeatureGroup(
            name=f"{CAT_KR.get(cat, cat)} ({len(cat_df)}개)",
            show=True,
        )
        color = CAT_COLORS.get(cat, '#6B7280')

        for _, row in cat_df.iterrows():
            name_val = row.get('name', row.get('시설명', row.get('건물명', '')))
            tooltip_text = f"{CAT_KR.get(cat, cat)}"
            if name_val:
                tooltip_text += f" | {name_val}"

            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                weight=1.5,
                tooltip=tooltip_text,
            ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


map_obj  = build_map(candidate, covered_df, active_cats, range_km)
map_html = map_obj._repr_html_()




# ── 레이아웃: 지도 + 차트 ─────────────────────────────────────────
col_map, col_chart = st.columns([3, 2])

with col_map:
    st.subheader(f"{selected_rank}순위 후보지 커버리지")
    st.caption(f"위도 {candidate['lat']:.6f} | 경도 {candidate['lng']:.6f} | 반경 {range_km}km")
    st.components.v1.html(map_html, height=580, scrolling=False)

with col_chart:
    # ── 카테고리별 건물 수 막대 차트 ──────────────────────────────
    st.subheader("카테고리별 건물 수")

    bar_rows = []
    for cat in active_cats:
        cnt = int(cat_counts.get(cat, 0))
        bar_rows.append({
            '카테고리':  CAT_KR.get(cat, cat),
            '건물 수':   cnt,
            '가중치':    weights.get(cat, 0),
            '가중치 점수': round(cnt * weights.get(cat, 0), 4),
            '_color':   CAT_COLORS.get(cat, '#6B7280'),
        })

    bar_df = pd.DataFrame(bar_rows).sort_values('건물 수', ascending=False)

    fig = go.Figure(go.Bar(
        x=bar_df['카테고리'],
        y=bar_df['건물 수'],
        marker_color=bar_df['_color'].tolist(),
        text=bar_df['건물 수'],
        textposition='outside',
        hovertemplate=(
            '<b>%{x}</b><br>'
            '건물 수: %{y}개<br>'
            '가중치: %{customdata[0]}<br>'
            '가중치 점수: %{customdata[1]}<extra></extra>'
        ),
        customdata=bar_df[['가중치', '가중치 점수']].values,
    ))
    fig.update_layout(
        xaxis_tickangle=-40,
        yaxis_title='건물 수',
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=20, b=80, l=50, r=20),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 상세 테이블 ────────────────────────────────────────────────
    st.subheader("카테고리별 상세")
    display_df = bar_df[['카테고리', '건물 수', '가중치', '가중치 점수']].copy()
    st.dataframe(display_df, hide_index=True, use_container_width=True)

st.divider()

# ── 전체 후보지 비교 요약 ─────────────────────────────────────────
st.subheader("전체 후보지 비교")

summary_rows = []
for i, (_, cand) in enumerate(df_rank.iterrows()):
    c_idx     = cover_result.iloc[i]['building_indices']
    c_df      = df_all.iloc[c_idx]
    c_counts  = c_df['category'].value_counts()
    w_score   = sum(c_counts.get(cat, 0) * weights.get(cat, 0) for cat in active_cats)

    row = {
        '순위':         int(cand['rank']),
        '위도':         round(cand['lat'], 6),
        '경도':         round(cand['lng'], 6),
        '커버 건물 수': len(c_idx),
        '가중치 점수':  round(w_score, 4),
    }
    for cat in active_cats:
        row[CAT_KR.get(cat, cat)] = int(c_counts.get(cat, 0))
    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows)

# 선택된 행 강조 표시
def highlight_selected(row):
    if row['순위'] == selected_rank:
        return ['background-color: #FEF9C3'] * len(row)
    return [''] * len(row)

st.dataframe(
    summary_df.style.apply(highlight_selected, axis=1),
    hide_index=True,
    use_container_width=True,
)
