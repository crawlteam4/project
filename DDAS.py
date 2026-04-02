import streamlit as st
import pandas as pd
import pymysql

# DESIGN implement changes to the standard streamlit UI/UX
st.set_page_config(page_title="D-DAS", page_icon="images/technology.png", layout="wide", initial_sidebar_state="collapsed")
    
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

def get_connection():
    return pymysql.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        charset="utf8mb4"
    )

with st.sidebar:
    st.write("📊 **전체 분석 진행률**")
    st.progress(10)
    st.info("🔎 **0단계: 로그인 및 가이드**\n\n가이드를 확인하고 로그인하세요.")
    st.divider()

# 회원가입 스타일
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

# 제 맘대로 drone defense allocaton system -> D - DAS로 지어봤습니다 ㅎㅎ
with st.container():
    col1, col2= st.columns([3.73, 1])
    with col1:
        st.title("대드론 방어체계")
        st.write( '(D-DAS : Drone Defense Allocation Service)')
        st.write("")
        st.write("💡 **안내**")
        st.caption("본 서비스는 국내 도심 환경을 고려한 대드론 방어체계(C-UAS) 최적 입지 분석을 제공합니다.")
    with col2:
        st.write("")
        st.write("")
        st.image('images/technology.png', width=200)

st.divider()

chan1, id_log=st.columns([5,2])

with chan1:
    st.subheader("🚀 이용 가이드")
    st.write("처음 방문하셨나요? 아래 순서대로 분석을 진행해 보세요.")

    st.divider() 
    st.write("") 
    

    # 2. 카드 섹션 (파란색 숫자 아이콘 + 간결한 문구)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container(border=True):
            st.markdown("### 1️⃣")
            st.markdown("### **데이터 탐색**")
            st.write('')
            st.caption("사이드바: 1_입지 분석")
            st.write("서울시 전역의 **Raw Data를 지도에서 확인**하고, 데이터 분포 현황을 파악합니다.")

    with col2:
        with st.container(border=True):
            st.markdown("### 2️⃣")
            st.markdown("### **분석 설계**")
            st.write('')
            st.caption("사이드바: 2_후보지 조건 설정")
            st.write("분석할 **격자 영역을 생성**하고, 방어무기 **사정거리** 및 시설별 **가중치**를 설정합니다.")

    with col3:
        with st.container(border=True):
            st.markdown("### 3️⃣")
            st.markdown("### **후보지 계산**")
            st.write('')
            st.caption("사이드바: 3_후보지 계산")
            st.write("설정된 시나리오를 바탕으로 **최적의 배치 지점**을 알고리즘이 자동 산출합니다.")

    with col4:
        with st.container(border=True):
            st.markdown("### 4️⃣")
            st.markdown("### **결과 활용**")
            st.write('')
            st.caption("사이드바: 4~6번 페이지")
            st.write("도출된 후보지의 **상세 점수를 확인**하고 여러 시나리오를 상호 비교합니다.")


st.markdown("---")
# 아래에 추가적인 서비스 소개나 공지사항 배치
        


with id_log:
    # border=True를 유지하여 시각적 구분을 명확히 함
    with st.container(border=True, height=471):
        # 1. 상단 타이틀: 
        st.subheader("🔐 시스템 로그인")
        st.write('')
        st.caption("D-DAS 서비스 이용을 위해 로그인하세요.")
        st.write('')        
        
        # 2. 간격 조절: 
        # label_visibility='collapsed'를 쓰면 위아래 간격이 최소화
        input_sender = st.text_input('ID', placeholder='아이디를 입력하세요', key='login_id', label_visibility='collapsed')
        input_recipient = st.text_input('PW', placeholder='비밀번호를 입력하세요', type='password', key='login_pw', label_visibility='collapsed')
        
        # 버튼 위쪽에만 살짝 간격을 주어 클릭 실수를 방지
        st.write("") 
        st.write('')
        # 3. 로그인 버튼: type="primary"로 색상 강조 및 가로 꽉 채우기
        sub_butt = st.button('로그인', use_container_width=True, type="primary")

        # 4. 박스 내부 하단 정리
        st.divider()
        
        # 회원가입 안내를 2열로 배치하여 박스 하단 밀도를 높임
        c1, c2 = st.columns([5, 2])
        with c1:
            st.caption("계정이 없으신가요?")
        with c2:
            st.page_link("pages/회원가입.py", label="회원가입")
        



if sub_butt:
    conn=get_connection()
    with conn.cursor() as cursor:
        sql = "SELECT * FROM users WHERE user_id = %s AND password = %s"
        cursor.execute(sql, (input_sender, input_recipient))
        
        if cursor.fetchone():
            st.session_state.logged_in = True
            st.switch_page("pages/1_데이터 탐색.py")
            
        