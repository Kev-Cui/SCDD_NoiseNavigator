import pandas as pd
import streamlit as st
from shapely import wkt
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from streamlit_float import float_init, float_parent

#这个版本想要做好看的悬浮窗口但是失败，若想排错请随意

# 配置页面（必须第一个命令）
st.set_page_config(layout="wide")

# 初始化浮动容器
float_init()

# 设置全局样式
st.markdown("""
<style>
    /* 主容器样式 */
    .main .block-container {
        padding: 0 !important;
    }
    
    /* 浮动控制面板样式 */
    .floating-panel {
        position: fixed !important;
        top: 20px !important;
        left: 20px !important;
        width: 300px !important;
        max-height: 80vh;
        background: rgba(255,255,255,0.95);
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        z-index: 9999;
        overflow-y: auto;
    }
    
    /* 地图容器样式 */
    .map-container {
        position: absolute !important;
        left: 340px !important;  /* 控制面板宽度 + 边距 */
        right: 20px !important;
        top: 20px !important;
        bottom: 20px !important;
        z-index: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# 数据加载函数（保持原样）
@st.cache_data
def load_noise_data():
    noise_df = pd.read_csv('data/cleaned/noise_map.csv')
    noise_df = noise_df.rename(columns={'Day/Night period': 'Day_Night_period'})
    noise_df['geometry'] = noise_df['WKT_LNG_LAT'].apply(wkt.loads)
    return gpd.GeoDataFrame(noise_df, geometry='geometry').set_crs(epsg=4326)

@st.cache_data
def load_concert_data():
    try:
        concert_df = pd.read_csv('data/cleaned/concert_plan.csv', encoding='utf-8')
    except UnicodeDecodeError:
        concert_df = pd.read_csv('data/cleaned/concert_plan.csv', encoding='latin1')
    concert_df.replace('Unknown', pd.NA, inplace=True)
    concert_df['Date'] = pd.to_datetime(concert_df['Date'])
    concert_df[['Latitude', 'Longitude']] = concert_df[['Latitude', 'Longitude']].apply(pd.to_numeric, errors='coerce')
    return concert_df.dropna(subset=['Latitude', 'Longitude'])

# 加载数据
noise_gdf = load_noise_data()
concert_df = load_concert_data()

control_container = st.container()
with control_container:
    st.header("控制面板")
    selected_types = st.multiselect("噪声类型", options=noise_gdf['Type'].unique())
    selected_periods = st.multiselect("时段", options=noise_gdf['Day_Night_period'].unique())
    selected_legends = st.multiselect("图例分类", options=noise_gdf['legend'].unique())
    concert_date = st.date_input("选择日期", min_value=concert_df['Date'].min().date())

# 数据过滤（保持原样）
noise_filter = noise_gdf[
    (noise_gdf['Type'].isin(selected_types)) &
    (noise_gdf['Day_Night_period'].isin(selected_periods)) &
    (noise_gdf['legend'].isin(selected_legends))
]
concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]

# 创建地图容器
with st.container():
    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    m = folium.Map(
        location=[52.3676, 4.9041],
        zoom_start=12,
        tiles='CartoDB positron',
        control_scale=True
    )
    
    # 添加地图元素（保持原样）
    for _, row in noise_filter.iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x, row=row: {
                'color': '#FF6B6B' if row['Day_Night_period'] == 'day' else '#4ECDC4',
                'weight': 1.5,
                'fillOpacity': 0.3
            },
            tooltip=f"类型: {row['Type']}<br>时段: {row['Day_Night_period']}"
        ).add_to(m)
    
    for _, event in concert_filter.iterrows():
        folium.Marker(
            location=[event['Latitude'], event['Longitude']],
            popup=f"""<b>{event['Artist']}</b><br>
                    {event['Venue']}<br>
                    {event['Date'].strftime('%Y-%m-%d')}""",
            icon=folium.Icon(color='purple', icon='music', prefix='fa')
        ).add_to(m)
    
    folium_static(m)
    st.markdown('</div>', unsafe_allow_html=True)

# ✅ 正确调用位置（在容器外部绑定浮动样式）
float_css = """
position: fixed;
top: 20px;
left: 20px;
width: 300px;
max-height: 80vh;
background: rgba(255,255,255,0.95);
border-radius: 8px;
padding: 15px;
box-shadow: 0 2px 10px rgba(0,0,0,0.1);
z-index: 9999;
overflow-y: auto;
"""
float_parent(css=float_css)