import streamlit as st
import pandas as pd
import numpy as np
import folium
import plotly.graph_objects as go
import base64
from calculate.calculate import building_cover
from db.db import *
from utils import set_common_banner


@st.dialog(" ", width="medium")
def render_help():
    st.subheader('도움말')
    st.write("이 페이지는 **3단계 계산을 통해 선정된 예비 후보지들**간의 원할한 비교를 위해 그래프와 표 등을 제공합니다.")
    st.write("") 
    st.warning('가장 마지막에 분석을 시행한 시나리오에 대한 내용.')

st.set_page_config(layout="wide")
set_common_banner()

# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.error("로그인이 필요합니다.")
#     st.stop()  # 이 아래 코드는 실행되지 않음

st.markdown("""
<style>
[data-testid="stPageLink"] a {
    color: #4c8bf5 !important;
    text-decoration: underline !important;
    font-size: 14px !important;
    transition: color 0.2s ease, letter-spacing 0.15s ease !important;
    display: inline-block !important;
}
[data-testid="stPageLink"] a:hover {
    color: #1a3fa3 !important;
    letter-spacing: 0.5px !important;
}
</style>
""", unsafe_allow_html=True)


if st.session_state.get('calc_results') ==None:
    st.error('사용자 입력 페이지에서 조건을 먼저 입력해주세요.')
    st.page_link("pages/2_후보지 조건 설정.py", label="조건 설정 페이지로 이동")
    st.stop()  # 여기서 실행 중단

# title 과 도움말버튼
header_col, help_col = st.columns([10, 1])
with header_col:
    st.subheader("결과 요약")
with help_col:
    st.write("") # 수직 정렬용 여백
    if st.button("도움말"):
        render_help()


results    = st.session_state.get('calc_results')

df_rank  = results['df_rank']

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


if len(scores) >= 2:
    drop_data = [{
        '구간':      f"{ranks[i]}순위 → {ranks[i+1]}순위",
        '점수 차이': round(scores[i] - scores[i+1], 5),
        '증감률':      f"{(scores[i] - scores[i+1]) / scores[0] * 100:.1f}%",
    } for i in range(len(scores) - 1)]
        
# if len(scores) >= 2:
drop_data = [{
    '구간':      f"{ranks[i]}순위 → {ranks[i+1]}순위",
    '점수 차이': round(scores[i] - scores[i+1], 5),
    '증감률':      f"{(scores[i] - scores[i+1]) / scores[0] * 100:.1f}%",
} for i in range(len(scores) - 1)]
    


# ── 세션 상태 확인 ────────────────────────────────────────────────
user_input = st.session_state.get('user_input')

if results is None:
    st.info("계산 페이지에서 계산을 먼저 실행해주세요.")
    st.stop()

if user_input is None:
    st.info("사용자 입력 페이지에서 조건을 먼저 입력해주세요.")
    st.stop()

tab1, tab2, tab3=st.tabs(['후보지 상세정보','후보지 간 비교 1','후보지 간 비교 2'])

