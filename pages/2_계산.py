import streamlit as st
import os


st.set_page_config(layout="wide")

with st.container():
    col1, col2=st.columns([6,3])
    with col1:
        
        map_file = os.path.join(os.path.dirname(__file__), '../map.html')
        if os.path.exists(map_file):
            with open(map_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=700)
