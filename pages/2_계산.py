import streamlit as st
import os

st.set_page_config(layout="wide")

map_path = os.path.join(os.path.dirname(__file__), '../map.html')


def render_map(col):
    with col:
        if os.path.exists(map_path):
            with open(map_path, 'r', encoding='utf-8') as f:
                html = f.read()
            st.components.v1.html(html, height=700)


def render_input_summary(col):
    """session_state['user_input']을 오른쪽 컬럼에 예쁘게 표시"""
    with col:
        data = st.session_state.get('user_input')

        if data is None:
            st.info('사용자 입력 페이지에서 값을 입력하고 Select를 눌러주세요.')
            return

        # ── 상단 요약 카드 ────────────────────────────────────────
        with st.container(border=True):
            st.markdown('#### 입력 요약')

            c1, c2 = st.columns(2)
            c1.metric('사정 거리', f"{data['range_km']} km")
            c2.metric('후보지 수', f"{data['radar_num']} 개")

        # ── 선택된 카테고리 & 가중치 ──────────────────────────────
        active = {cat: w for cat, w in data['selected_weights'].items() if w > 0}

        with st.container(border=True):
            st.markdown(f'#### 선택 카테고리  `{len(active)}개`')

            if active:
                # 가중치 내림차순 정렬
                for cat, w in sorted(active.items(), key=lambda x: x[1], reverse=True):
                    bar_pct = int(w * 100 / max(active.values()) * 100) / 100  # 0~100 스케일
                    st.markdown(
                        f"""
                        <div style="margin-bottom:6px">
                            <div style="display:flex; justify-content:space-between; font-size:13px">
                                <span>{cat}</span>
                                <span style="color:#888">{w:.5f}</span>
                            </div>
                            <div style="background:#e0e0e0; border-radius:4px; height:8px">
                                <div style="width:{bar_pct}%; background:#4c8bf5;
                                            border-radius:4px; height:8px"></div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.caption('선택된 카테고리가 없습니다.')


def main():
    with st.container():
        col1, col2 = st.columns([6, 3])
        render_map(col1)
        render_input_summary(col2)


main()