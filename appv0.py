import pandas as pd
import json
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import streamlit as st
from shapely import wkt

# Example JSON data as a Python list of dictionaries
json_data = json.load(open('data/translated/noise map.json'))

# Convert the JSON data to a Pandas DataFrame
data = pd.DataFrame(json_data)

# Function to parse WKT and return a GeoDataFrame
def parse_wkt_to_geodataframe(data, wkt_column):
    # Parse WKT strings into geometry objects
    data['geometry'] = data[wkt_column].apply(wkt.loads)
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(data, geometry='geometry')
    gdf = gdf.set_crs(epsg=4326)
    return gdf

# Parse the WKT_LNG_LAT column to create a GeoDataFrame
gdf = parse_wkt_to_geodataframe(data, 'WKT_LNG_LAT')

# Streamlit 界面
st.title("Amsterdam Noise Data")
st.sidebar.header("Legend Filter")

# 图例选择器
legends = gdf['legend'].unique().tolist()
selected_legends = st.sidebar.multiselect(
    "Select legends to display:",
    options=legends,
    default=legends
)

# 过滤数据
filtered_gdf = gdf[gdf['legend'].isin(selected_legends)]

# 创建地图
m = folium.Map(
    location=[52.3676, 4.9041], 
    zoom_start=12,
    tiles='CartoDB positron'  # 更简洁的地图样式
)

# 添加地理数据（使用地理坐标系）
folium.GeoJson(
    filtered_gdf,
    style_function=lambda x: {'color': 'blue', 'weight': 1},
    tooltip=folium.GeoJsonTooltip(fields=['legend', 'source'])
).add_to(m)

# 显示地图
folium_static(m, width=1200, height=600)