import streamlit as st
import pandas as pd
import folium
import os
from get_data.get import *
from calculate.calculate import *
from visualize.visualize import *
from db.db import upload_result, delete_result

st.set_page_config(layout="wide")




# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.error("로그인이 필요합니다.")
#     st.stop()  # 이 아래 코드는 실행되지 않음
    

    

ICON_MAP = {
    "broadcast":         folium.Icon(color="orange",    icon="broadcast-tower",  prefix="fa"),
    "electricity":       folium.Icon(color="green",     icon="bolt",             prefix="fa"),
    "factory":           folium.Icon(color="blue",      icon="industry",         prefix="fa"),
    "hospital":          folium.Icon(color="red",       icon="hospital",         prefix="fa"),
    "infra":             folium.Icon(color="darkblue",  icon="cogs",             prefix="fa"),
    "prison":            folium.Icon(color="black",     icon="university",       prefix="fa"),
    "public":            folium.Icon(color="cadetblue", icon="building",         prefix="fa"),
    "science":           folium.Icon(color="pink",      icon="flask",            prefix="fa"),
    "telecommunication": folium.Icon(color="beige",     icon="satellite-dish",   prefix="fa"),
    "transportation":    folium.Icon(color="darkgreen", icon="train",            prefix="fa"),
    "water":             folium.Icon(color="lightblue", icon="tint",             prefix="fa"),
    "frequency":         folium.Icon(color="darkred",   icon="signal",           prefix="fa"),
}
with st.sidebar:
    st.write("📊 **전체 분석 진행률**")
    st.progress(75)
    st.info("🚀 **3단계: 후보지 계산**\n\n알고리즘이 최적의 배치 지점을 산출하고 있습니다.")
    st.divider()

