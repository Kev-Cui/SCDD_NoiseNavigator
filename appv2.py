import pandas as pd
import streamlit as st
from shapely import wkt
import geopandas as gpd
import folium
from streamlit_folium import folium_static

# 配置页面 + 全屏样式
st.set_page_config(layout="wide")
st.markdown("""
<style>
    /* 全屏布局 */
    html, body, #root, .reportview-container {
        height: 100%;
        margin: 0;
        padding: 0;
    }
    
    /* 隐藏所有默认元素 */
    .main .block-container {
        padding: 0;
        max-width: 100%;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        width: 300px !important;
        background: rgba(255,255,255,0.9);
        padding: 20px;
        box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        z-index: 100;
    }
    
    /* 地图容器全屏 */
    .stMap {
        position: fixed !important;
        top: 0;
        left: 300;
        right: 0;
        bottom: 0;
        z-index: 0;
    }
    
    /* 隐藏标题 */
    h1 {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 数据加载函数
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

# 侧边栏控制面板
with st.sidebar:
    # 噪声数据筛选
    selected_types = st.multiselect(
        "噪声类型",
        options=noise_gdf['Type'].unique(),
        # default=noise_gdf['Type'].unique()
    )
    selected_periods = st.multiselect(
        "时段",
        options=noise_gdf['Day_Night_period'].unique(),
        default=noise_gdf['Day_Night_period'].unique()
    )
    selected_legends = st.multiselect(
        "图例分类",
        options=noise_gdf['legend'].unique(),
        # default=noise_gdf['legend'].unique()
    )

    # 演唱会数据筛选
    concert_date = st.date_input(
        "演唱会日期",
        min_value=concert_df['Date'].min().date()
    )

# 数据过滤
noise_filter = noise_gdf[
    (noise_gdf['Type'].isin(selected_types)) &
    (noise_gdf['Day_Night_period'].isin(selected_periods)) &
    (noise_gdf['legend'].isin(selected_legends))
]

concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]

# 创建地图
m = folium.Map(
    location=[52.3676, 4.9041],
    zoom_start=12,
    tiles='CartoDB positron',
    control_scale=True
)

# 添加噪声多边形
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

# 添加演唱会标记
for _, event in concert_filter.iterrows():
    folium.Marker(
        location=[event['Latitude'], event['Longitude']],
        popup=f"""<b>{event['Artist']}</b><br>
                {event['Venue']}<br>
                {event['Date'].strftime('%Y-%m-%d')}""",
        icon=folium.Icon(color='purple', icon='music', prefix='fa')
    ).add_to(m)

# 显示全屏地图
folium_static(m, width=1920, height=600)