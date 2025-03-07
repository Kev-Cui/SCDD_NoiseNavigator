import pandas as pd
import streamlit as st
from shapely import wkt
import geopandas as gpd
import folium
from streamlit_folium import st_folium

THEME_COLOR = {
    'primary': '#6C9BCF',
    'secondary': '#A8D5BA',
    'day_colors': ['#FFF9C4', '#FFF176', '#FFD54F', '#FFB300', '#FF8F00', '#FF6F00'],
    'night_colors': ['#80CBC4', '#4DB6AC', '#26A69A', '#009688', '#00897B', '#00796B']
}

st.set_page_config(layout="wide")
st.markdown(f"""
<style>
    .stMultiSelect label p {{
        font-size: 14px !important;
        margin-bottom: 8px !important;
    }}
</style>
""", unsafe_allow_html=True)

# Initialize map state
if 'map_state' not in st.session_state:
    st.session_state.map_state = {
        'center': (52.3676, 4.9041),
        'zoom': 12,
        'bounds': None
    }

# Data loading with correct column names
@st.cache_data
def load_noise_data():
    noise_gdf = pd.read_csv('data/cleaned/noise_map.csv')
    noise_gdf = noise_gdf.rename(columns={
        'Day/Night period': 'period',
        'Type': 'source_type',
        'legend': 'legend'  # 确保列名正确
    })
    noise_gdf['period'] = noise_gdf['period'].str.lower()
    noise_gdf['geometry'] = noise_gdf['WKT_LNG_LAT'].apply(wkt.loads)
    return gpd.GeoDataFrame(noise_gdf, geometry='geometry').set_crs(epsg=4326)

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

# Load data
noise_gdf = load_noise_data()
concert_df = load_concert_data()

# Sidebar controls with correct column reference
with st.sidebar:
    time_mode = st.radio(
        "time_period",
        options=["Day", "Night"],
        format_func=lambda x: f"🌞 {x}" if x == "Day" else f"🌙 {x}",
        horizontal=True,
        label_visibility="collapsed"
    ).lower()

    # Noise levels selection
    st.markdown("**🔊 Noise Levels**")
    noise_level_mapping = {
        1:'Mild <55dB', 2:'Noisy 55-60dB', 3:'Loud 60-65dB',
        4:'Louder 65-70dB', 5:'Very Loud 70-75dB', 6:'Extremely Loud >75dB',
        11:'Mild <50dB', 12:'Noisy 50-55dB', 13:'Loud 55-60dB',
        14:'Louder 60-65dB', 15:'Very Loud 65-70dB', 16:'Extremely Loud >70dB'
    }
    
    available_levels = [k for k in noise_level_mapping if k <10] if time_mode == "day" else [k for k in noise_level_mapping if k >=10]
    
    selected_levels = st.multiselect(
        "Select Noise Levels:",
        options=available_levels,
        default=available_levels,
        format_func=lambda x: noise_level_mapping[x]
    )
    
    # Corrected column name reference here
    st.markdown("**🏭 Noise Sources**")
    noise_sources = st.multiselect(
        "Select Noise Sources:",
        options=noise_gdf['source_type'].unique(),  # Use renamed column
        default=noise_gdf['source_type'].unique()
    )
    
    st.markdown("---")
    concert_date = st.date_input(
        "🎤 Concert Date",
        min_value=concert_df['Date'].min().date()
    )

# Data filtering with correct column names
noise_filter = noise_gdf[
    (noise_gdf['source_type'].isin(noise_sources)) &  # Use renamed column
    (noise_gdf['period'] == time_mode) &
    (noise_gdf['legend'].isin(selected_levels))
]

concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]

# Map creation and visualization
m = folium.Map(
    location=list(st.session_state.map_state['center']),
    zoom_start=st.session_state.map_state['zoom'],
    tiles='CartoDB positron',
    control_scale=True,
    prefer_canvas=True
)

if not noise_filter.empty:
    for _, row in noise_filter.iterrows():
        level = row['legend']
        color_index = (level % 10) - 1 if level < 10 else (level // 10) - 1
        
        color_scheme = THEME_COLOR['day_colors'] if time_mode == "day" else THEME_COLOR['night_colors']
        border_color = "#FFA000" if time_mode == "day" else "#00796B"
        
        if 0 <= color_index < len(color_scheme):
            folium.GeoJson(
                row['geometry'],
                style_function=lambda x, fill=color_scheme[color_index], border=border_color: {
                    'fillColor': fill,
                    'color': border,
                    'weight': 1.5,
                    'fillOpacity': 0.5
                },
                tooltip=f"Source: {row['source_type']}<br>Level: {noise_level_mapping.get(level, 'N/A')}"
            ).add_to(m)
else:
    st.warning("No noise data available with current filters")

# 演唱会标记（保持原样）
for _, event in concert_filter.iterrows():
    folium.Marker(
        location=[event['Latitude'], event['Longitude']],
        popup=f"""<b>{event['Artist']}</b><br>
                {event['Venue']}<br>
                {event['Date'].strftime('%Y-%m-%d')}""",
        icon=folium.Icon(color='purple', icon='music', prefix='fa')
    ).add_to(m)

# 地图渲染（保持原样）
map_state = st_folium(
    m,
    key="main_map",
    width=1920,
    height=600,
    returned_objects=["zoom", "center", "bounds"],
    use_container_width=True
)

# 更新地图状态
if map_state and map_state.get("center") and map_state.get("zoom"):
    new_center = (map_state["center"]["lat"], map_state["center"]["lng"])
    new_zoom = map_state["zoom"]
    
    if (new_center != st.session_state.map_state['center'] or 
        new_zoom != st.session_state.map_state['zoom']):
        st.session_state.map_state.update({
            "center": new_center,
            "zoom": new_zoom,
            "bounds": map_state.get("bounds")
        })
        st.rerun()