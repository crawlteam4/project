import streamlit as st
import sys
import os

from utils import apply_input_style


# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.error("로그인이 필요합니다.")
#     st.stop()  # 이 아래 코드는 실행되지 않음
    
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

# with st.sidebar:
#     st.write("📊 **전체 분석 진행률**")
#     st.progress(50)
#     st.info("⚙️ **2단계: 분석 설계**\n\n격자를 생성하고 원하는 입력값과 고려변수를 선택해 보세요.")
#     st.divider()

with st.sidebar:


    st.markdown("### 📋 분석 진행 현황")
    
    # 진행률을 숫자로 보여주는 대신 간결한 텍스트로 대체
    st.caption("전체 공정률: 50%")


    
    # 각 단계를 하나로 묶음
    st.write("✅ **1. 데이터 탐색**")
    st.write("🔵 **2. 분석 설계** (진행 중)")
    st.write("⚪ **3. 후보지 계산**")
    st.write("⚪ **4. 결과 확인**")

    st.divider()
    # 상세 가이드는 가장 중요한 핵심 한 문장만
    st.info("**2단계: 분석 설계**\n\n격자를 생성하고 분석에 사용할 변수와 가중치를 설정해 주세요.")


st.title('D-DAS',text_alignment='right')

col1, col2 = st.columns([6, 3])

with col2:
    st.caption( 'Drone Defense Allocation System',text_alignment='right')


with st.expander("⚙️ **이 페이지에서는 무엇을 하나요?**", expanded=False): # 중요하므로 펼쳐둠
    st.write("서울시 내 집중 방어 구역을 선택하고, 장비 스펙과 시설별 중요도를 설정하는 단계입니다.")
    st.write("")

    help_tab1, help_tab2 = st.tabs(["📋 주요 설정 항목", "📸 따라하기 가이드"])
    
    with help_tab1:
        # 비율을 조절하여 텍스트가 너무 한 줄로 늘어지지 않게 함
        col1, col2, _ = st.columns([0.4, 0.4, 0.2]) 
        with col1:
            st.info("**📍 격자 생성 (Grid)**")
            st.markdown("""
            - 지도 위 클릭으로 분석 영역 설정
            - 격자 크기(100m 등) 조정
            - 수계 감지로 불필요한 영역 제외
            """)
        with col2:
            st.success("**🎯 방어 조건 설정**")
            st.markdown("""
            - 사거리(km) 및 후보지 개수 설정
            - 보호 대상 시설 선택
            - 시설별 가중치 부여
            """)

    with help_tab2:
        st.markdown("##### **[따라하기: 분석 설계 3단계]**")
        st.write("")

        # --- STEP 1 ---
        # 이미지와 설명을 7:3 비율로 가로 배치하여 이미지를 크게 보여줌
        c1_img, c1_txt = st.columns([0.7, 0.3])
        with c1_img:
            st.image('images/guide1.png', use_container_width=True) # 컬럼 너비에 맞춤
        with c1_txt:
            st.markdown("#### **1. 영역 지정**")
            st.markdown("- 지도 위를 **자유롭게 클릭**하여 방어하고 싶은 지역을 닫힌 다각형 형태로 그리세요.")
        
        st.divider() # 단계별 구분선

        # --- STEP 2 ---
        c2_img, c2_txt = st.columns([0.7, 0.3])
        with c2_img:
            st.image('images/guide2.png', use_container_width=True)
        with c2_txt:
            st.markdown("#### **2. 격자 생성**")
            # 강조색 활용
            st.markdown("""
            - 우측 생성기에서 **:blue[[격자 크기]]** 설정
            - **:orange[[수계 감지]]** 버튼 클릭
            - **:green[[격자 생성]]** 버튼 클릭 후 저장
            """)

        st.divider()

        # --- STEP 3 ---
        c3_img, c3_txt = st.columns([0.7, 0.3])
        with c3_img:
            st.image('images/guide3.png', use_container_width=True)
        with c3_txt:
            st.markdown("#### **3. 가중치 선택**")
            st.markdown("""
            - **:orange[장비 사거리]** 및 **:green[후보지 수]** 입력
            - 보호가 필요한 시설 체크
            - 시설 체크 시 자동으로 뜨는 **:blue[가중치 값]** 입력 (default 값 제공)
            - 최하단 **:red[[Select]]** 버튼 클릭
            """)

    st.divider()
    # 주의사항을 st.warning으로 더 강력하게 표시
    st.warning("⚠️ **주의**: 반드시 [따라하기 가이드] 순서대로 진행해야 정상적으로 계산이 실행됩니다.")

st.divider()

with st.container():
    col1, col2=st.columns([7,2])
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

            options = ['전력시설', '정보통신시설', '국가 공공기관 시설', '교통 항공 항만 시설', '수원 시설', '지하공동구',
                     '산업 시설', '기지국', '병원', '과학연구', '교정 시설', '방송시설']
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
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        checked = st.checkbox(opt, key=f'check_{opt}')
                    with c2:
                        if checked:
                            st.text_input('가중치', value=default_weights[opt], key=f'weight_{opt}', label_visibility='collapsed', placeholder='가중치')

            st.write('')
        warn_placeholder = st.empty()

        if st.button("Select", key=f"button_{opt}", use_container_width=True, type='primary'):
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
                st.session_state.pop('calc_results', None)

                st.switch_page("pages/3_후보지 계산.py")


                
            
