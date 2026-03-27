import streamlit as st
import os



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

    with col2: 
        with st.container(border=True):
            options = ['전력시설', '정보통신시설', '국가 공공기관 시설', '교통 항공 항만 시설', '수원 시설', '지하공동구', '인구밀도 ',
                    '토지 이용 압축도', '산업 시설', '기지국', '병원', '과학연구', '교정 시설', '방송시설']

            for opt in options:
                st.toggle(opt, key=opt)

            st.write('')
            if st.button("Select", key=f"button_{opt}",use_container_width=True):
                selected = [opt for opt in options if st.session_state.get(opt, False)]
                

                
            

    


