import pandas as pd
import streamlit as st
from shapely import wkt
import geopandas as gpd
import folium
from streamlit_folium import st_folium
st.session_state.update(st.session_state)
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

# Data loading with correct column names
@st.cache_data
def load_noise_data():
    noise_df = pd.read_csv('data/cleaned/noise_map.csv')
    noise_df = noise_df.rename(columns={
        'Day/Night period': 'period',
        'Type': 'source_type'
    })
    noise_df['period'] = noise_df['period'].str.lower()
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

# Load data
noise_gdf = load_noise_data()
concert_df = load_concert_data()

# Modified default selections
DEFAULT_SOURCE = ["Road Traffic"]
NOISE_LEVEL_MAPPING = {
    1: 'Mild <55dB', 2: 'Noisy 55-60dB', 3: 'Loud 60-65dB',
    4: 'Louder 65-70dB', 5: 'Very Loud 70-75dB', 6: 'Extremely Loud >75dB',
    11: 'Mild <50dB', 12: 'Noisy 50-55dB', 13: 'Loud 55-60dB',
    14: 'Louder 60-65dB', 15: 'Very Loud 65-70dB', 16: 'Extremely Loud >70dB'
}

with st.sidebar:
    time_mode = st.radio(
        "time_period",
        options=["Day", "Night"],
        format_func=lambda x: f"🌞 {x}" if x == "Day" else f"🌙 {x}",
        horizontal=True,
        label_visibility="collapsed"
    ).lower()

    # Modified noise levels selection
    st.markdown("**🔊 Noise Levels**")
    
    # Define available levels based on time mode
    if time_mode == "day":
        available_levels = [1, 2, 3, 4, 5, 6]  # All day levels
        default_levels = [5, 6]  # Loud and very loud
    else:
        available_levels = [11, 12, 13, 14, 15, 16]  # All night levels
        default_levels = [15, 16]  # Loud and very loud

    selected_levels = st.multiselect(
        "Select Noise Levels:",
        options=available_levels,
        default=default_levels,
        format_func=lambda x: NOISE_LEVEL_MAPPING[x]
    )

    # Modified default noise source
    st.markdown("**🏭 Noise Sources**")
    noise_sources = st.multiselect(
        "Select Noise Sources:",
        options=noise_gdf['source_type'].unique(),
        default=DEFAULT_SOURCE
    )

    st.markdown("---")
    concert_date = st.date_input(
        "🎤 Concert Date",
        min_value=concert_df['Date'].min().date()
    )

# Data filtering
noise_filter = noise_gdf[
    (noise_gdf['source_type'].isin(noise_sources)) &
    (noise_gdf['period'] == time_mode) &
    (noise_gdf['legend'].isin(selected_levels))
]

concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]

# Map creation
m = folium.Map(
    location=(52.3676, 4.9041),  # Fixed initial position
    zoom_start=12,               # Fixed initial zoom
    tiles='CartoDB positron',
    control_scale=True,
    prefer_canvas=True,
    zoom_control=False
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
                tooltip=f"Source: {row['source_type']}<br>Level: {NOISE_LEVEL_MAPPING.get(level, 'N/A')}"
            ).add_to(m)

# Modified concert markers with purple circles
PURPLE_COLOR = '#9C27B0'  # Purple color matching the icon
for _, event in concert_filter.iterrows():
    folium.Marker(
        location=[event['Latitude'], event['Longitude']],
        popup=f"""<b>{event['Artist']}</b><br>
                {event['Venue']}<br>
                {event['Date'].strftime('%Y-%m-%d')}""",
        icon=folium.Icon(color='purple', icon='music', prefix='fa')
    ).add_to(m)
    
    # Add 50m radius circle[2,3](@ref)
    folium.Circle(
        location=[event['Latitude'], event['Longitude']],
        radius=50,
        color=PURPLE_COLOR,
        fill=True,
        fill_color=PURPLE_COLOR,
        fill_opacity=0.2,
        weight=2
    ).add_to(m)

# Map rendering (simplified version)
st_folium(
    m,
    key="main_map",
    width=1920,
    height=600,
    use_container_width=True,
    returned_objects=[],  # Don't return any map parameters
)