with tab3: 
    col1,col2=st.columns([6,3])
    with col1, col2:
        with col1:
            with st.container(border=True):
                st.markdown('<h5 style="padding: 10px; border-radius: 5px;">후보지 순위별 종합점수(정규화 후) 그래프</h5>', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(
                pd.DataFrame(drop_data).style.apply(
                    lambda row: ['background-color:#FEF9C3; color:#454545; font-weight:bold;'
                                    if row.name == elbow_idx else '' for _ in row],
                    axis=1,
                ),
                hide_index=True, use_container_width=True,
    )


        with col2:
            range_km = st.session_state['user_input']['range_km']
            radar_num = st.session_state['user_input']['radar_num']
            results    = st.session_state.get('calc_results')

            with st.container(border=True):
                # 컬럼 생성
                sub_col1, sub_col2 = st.columns([3, 3])

                num_fac=results.get('selected_facilities')
                with sub_col1:
                    st.markdown("###### 분석 조건 요약")
                    st.metric("사정 거리", f"{range_km}km")
                    st.metric("후보지 수", f"{len(results['df_rank'])}개")

            # 2. 선택된 시설 리스트 (Badge 스타일 혹은 리스트 정리)
                with sub_col2:
                    name_list = st.session_state['user_input']['selected_weights']
                    select_name_list = [name for name, weight in name_list.items() if weight != 0]

                    st.markdown(f"###### 선택 시설 ({len(select_name_list)}개)")
                    if select_name_list:
                        # 텍스트 앞에 이모지를 붙여 시각적 요소 추가
                        for i, name in enumerate(select_name_list, 1):
                            st.markdown(f"•  {name}")
                    else:
                        st.caption("선택된 시설이 없습니다.")





with tab1:

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
    
    # 상단 레이아웃 구성을 위한 컬럼 생성 (지도 3 : 지표 2)
    col_top_map, col_top_summary = st.columns([5, 2])

    with col_top_summary:
        
        with st.container(border=True):
            st.markdown("##### 분석 결과 요약")
            # 1. 순위 선택 (원래 col_sel1에 있던 내용)
            selected_rank = st.selectbox(
                "후보지 순위 선택",
                rank_options,
                format_func=lambda x: f"{x}순위",
                key="rank_selector"
            )
            
            st.divider()

            # 선택한 후보지 정보 계산 (기존 로직 유지)
            cand_idx      = selected_rank - 1
            candidate     = df_rank.iloc[cand_idx]
            # 이미 df_rank에 들어있는 점수를 가져옴
            final_score   = candidate['score']
            covered_idx   = cover_result.iloc[cand_idx]['building_indices']
            covered_df    = df_all.iloc[covered_idx].copy()
            cat_counts    = covered_df['category'].value_counts()

            # ── 지표 요약 계산 ─────────────────────────────────────────────────────
            total_covered = len(covered_idx)
            weighted_score = sum(
                cat_counts.get(cat, 0) * weights.get(cat, 0)
                for cat in active_cats
            )
           

            # 2. 메트릭 표시 (원래 col_sel2에 있던 내용)
            st.metric("순위",         f"{selected_rank}위")
            st.metric("커버 건물 수", f"{total_covered}개")
            st.metric("가중치 점수",  f"{final_score:.4f}")
            st.metric("반경",         f"{range_km} km")

    # ── Folium 지도 생성 (기존 함수 유지) ──────────────────────────────────────────
    def build_map(candidate, covered_df, active_cats, range_km):
        # m = folium.Map(
        #     location=[candidate['lat'], candidate['lng']],
        #     zoom_start=14,
        #     tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        #     attr='© OpenStreetMap contributors'
        # )
        
        m = folium.Map(location=[candidate['lat'], candidate['lng']], 
               zoom_start=14,
               tiles=None)
        folium.TileLayer(
                            tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
                            attr='© OpenStreetMap contributors',
                            name='Layer',   # ← 레이어 컨트롤에 표시될 이름
                            show=True
                        ).add_to(m)
        # ... (기존 build_map 내부 코드와 동일하게 유지) ...
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

        folium.Marker(
            location=[candidate['lat'], candidate['lng']],
            icon=folium.DivIcon(
                html=f'''<div style="background:#EF4444;color:white;font-weight:bold;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:13px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);">{int(candidate['rank'])}</div>''',
                icon_size=(32, 32),
                icon_anchor=(16, 16),
            ),
            tooltip=f"{int(candidate['rank'])}순위 후보지 | 위도 {candidate['lat']:.5f}, 경도 {candidate['lng']:.5f}",
        ).add_to(m)

        for cat in active_cats:
            cat_df = covered_df[covered_df['category'] == cat]
            if cat_df.empty: continue
            layer = folium.FeatureGroup(name=f"{CAT_KR.get(cat, cat)} ({len(cat_df)}개)", show=True)
            color = CAT_COLORS.get(cat, '#6B7280')
            for _, row in cat_df.iterrows():
                name_val = row.get('name', row.get('시설명', row.get('건물명', '')))
                tooltip_text = f"{CAT_KR.get(cat, cat)}"
                if name_val: tooltip_text += f" | {name_val}"
                folium.CircleMarker(location=[row['latitude'], row['longitude']], radius=6, color=color, fill=True, fill_color=color, fill_opacity=0.8, weight=1.5, tooltip=tooltip_text).add_to(layer)
            layer.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        return m

    map_obj  = build_map(candidate, covered_df, active_cats, range_km)
    map_html = map_obj._repr_html_()

    with col_top_map:
        with st.container(border=True):
            st.markdown(f"##### {selected_rank}순위 후보지 커버리지")
            st.caption(f"위도 {candidate['lat']:.6f} | 경도 {candidate['lng']:.6f} | 반경 {range_km}km")
            st.components.v1.html(map_html, height=500, scrolling=False)

    st.divider()

    # 하단 레이아웃: 차트(1) : 상세 표(1)
    col_btm_chart, col_btm_table = st.columns([1, 1])

    with col_btm_chart:
        with st.container(border=True):
        # ── 카테고리별 건물 수 막대 차트 (기존 로직 유지) ──────────────────────────────
            st.markdown("##### 카테고리별 건물 수")
            bar_rows = []
            for cat in active_cats:
                cnt = int(cat_counts.get(cat, 0))
                bar_rows.append({
                    '카테고리':  CAT_KR.get(cat, cat),
                    '건물 수':   cnt,
                    '가중치':    weights.get(cat, 0),
                    '가중치 점수 (정규화 전)': round(cnt * weights.get(cat, 0), 4),
                    '_color':   CAT_COLORS.get(cat, '#6B7280'),
                })
            bar_df = pd.DataFrame(bar_rows).sort_values('건물 수', ascending=False)

            fig = go.Figure(go.Bar(
                x=bar_df['카테고리'],
                y=bar_df['건물 수'],
                marker_color=bar_df['_color'].tolist(),
                text=bar_df['건물 수'],
                textposition='outside',
                hovertemplate=('<b>%{x}</b><br>건물 수: %{y}개<br>가중치: %{customdata[0]}<br>가중치 점수: %{customdata[1]}<extra></extra>'),
                customdata=bar_df[['가중치', '가중치 점수 (정규화 전)']].values,
            ))
            fig.update_layout(xaxis_tickangle=-40, yaxis_title='건물 수', plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=20, b=80, l=50, r=20), height=400)
            st.plotly_chart(fig, use_container_width=True)

    with col_btm_table:
        with st.container(border=True):
            # ── 상세 테이블 (기존 로직 유지) ────────────────────────────────────────────────
            st.markdown("##### 카테고리별 상세")
            display_df = bar_df[['카테고리', '건물 수', '가중치', '가중치 점수 (정규화 전)']].copy()
            st.dataframe(display_df, hide_index=True, use_container_width=True, height=400)


