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

        with st.status('후보지 계산 중...', expanded=True) as calc_status:
            set_score(dfs1, weight_dic)

            st.write('최적 후보지 계산 중... ')
            rank_dic, max_radar_num = calc_rank(dfs1, df_grid, RANGE_KM, radar_num=50, polygon_coords=grid_bd_points)

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
        name_list=st.session_state['user_input']['selected_weights']
        select_name_lsit=[]
        # st.write(name_list)
        for name, weight in name_list.items():
            if weight!=0:
                select_name_lsit.append(name)
        with st.container(border=True):
            st.subheader(f"선택된 시설 ({len(select_name_lsit)}개)")
            for i, name in enumerate(select_name_lsit, 1):
                st.write(f"{i}. {name}")

        st.markdown('#### 시나리오 저장')
        st.caption('다른 조건과 비교하려면 시나리오로 저장하세요.')
        name = st.text_input('시나리오 이름', placeholder='예) 사정거리 2km')
        if st.button('저장', use_container_width=True):
            if not name.strip():
                st.warning('시나리오 이름을 입력하세요.')
            else:
                scenario  = {'name': name.strip(), **results}
                scenarios = st.session_state.get('scenarios', [])
                scenarios = [s for s in scenarios if s['name'] != name.strip()]
                scenarios.append(scenario)
                st.session_state['scenarios'] = scenarios
                st.success(f"'{name.strip()}' 저장 완료! (총 {len(scenarios)}개)")
        




main()
