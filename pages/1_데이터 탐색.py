import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from shapely.wkt import loads
from shapely.geometry import box
import json

# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.error("로그인이 필요합니다.")
#     st.stop()  # 이 아래 코드는 실행되지 않음
    
# =========================================================
# 1. 초기 설정 및 데이터 매핑
# =========================================================

@st.cache_resource
def get_engine():
    host, port, database, user, password = '127.0.0.1', 3306, "projectdb", "root", "catyou0929"
    return create_engine(f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4')

FACILITY_MAP = {
    "국가중요시설": {
        "전력시설 (electricity)": ["변전소"],
        "정보통신시설 (telecommunication)": ["통신망", "금융"],
        "국가 공공기관 시설 (public)": ["국가유산", "중앙행정기관", "지방행정기관"],
        "교통 항공 항만 시설 (transportation)": ["차량기지", "철도", "공항", "교량", "터널"],
        "수원 시설 (water)": ["지방정수장", "배수지"],
        "지하공동구 (infra)": ["공동구"],
        "산업 시설 (factory)": ["산업시설"],
        "병원 (hospital)": ["병원", "혈액검사센터", "혈액원"],
        "과학연구 (science)": ["과학연구"],
        "교정 시설 (prison)": ["교정시설"],
        "방송시설 (broadcast)": ["방송국"]
    },
    "RF신호 밀집도": {
        "기지국 (frequency)": ["기지국"]
    }
}

TABLE_NAME_MAP = {
    "전력시설 (electricity)": "electricity", "정보통신시설 (telecommunication)": "telecommunication",
    "국가 공공기관 시설 (public)": "public", "교통 항공 항만 시설 (transportation)": "transportation",
    "수원 시설 (water)": "water", "지하공동구 (infra)": "infra", "산업 시설 (factory)": "factory",
    "병원 (hospital)": "hospital", "과학연구 (science)": "science", "교정 시설 (prison)": "prison",
    "방송시설 (broadcast)": "broadcast", "기지국 (frequency)": "frequency"
}

GRID_MAP = {
    "인구 밀집도": "raw",
    "건물 고도&밀집도": "density"
}

# =========================================================
# 2. 데이터 처리 함수 (Business Logic)
# =========================================================

@st.cache_data
def load_facility_data(target_mids, sel_tag):
    engine = get_engine()
    all_df = []
    for m_disp in target_mids:
        table = TABLE_NAME_MAP.get(m_disp)
        if not table: continue
        
        query = f"SELECT name, latitude, longitude, tag FROM `{table}`"
        if sel_tag:
            tag_str = "', '".join(sel_tag)
            query += f" WHERE tag IN ('{tag_str}')"
        
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['mid_cat'] = m_disp
            all_df.append(df)
            
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

@st.cache_data
def load_grid_gdf(g_name):
    """새로운 파일 구조(Tag 없음, CRS 변환 필요)를 반영한 로드 함수"""
    engine = get_engine()
    table = GRID_MAP.get(g_name)
    if not table: return None

    # 1. 인구 밀집도 처리 (SW/NE 좌표 기반 격자 생성)
    if g_name == "인구 밀집도":
        query = f"SELECT 격자명 as gid, 밀집도 as value, sw_lat, sw_lng, ne_lat, ne_lng FROM `{table}` WHERE 밀집도 > 0"
        df = pd.read_sql(query, engine)
        if df.empty: return None
        
        # 좌표 컬럼을 이용하여 Polygon 생성
        df['geometry'] = df.apply(lambda r: box(r['sw_lng'], r['sw_lat'], r['ne_lng'], r['ne_lat']), axis=1)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
        
        display_name = "생활인구"
        gdf = gdf.rename(columns={'value': display_name})
        return gdf[['gid', display_name, 'geometry']]

    # 2. 건물 고도&밀집도 처리 (EPSG:5179 변환 필요)
    elif g_name == "건물 고도&밀집도":
        # WKT로 읽어와서 CRS 변환 수행
        query = f"SELECT gid, value, geometry FROM `{table}` WHERE value > 0"
        df = pd.read_sql(query, engine)
        if df.empty: return None
        
        df['geometry'] = df['geometry'].apply(loads)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:5179").to_crs(epsg=4326)
        
        display_name = "토지이용압축도"
        gdf = gdf.rename(columns={'value': display_name})
        gdf[display_name] = gdf[display_name].round(2)
        return gdf[['gid', display_name, 'geometry']]

    return None

# =========================================================
# 3. UI 함수 (UI Logic)
# =========================================================

def render_facility_tab():
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_main = st.multiselect("대분류 선택", list(FACILITY_MAP.keys()), placeholder="전체 조회")
    
    mid_opts = []
    main_list = sel_main if sel_main else list(FACILITY_MAP.keys())
    for m in main_list:
        mid_opts.extend(list(FACILITY_MAP[m].keys()))
    
    with c2:
        sel_mid = st.multiselect("중분류 선택", sorted(list(set(mid_opts))), placeholder="전체 조회")
    
    target_mids = sel_mid if sel_mid else mid_opts
    tag_opts = []
    for m in target_mids:
        for main in FACILITY_MAP:
            if m in FACILITY_MAP[main]:
                tag_opts.extend(FACILITY_MAP[main][m])
    
    with c3:
        sel_tag = st.multiselect("소분류(Tag) 선택", sorted(list(set(tag_opts))), placeholder="전체 조회")

    if st.button("시설물 데이터 조회", key="btn_f"):
        final_df = load_facility_data(target_mids, sel_tag)
        
        if not final_df.empty:
            st.info(f"📍 검색 결과: 총 {len(final_df)}개의 시설물을 찾았습니다.")
            csv_data = final_df.to_csv(index=False).encode('utf_8_sig')
            st.download_button(label="📥 시설물 결과 CSV 다운로드", data=csv_data, file_name='facility_analysis.csv', mime='text/csv')

            m = folium.Map(location=[final_df.latitude.mean(), final_df.longitude.mean()], zoom_start=11)
            mc = MarkerCluster(name="시설물 클러스터").add_to(m)
            for _, row in final_df.iterrows():
                popup_text = f"<b>{row['name']}</b><br>{row['mid_cat']}<br>Tag: {row['tag']}"
                folium.Marker(
                    [row['latitude'], row['longitude']], 
                    popup=folium.Popup(popup_text, max_width=250),
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(mc)
            
            folium.LayerControl().add_to(m)
            folium_static(m, width=1300, height=700)
        else:
            st.warning("조건에 해당하는 시설물 데이터가 없습니다.")

def render_grid_tab():
    """TAB 2: 격자 분석 화면 구성"""
    cc1, cc2 = st.columns([2, 1])
    with cc1:
        sel_grid = st.multiselect("분석할 격자 레이어 선택", list(GRID_MAP.keys()), default=list(GRID_MAP.keys()))
    
    COLOR_THEME = {"인구 밀집도": "YlOrRd", "건물 고도&밀집도": "PuBu"}

    if st.button("격자 데이터 조회", key="btn_g"):
        # 서울 중심 좌표로 지도 생성
        m_g = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles='cartodbpositron')
        gdfs_dict = {}

        for g_name in sel_grid:
            gdf = load_grid_gdf(g_name)
            if gdf is not None:
                display_col = gdf.columns[1] # '생활인구' 또는 '토지이용압축도'
                
                # 범례(Bins) 계산
                vals = gdf[display_col].dropna()
                thresholds = sorted(list(set([vals.min()] + vals.quantile([0.5, 0.8, 0.9, 0.95, 1.0]).tolist())))
                
                # 각 레이어별 Choropleth 추가
                folium.Choropleth(
                    geo_data=gdf, name=g_name, data=gdf,
                    columns=['gid', display_col], key_on='feature.properties.gid',
                    bins=thresholds, fill_color=COLOR_THEME.get(g_name, "Greens"),
                    fill_opacity=0.5, line_opacity=0.3, line_color='gray', highlight=True
                ).add_to(m_g)
                
                gdfs_dict[display_col] = gdf

        # --- 원래의 sjoin(Spatial Join) 통합 로직 복구 ---
        combined_gdf = None
        if "생활인구" in gdfs_dict and "토지이용압축도" in gdfs_dict:
            pop_gdf = gdfs_dict["생활인구"].copy()
            area_gdf = gdfs_dict["토지이용압축도"].copy()
            
            # 1. 인구 격자의 중심점(centroid) 생성 (결합 기준점)
            pop_gdf['centroid'] = pop_gdf.geometry.centroid
            
            # 2. sjoin 실행: 인구 중심점이 건물 격자 폴리곤 안에 포함되는지 확인
            # predicate='within'을 사용하여 공간적으로 결합
            combined_gdf = gpd.sjoin(
                pop_gdf.set_geometry('centroid'), 
                area_gdf[['토지이용압축도', 'geometry']], 
                how='left', 
                predicate='within'
            )
            
            # 3. geometry를 다시 폴리곤으로 복구하고 불필요한 컬럼 정리
            combined_gdf = combined_gdf.set_geometry('geometry').drop(columns=['centroid', 'index_right'], errors='ignore')
            
        elif len(gdfs_dict) == 1:
            combined_gdf = list(gdfs_dict.values())[0]

        # --- 통합 툴팁 레이어 및 다운로드 버튼 ---
        if combined_gdf is not None:
            # GeoJSON 다운로드 버튼
            geojson_data = combined_gdf.to_json()
            st.download_button(label="🌍 격자 통합 GeoJSON 다운로드", data=geojson_data, file_name='grid_analysis.geojson', mime='application/json')
            
            # --- 툴팁 필드 및 별칭(Aliases) 동적 구성 ---
            active_fields = ['gid']
            active_aliases = ['ID:'] # gid에 대응하는 별칭
            
            if '생활인구' in combined_gdf.columns:
                active_fields.append('생활인구')
                active_aliases.append('인구밀도:')
                
            if '토지이용압축도' in combined_gdf.columns:
                active_fields.append('토지이용압축도')
                active_aliases.append('건물압축도:')

            # 투명한 레이어를 위에 덮어 툴팁 구현
            folium.GeoJson(
                combined_gdf,
                name="통합 데이터 툴팁",
                style_function=lambda x: {'fillColor': 'transparent', 'color': 'transparent'},
                tooltip=folium.GeoJsonTooltip(
                    fields=active_fields, 
                    aliases=active_aliases,  # 개수를 맞춘 동적 별칭 리스트 사용
                    localize=True
                )
            ).add_to(m_g)

        folium.LayerControl().add_to(m_g)
        folium_static(m_g, width=1300, height=750)

# =========================================================
# 4. 앱 실행
# =========================================================

def main():
    st.set_page_config(layout="wide", page_title="C-UAS 통합 분석")
    
    with st.sidebar:
        st.write("📊 **전체 분석 진행률**")
        st.caption("현재: 1단계 (25%)")
        st.progress(25)
        st.info("🔎 **1단계: 데이터 탐색**\n\n서울시 전역의 기초 데이터를 자유롭게 탐색해 보세요.")


    st.title("입지 데이터 탐색")
    st.write("")

    with st.expander("🔍 **이 페이지에서는 무엇을 하나요?**", expanded=False):
        st.write("본 페이지는 서울시의 **시설물(지점)**, **인구/건물(격자)** 데이터를 탐색하는 단계입니다.")
        st.write("") 

        col1, col2 = st.columns([2,5])
        
        with col1:
            # 탭 1에 대한 설명
            st.markdown("##### 📍 시설물 지점 분석 (Point)")
            with st.container(border=True, width=400):
                st.markdown("""
                - **데이터**: 분류별 시설 위치
                - **조작**: `대분류` → `중분류` → `소분류` 순으로 선택
                - **특징**: 서울시 내 건물이나 시설의 정확한 위치 확인
                """)
                
        with col2:
            # 탭 2에 대한 설명
            st.markdown("##### 🟩 인구/건물 격자 분석 (Grid)")
            with st.container(border=True, width=400):
                st.markdown("""
                - **데이터**: 생활인구 밀집도, 토지이용 압축도
                - **조작**: 별도 분류 없이 **인구, 건물 선택**
                - **특징**: 서울시 전역의 밀집도/고도 흐름 파악
                """)

        st.divider()
        
        # 공통 이용 방법
        st.markdown("##### 🛠️ 이용 방법")
        st.caption("""
            1️⃣ 하단 탭 메뉴에서 **시설물 or 인물/건물**을 먼저 선택하세요.  
            2️⃣ 원하는 **데이터 조건**을 설정한 후 **[데이터 조회]** 버튼을 클릭하세요.  
            3️⃣ 지도에서 결과를 확인하고, 필요한 경우 하단에서 **CSV 파일로 다운로드**하세요.
            """)
        
        st.info("💡 **Tip:** 데이터를 확인하고 다음 단계에서 어떤 변수를 얼마만큼의 가중치로 설정할 건지 고려해보세요")

    st.write("")
    
    tab1, tab2 = st.tabs(["📍 시설물 지점 분석", "🟩 인구/건물 격자 분석"])
    with tab1:
        render_facility_tab()
    with tab2: 
        render_grid_tab()

if __name__ == "__main__":
    main()