with tab2:
        with st.container(border=True):
            # 종합점수 및 생활인구/토지이용 압축도 간 비교
            results = st.session_state.get('final_df', None)

            if results is None:
                st.info("계산을 먼저 실행해주세요.")
            else:
                results.columns=['순위', '격자ID', '위도', '경도', '종합 점수 (정규화 후)','인구 밀도','건물 밀집도']
                
                # 상단 제목 및 버튼 (우측에 수평으로 배치)
                col_title, col_buttons = st.columns([9, 2])
                with col_title:
                    st.markdown('<h5 style="padding: 10px; border-radius: 5px;">종합점수 및 생활인구/토지이용 압축도 비교</h5>', unsafe_allow_html=True)
                    st.write("")
                with col_buttons:
                    c1, c2 = st.columns([1,1])
                    c1.download_button(
                        label="CSV Download",
                        data=results.to_csv(index=False).encode('utf-8'),
                        file_name='candidate_sites.csv',
                        mime='text/csv',
                    )
                    if c2.button('DB Upload'):
                        upload_result(results)

                # 데이터프레임 표시
                st.dataframe(results, use_container_width=True, hide_index=True)



            st.divider()

            # 커버 건물 개수 간 비교
            st.markdown('<h5 style="padding: 10px; border-radius: 5px;">커버 건물 개수 간 비교</h5>', unsafe_allow_html=True)
            st.write("")

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



# # ── 선택된 시설 배지 표시 ──────────────────────────────────────────
# selected_facilities = results.get('selected_facilities', [])
# if selected_facilities:
#     st.markdown("### 분석 조건")
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric("선택된 시설 수", len(selected_facilities))
#     with col2:
#         st.metric("분석 범위", f"{results.get('range_km', 'N/A')} km")
#     with col3:
#         st.metric("상위 후보지", len(results['df_rank']))
    
#     # 배지 스타일로 선택된 시설 표시
#     st.markdown("**선택된 시설:**")
#     badges_html = ""
#     colors = ["#E0E7FF", "#E0F2FE", "#F0FDF4", "#FEF3C7", "#FCE7F3", "#F3E8FF", "#ECFDF5", "#FEE2E2", "#DBEAFE", "#FEF08A"]
#     for i, facility in enumerate(selected_facilities):
#         color = colors[i % len(colors)]
#         badges_html += f"""<span style='display: inline-block; background-color: {color}; padding: 6px 12px; border-radius: 16px; margin-right: 6px; margin-bottom: 6px; font-size: 13px; font-weight: 500;'>{facility}</span>"""
    
#     st.markdown(badges_html, unsafe_allow_html=True)
#     st.divider()



# ── 전체 후보지 비교 요약 ─────────────────────────────────────────
