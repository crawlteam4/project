# 생각하는 그래프 후보지 
import streamlit as st

col1,col2=st.columns([1,2])

with col1:
    st.write('후보지별 점수 그래프')
    st.line_chart([6,4,1])
    st.caption('점수의 급락 지점을 제공하여 가장 최적의 후보지 개수를 시각화 하는 것에 도움을 준다.')

with col2:
    st.write('선택된 위치의 건물 개수 히트맵')