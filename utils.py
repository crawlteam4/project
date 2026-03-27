import streamlit as st




def apply_input_style():
    st.markdown("""
    <style>
    div[data-baseweb="input"],
    div[data-baseweb="base-input"] {
        background-color: #f0f2f6 !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {
        background-color: #f0f2f6 !important;
    }
    div[data-baseweb="textarea"] textarea {
        background-color: #f0f2f6 !important;
    }
    </style>
    """, unsafe_allow_html=True)
