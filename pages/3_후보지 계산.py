import streamlit as st
import pandas as pd
import folium
import os
import base64
from get.get import *
from calculate.calculate import *
from visualize.visualize import *
from db.db import upload_result, delete_result
from utils import set_common_banner

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

@st.dialog(" ", width="medium")
def render_help():
    st.subheader('도움말')
    st.write("이 페이지는 **2단계에서 설정한 조건에 따라 최적의 후보지를 자동으로 계산**하고 결과를 시각화합니다.")
    st.write("") 

    col1, col2 = st.columns([3,3])
    
    with col1:
        # 탭 1에 대한 설명
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 지도 시각화</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>계산된 후보지를 지도 위에 표시하고, 각 후보지의 사정거리 내 시설물 분포를 확인합니다.</p>", unsafe_allow_html=True)
            
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 시나리오 저장</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>현재 분석 결과를 시나리오로 저장하여 다른 분석 결과와 비교할 수 있습니다.</p>", unsafe_allow_html=True)
            
    with col2:
        # 탭 2에 대한 설명
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 분석 조건 요약</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>사정거리, 후보지 수, 선택된 시설 등 현재 분석 조건을 한 눈에 확인합니다.</p>", unsafe_allow_html=True)
            
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 모든 조건 초기화</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>분석 조건을 초기화하고 처음부터 새로운 분석을 시작할 수 있습니다.</p>", unsafe_allow_html=True)


def main():
        # Get data building data
    df_grid, grid_bd_points = get_latest_grid_data()

    dfs1 = get_dfs1()

    # Get pop/density data
    dfs2 = get_dfs2(df_grid)


    if 'user_input' not in st.session_state:
        st.error('사용자 입력 페이지에서 조건을 먼저 입력해주세요.')
        st.page_link("pages/2_후보지 조건 설정.py", label="조건 설정 페이지로 이동")
        st.stop()  # 여기서 실행 중단




        

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

    header_col, help_col = st.columns([10, 1])
    with header_col:
        st.subheader("후보지 탐색 결과")
    with help_col:
        st.write("") # 수직 정렬용 여백
        if st.button("도움말"):
            render_help()


    col1, col2 = st.columns([6, 3])

    with col1:
        with st.container(border=True):
            map_file = os.path.join(os.path.dirname(__file__), '../map.html')
            if os.path.exists(map_file):
                with open(map_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=650)

    with col2:
        # 데이터 가져오기
        range_km = st.session_state['user_input']['range_km']
        results = st.session_state.get('calc_results')

        with st.container(border=True):
            # 컬럼 생성
            sub_col1, sub_col2 = st.columns([2, 4.1])

            # --- 왼쪽: 분석 조건 요약 ---
            with sub_col1:
                st.markdown("###### 분석 조건 요약")
                st.metric("사정 거리", f"{range_km}km")
                st.metric("후보지 수", f"{len(results['df_rank'])}개")

            # --- 오른쪽: 선택 시설 리스트 ---
            with sub_col2:
                name_list = st.session_state['user_input']['selected_weights']
                select_name_list = [name for name, weight in name_list.items() if weight != 0]
                
                st.markdown(f"###### 선택 시설 ({len(select_name_list)}개)")
                
                if select_name_list:
                    f_c1, f_c2 = st.columns(2)
                    for i, name in enumerate(select_name_list):
                        target_col = f_c1 if i % 2 == 0 else f_c2
                        target_col.markdown(f"• {name}")
                else:
                    st.caption("선택된 시설 없음")
        # 3. 시나리오 저장 섹션 (강조된 박스 형태)
        with st.container(border=True):
            st.markdown("###### 시나리오 저장")
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

        # 4. 초기화 섹션
        with st.container(border=True):
            st.markdown("###### 초기화")
            st.caption('분석 조건을 초기화하고 처음부터 설정하세요.')
            if st.button('모든 조건 초기화', use_container_width=True, type="secondary"):
                st.session_state.pop('user_input', None)
                st.session_state.pop('calc_results', None)
                st.session_state.pop('final_df', None)
                st.success('모든 조건이 초기화되었습니다. 2단계 페이지로 돌아가 다시 설정해주세요.')
                st.rerun()
            




main()
