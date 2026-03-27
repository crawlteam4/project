import streamlit as st
import sys
import os

from utils import apply_input_style



apply_input_style()
# 두 컬럼의 높이를 같게 설정하는 CSS
st.markdown('''
<style>
    [data-testid="column"] {
        display: flex !important;
        flex-direction: column;
    }
</style>
''', unsafe_allow_html=True)

st.caption( 'Drone Defense Allocation System      ',text_alignment='right')

with st.container():
    col1, col2=st.columns([6,3])
    with col1:
        
        map_file = os.path.join(os.path.dirname(__file__), '../make_grid.html')
        if os.path.exists(map_file):
            with open(map_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=700)

        progress_placeholder = st.empty()
        

    with col2: 

        with st.container(border=True):
            st.number_input('사정 거리 (km)', min_value=0.0, max_value=100.0, value=1.5, step=0.2, format='%.1f', key='range_km')
            st.text_input('후보지 수', value='3', key='radar_num', placeholder='후보지 수를 입력하세요')

            options = ['전력시설', '정보통신시설', '국가 공공기관 시설', '교통 항공 항만 시설', '수원 시설', '지하공동구', '인구밀도 ',
                    '토지 이용 압축도', '산업 시설', '기지국', '병원', '과학연구', '교정 시설', '방송시설']
            default_weights = {
                '전력시설':           '0.02198',
                '정보통신시설':        '0.14754',
                '국가 공공기관 시설':  '0.00075',
                '교통 항공 항만 시설': '0.00187',
                '수원 시설':           '0.17237',
                '지하공동구':          '0.01237',
                '인구밀도 ':           '0.0',
                '토지 이용 압축도':    '0.0',
                '산업 시설':           '0.00376',
                '기지국':              '0.00001',
                '병원':                '0.00097',
                '과학연구':            '0.08148',
                '교정 시설':           '0.02757',
                '방송시설':            '0.41787',
            }
            st.write('후보지 고려 사항을 선택하세요 ')
            with st.container(border=True):
                for opt in options:
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        checked = st.checkbox(opt, key=f'check_{opt}')
                    with c2:
                        if checked:
                            st.text_input('가중치', value=default_weights[opt], key=f'weight_{opt}', label_visibility='collapsed', placeholder='가중치')

            st.write('')
        warn_placeholder = st.empty()

        if st.button("Select", key=f"button_{opt}", use_container_width=True):
            any_checked = any(st.session_state.get(f'check_{opt}', False) for opt in options)

            if not any_checked:
                warn_placeholder.warning('고려 사항을 선택하세요')
            else:
                selected_weights = {}
                for opt in options:
                    if st.session_state.get(f'check_{opt}', False):
                        try:
                            w = float(st.session_state.get(f'weight_{opt}', '0'))
                        except (ValueError, TypeError):
                            w = 0.0
                    else:
                        w = 0.0
                    selected_weights[opt] = w

                range_km = float(st.session_state.get('range_km', 1.5))
                radar_num = st.session_state.get('radar_num', '3')

                st.session_state['user_input'] = {
                    'range_km':        range_km,
                    'radar_num':       radar_num,
                    'selected_weights': selected_weights,
                }

                st.switch_page("pages/2_계산.py")


                
            
