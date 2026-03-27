import streamlit as st
import pandas as pd


# DESIGN implement changes to the standard streamlit UI/UX
st.set_page_config(page_title="D-DAS", page_icon="images/technology.png", layout="wide", initial_sidebar_state="collapsed")
    
# 제 맘대로 drone defense allocaton system -> D - DAS로 지어봤습니다 ㅎㅎ
with st.container():
    col1, col2= st.columns([5, 1])
    with col1:
        st.title('D-DAS :')
        st.subheader( 'Drone Defense Allocation System')
    with col2:
        st.image('images/technology.png', width=200)

st.divider()

with st.container(border=True):
    st.write('')
    st.write('')
    input_sender = st.text_input('', placeholder='id')

    input_recipient = st.text_input('',placeholder='password')
    st.write('')
    st.write('')

    sub_butt=st.button('Submit',use_container_width=True)
    st.write('')
    st.write('')

if sub_butt:
    st.switch_page("pages/1_사용자입력.py")
    # 이거는 이후에 로컬 환경에서 작동시킬 때는 my sql이랑 연동해서 
    # 로그인 가능한지 확인해서 page 넘어갈 수 있도록 할 것입니다. 
        