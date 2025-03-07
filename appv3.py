import pandas as pd
import streamlit as st
from shapely import wkt
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from streamlit_float import float_init, float_parent

#这个版本想要做好看的悬浮窗口但是失败，若想排错请随意


st.set_page_config(layout="wide")

float_init() #initialize float container

st.markdown("""
<style>
    /* 主容器样式 */
    .main .block-container {
        padding: 0 !important;
    }
    
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
    
    .map-container {
        position: absolute !important;
        left: 340px !important; 
        right: 20px !important;
        top: 20px !important;
        bottom: 20px !important;
        z-index: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# Load Data Functions
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

# Load Data
noise_gdf = load_noise_data()
concert_df = load_concert_data()

control_container = st.container()
with control_container:
    st.header("Control Board")
    selected_types = st.multiselect("Noise Source", options=noise_gdf['Type'].unique())
    selected_periods = st.multiselect("Time Period", options=noise_gdf['Day_Night_period'].unique())
    selected_legends = st.multiselect("Legend", options=noise_gdf['legend'].unique())
    concert_date = st.date_input("Date", min_value=concert_df['Date'].min().date())

# Data Filtering
noise_filter = noise_gdf[
    (noise_gdf['Type'].isin(selected_types)) &
    (noise_gdf['Day_Night_period'].isin(selected_periods)) &
    (noise_gdf['legend'].isin(selected_legends))
]
concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]

# Map Container to separate it from Floating Container
with st.container():
    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    m = folium.Map(
        location=[52.3676, 4.9041],
        zoom_start=12,
        tiles='CartoDB positron',
        control_scale=True
    )
    
    # Map elements
    for _, row in noise_filter.iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x, row=row: {
                'color': '#FF6B6B' if row['Day_Night_period'] == 'day' else '#4ECDC4',
                'weight': 1.5,
                'fillOpacity': 0.3
            },
            tooltip=f"Type: {row['Type']}<br>Time: {row['Day_Night_period']}"
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

# Float Container's css
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
float_parent(css=float_css) # something must be wrong with this line