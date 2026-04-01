import streamlit as st
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree # 제거 예정

st.set_page_config(layout="wide")


if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("로그인이 필요합니다.")
    st.stop()  # 이 아래 코드는 실행되지 않음
    
    
st.title("데이터프레임")


# 모듈화 시 제거 예정
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


def build_detail_df(df_rank, dfs, range_km):

    # 카테고리 컬럼이 붙은 전체 시설 DataFrame
    df_all = pd.concat(
        [df.assign(category=cat) for cat, df in dfs.items()],
        ignore_index=True,
    )

    # 각 후보지 기준 반경 내 시설 인덱스
    cover_result = building_cover(
        df_rank[['lat', 'lng']].values,
        df_all[['latitude', 'longitude']].values,
        range_km,
    )

    rows = []
    for i, (_, candidate) in enumerate(df_rank.iterrows()):
        covered_idx = cover_result.iloc[i]['building_indices']
        covered_df  = df_all.iloc[covered_idx]

        # 카테고리별 개수 집계
        cat_counts = covered_df['category'].value_counts()

        # 상위 3개 카테고리를 "방송시설(8), 병원(5), 변전소(3)" 형태로
        top3 = ', '.join(
            f"{cat}({cnt})" for cat, cnt in cat_counts.head(3).items()
        )

        rows.append({
            '순위':             int(candidate['rank']),
            '점수':             candidate['score'],
            '위도':             round(candidate['lat'], 6),
            '경도':             round(candidate['lng'], 6),
            '반경 내 시설 수':  len(covered_idx),
            '주요 커버 카테고리': top3 if top3 else '없음',
        })

    return pd.DataFrame(rows)



results = st.session_state.get('calc_results')

if results is None:
    st.info("계산을 먼저 실행해주세요.")
else:
    df_rank  = results['df_rank']
    dfs      = results['dfs']
    range_km = results['range_km']

    detail_df = build_detail_df(df_rank, dfs, range_km)

    st.markdown("#### 후보지 상세 정보")
    st.dataframe(detail_df, hide_index=True, use_container_width=True)

    st.divider()
    csv = detail_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name="결과.csv",
        mime="text/csv",
    )
