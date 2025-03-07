import pandas as pd
import streamlit as st
from shapely import wkt
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# Define theme colors
THEME_COLOR = {
    'primary': '#6C9BCF',
    'secondary': '#A8D5BA',
    'background': '#F8F9FA'
}

# Configure page layout
st.set_page_config(layout="wide")
st.markdown(f"""
<style>
    /* Full-screen layout */
    html, body, #root, .reportview-container {{
        height: 100%;
        margin: 0;
        padding: 0;
    }}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {{
        width: 300px !important;
        background: #90EE90 !important;  # 修改为浅绿色（原值：rgba(248, 249, 250, 0.95))
        padding: 20px;
        border-radius: 0 12px 12px 0 !important;
        box-shadow: 4px 0 15px rgba(0,0,0,0.08) !important;
    }}

    /* Map container styling */
    .stMap {{
        position: fixed !important;
        top: 0 !important;
        left: 300px !important;
        right: 0 !important;
        bottom: 0 !important;
        margin: 0 !important;
    }}

    .main .block-container {{
        padding: 0 !important;
        max-width: unset !important;
    }}
</style>
""", unsafe_allow_html=True)

# Initialize map state with proper structure
if 'map_state' not in st.session_state:
    st.session_state.map_state = {
        'center': (52.3676, 4.9041),
        'zoom': 12,
        'bounds': None
    }

# Data loading functions
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

# Load data
noise_gdf = load_noise_data()
concert_df = load_concert_data()

# Sidebar controls
with st.sidebar:
    selected_types = st.multiselect(
        "Noise Type",
        options=noise_gdf['Type'].unique()
    )
    selected_periods = st.multiselect(
        "Time Period",
        options=noise_gdf['Day_Night_period'].unique(),
        default=noise_gdf['Day_Night_period'].unique()
    )
    selected_legends = st.multiselect(
        "Legend Category",
        options=noise_gdf['legend'].unique()
    )
    concert_date = st.date_input(
        "Concert Date",
        min_value=concert_df['Date'].min().date()
    )

# Data filtering
noise_filter = noise_gdf[
    (noise_gdf['Type'].isin(selected_types)) &
    (noise_gdf['Day_Night_period'].isin(selected_periods)) &
    (noise_gdf['legend'].isin(selected_legends))
]

concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]

# Map creation with state preservation
m = folium.Map(
    location=list(st.session_state.map_state['center']),
    zoom_start=st.session_state.map_state['zoom'],
    tiles='CartoDB positron',
    control_scale=True,
    prefer_canvas=True  # Better performance
)

# Add noise polygons
for _, row in noise_filter.iterrows():
    folium.GeoJson(
        row['geometry'],
        style_function=lambda x, row=row: {
            'color': THEME_COLOR['primary'] if row['Day_Night_period'] == 'day' 
                    else THEME_COLOR['secondary'],
            'weight': 1.5,
            'fillOpacity': 0.3
        },
        tooltip=f"Type: {row['Type']}<br>Period: {row['Day_Night_period']}"
    ).add_to(m)

# Add concert markers
for _, event in concert_filter.iterrows():
    folium.Marker(
        location=[event['Latitude'], event['Longitude']],
        popup=f"""<b>{event['Artist']}</b><br>
                {event['Venue']}<br>
                {event['Date'].strftime('%Y-%m-%d')}""",
        icon=folium.Icon(color='purple', icon='music', prefix='fa')
    ).add_to(m)

# Render map and handle state updates
map_state = st_folium(
    m,
    key="main_map",
    width=1920,
    height=600,
    returned_objects=["zoom", "center", "bounds"],
    use_container_width=True
)

# Update session state only when valid changes occur
if map_state and map_state.get("center") and map_state.get("zoom"):
    new_center = (map_state["center"]["lat"], map_state["center"]["lng"])
    new_zoom = map_state["zoom"]
    
    # Only update if values actually changed
    if (new_center != st.session_state.map_state['center'] or 
        new_zoom != st.session_state.map_state['zoom']):
        st.session_state.map_state.update({
            "center": new_center,
            "zoom": new_zoom,
            "bounds": map_state.get("bounds")
        })
        st.rerun()  # Force refresh to maintain consistent state