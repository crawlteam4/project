import numpy as np
import pandas as pd
from get_data.get import *
from calculate.calculate import *
from visualize.visualize import *
from db.db import upload_result

st.set_page_config(layout="wide")


# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.error("로그인이 필요합니다.")
#     st.stop()  # 이 아래 코드는 실행되지 않음
    
with st.sidebar:
    st.write("📊 **전체 분석 진행률**")
    st.progress(100)
    st.success("✅ **최종: 결과 활용**\n\n완료된 분석을 다운로드해보세요.")
    st.divider()

st.title("데이터프레임")





results = st.session_state.get('final_df', None)

if results is None:
    st.info("계산을 먼저 실행해주세요.")
else:
    results.columns=['순위', '격자ID', '위도', '경도', '가중치 반영 점수','인구 밀도','건물 밀집도']
    st.subheader("후보지 결과 데이터프레임")
    st.dataframe(results)

    vac,but1=st.columns([8,1])
    with but1:
        with st.container(horizontal=True,horizontal_alignment='right'):
            st.download_button(
            label="Download CSV",
            data=results.to_csv(index=False).encode('utf-8'),
            file_name='candidate_sites.csv',
            mime='text/csv',
                )
            upload=st.button('Upload DB')
            if upload:
                upload_result(results)





