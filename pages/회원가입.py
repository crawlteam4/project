import streamlit as st
import pymysql

st.set_page_config(page_title="회원가입 | D-DAS", page_icon="images/technology.png",
                   layout="wide", initial_sidebar_state="collapsed")


def get_connection():
    return pymysql.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        charset="utf8mb4"
    )

def register_user(user_id: str, password: str, name: str, email: str) -> bool:
# sql 구문으로 MySQL에 사용자 정보 저장하는 함수    
    conn=get_connection()
    with conn.cursor() as cursor:
        sql = "INSERT INTO users (user_id, password, name, email) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (user_id, password, name, email))
        conn.commit()
    return True 


def is_duplicate_id(user_id: str) -> bool:
# sql 구문으로 MySQL에서 사용자 아이디 중복 여부 확인하는 함수  
    return False  # 연동 전까지 항상 중복 없음으로 처리


st.markdown("""
<style>
/* 로그인으로 돌아가기 링크 */
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

col1, col2 = st.columns([5, 1])
with col1:
    st.title('D-DAS :')
    st.subheader('Drone Defense Allocation System')
with col2:
    st.image('images/technology.png', width=200)

st.divider()

with st.container(border=True):
    st.markdown("#### 회원가입")
    st.write('')

    with st.form("signup_form"):
        user_id  = st.text_input("아이디", placeholder="영문, 숫자 조합 6자 이상")
        name     = st.text_input("이름",   placeholder="이름을 입력하세요")
        email    = st.text_input("이메일", placeholder="example@email.com")
        pw       = st.text_input("비밀번호",    type="password", placeholder="8자 이상")
        pw_check = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요")

        st.write('')
        submitted = st.form_submit_button("가입하기", use_container_width=True,
                                          type="primary")

    # 폼 제출 처리
    if submitted:
        # 입력값 검증
        if not all([user_id, name, email, pw, pw_check]):
            st.error("모든 항목을 입력해주세요.")
        elif len(user_id) < 6:
            st.error("아이디는 6자 이상이어야 합니다.")
        elif len(pw) < 8:
            st.error("비밀번호는 8자 이상이어야 합니다.")
        elif pw != pw_check:
            st.error("비밀번호가 일치하지 않습니다.")
        elif is_duplicate_id(user_id):
            st.error("이미 사용 중인 아이디입니다.")
        else:
            success = register_user(user_id, pw, name, email)
            if success:
                st.success("회원가입이 완료되었습니다! 로그인 페이지로 이동해주세요.")

    st.write('')
    col_a, col_b, col_c = st.columns([2, 1, 2])
    with col_b:
        st.page_link("DDAS.py", label="로그인으로 돌아가기")
