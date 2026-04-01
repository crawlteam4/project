import streamlit as st
from sqlalchemy import create_engine, text
from get_data.get import *

def load_data(data_list):
    engine = get_engine_server(db_name=None)
    dfs1 = get_all_data_server(engine, data_list)
    disconnect_db(engine)
    return dfs1