def main():

        # Get data building data
    df_grid, grid_bd_points = get_latest_grid_data()

    dfs1 = get_dfs1()

    # Get pop/density data
    dfs2 = get_dfs2(df_grid)


    if 'user_input' not in st.session_state:
        st.info('사용자 입력 페이지에서 조건을 먼저 입력해주세요.')
        

    if 'calc_results' not in st.session_state:
        user_input = st.session_state['user_input']
        weight     = user_input['selected_weights']

        weight_dic = {
            'broadcast':         weight['방송시설'],
            'electricity':       weight['전력시설'],
            'factory':           weight['산업 시설'],
            'hospital':          weight['병원'],
            'infra':             weight['지하공동구'],
            'prison':            weight['교정 시설'],
            'public':            weight['국가 공공기관 시설'],
            'science':           weight['과학연구'],
            'telecommunication': weight['정보통신시설'],
            'transportation':    weight['교통 항공 항만 시설'],
            'water':             weight['수원 시설'],
            'frequency':         weight['기지국'],
        }
        RANGE_KM  = float(user_input['range_km'])
        radar_num = int(user_input['radar_num'])

        with st.status('후보지 계산 중...', expanded=False) as calc_status:
            set_score(dfs1, weight_dic)

            st.write('최적 후보지 계산 중... ')
            rank_dic, max_radar_num = calc_rank(dfs1, df_grid, RANGE_KM, radar_num, polygon_coords=grid_bd_points)

            df_population = dfs2['population']
            df_area_density = dfs2['area_density']

            df_final = get_df_final(rank_dic, df_grid, df_population, df_area_density, RANGE_KM)

            

            st.session_state.final_df = df_final

            
            ICON_MAP = {
                "broadcast":         folium.Icon(color="orange",     icon="broadcast-tower",   prefix="fa"),
                "electricity":       folium.Icon(color="green",      icon="bolt",              prefix="fa"),
                "factory":           folium.Icon(color="blue",       icon="industry",          prefix="fa"),
                "hospital":          folium.Icon(color="red",        icon="hospital",          prefix="fa"),
                "infra":             folium.Icon(color="darkblue",   icon="cogs",              prefix="fa"),
                "prison":            folium.Icon(color="black",      icon="university",        prefix="fa"),
                "public":            folium.Icon(color="cadetblue",  icon="building",          prefix="fa"),
                "science":           folium.Icon(color="pink",       icon="flask",             prefix="fa"),
                "telecommunication": folium.Icon(color="beige",      icon="satellite-dish",    prefix="fa"),
                "transportation":    folium.Icon(color="darkgreen",  icon="train",             prefix="fa"),
                "water":             folium.Icon(color="lightblue",  icon="tint",              prefix="fa"),
                "frequency":         folium.Icon(color="darkred",    icon="signal",            prefix="fa"),
            }
            



            st.write('지도 생성 중...')
            
            visualize(df_grid, dfs1, rank_dic, RANGE_KM, ICON_MAP,
                        show_rank=None, polygon_coords=grid_bd_points,
                        df_final=df_final)

            df_rank = pd.DataFrame([
                {
                    'rank':  i + 1,
                    'score': score,
                    'lat':   df_grid.loc[idx, 'center_lat'],
                    'lng':   df_grid.loc[idx, 'center_lng'],
                }
                for i, (idx, score) in enumerate(rank_dic.items())
            ])

            # select_name_list 생성
            name_list = st.session_state['user_input']['selected_weights']
            select_name_list = [name for name, weight in name_list.items() if weight != 0]
            
            st.session_state['calc_results'] = {
                'df_rank':   df_rank,
                'dfs':       dfs1,
                'range_km':  RANGE_KM,
                'radar_num': radar_num,
                'weights':   weight_dic,
                'selected_facilities': select_name_list,
            }

            calc_status.update(
                label=f'{len(rank_dic)}개 후보지 선정',
                state='complete',
                expanded=False
            )

    results = st.session_state['calc_results']
    df_rank = results['df_rank']




    col1, col2 = st.columns([6, 3])

    with col1:
        st.write(st.session_state['user_input']['range_km'])
        map_file = os.path.join(os.path.dirname(__file__), '../map.html')
        if os.path.exists(map_file):
            with open(map_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=650)

    with col2:
        # 1. 분석 조건 요약 (사정거리 등 핵심 수치 강조)
        range_km = st.session_state['user_input']['range_km']
        radar_num = st.session_state['user_input']['radar_num']
        results    = st.session_state.get('calc_results')

        with st.container(border=True):
            num_fac=results.get('selected_facilities')
            st.markdown("### 📊 분석 조건 요약")
            c1, c2 = st.columns(2)
            c1.metric("사정 거리", f"{range_km}km")
            c2.metric("후보지 수", f"{len(results['df_rank'])}개")

        # 2. 선택된 시설 리스트 (Badge 스타일 혹은 리스트 정리)
        name_list = st.session_state['user_input']['selected_weights']
        select_name_list = [name for name, weight in name_list.items() if weight != 0]

        with st.container(border=True):
            st.subheader(f"🏢 선택 시설 ({len(select_name_list)}개)")
            if select_name_list:
                # 텍스트 앞에 이모지를 붙여 시각적 요소 추가
                for i, name in enumerate(select_name_list, 1):
                    st.markdown(f"**{i}.** {name}")
            else:
                st.caption("선택된 시설이 없습니다.")

        # 3. 시나리오 저장 섹션 (강조된 박스 형태)
        with st.container(border=True):
            st.markdown("#### 💾 시나리오 저장")
            st.caption('현재 분석 조건을 보관하여 나중에 비교하세요.')
            
            scenario_name = st.text_input(
                '시나리오 이름', 
                placeholder='예) 사정거리 2km 설정안',
                key='scenario_input'
            )
            
            # 버튼 색상에 포인트를 주기 위해 primary 적용 가능
            if st.button('시나리오 저장하기', use_container_width=True, type="primary"):
                if not scenario_name.strip():
                    st.warning('시나리오 이름을 입력하세요.')
                else:
                    # 기존 저장 로직 유지
                    scenario = {'name': scenario_name.strip(), **results}
                    scenarios = st.session_state.get('scenarios', [])
                    scenarios = [s for s in scenarios if s['name'] != scenario_name.strip()]
                    scenarios.append(scenario)
                    st.session_state['scenarios'] = scenarios
                    st.success(f"'{scenario_name.strip()}' 저장 완료!")
            




main()
