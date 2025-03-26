import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from datetime import datetime
from streamlit_folium import folium_static
from shapely import wkt
import geopandas as gpd

# Initialize page configuration
st.set_page_config(
    page_title="GeoDashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for grid layout
st.markdown("""
<style>
/* Main grid container */
.main .block-container {
    display: grid;
    grid-template-columns: 300px 1fr 300px;
    grid-template-rows: 500px 500px;
    gap: 10px;
    height: 100vh;
    max-width: 1920px;
}

/* Grid areas */
#left-sidebar {
    grid-column: 1;
    grid-row: 1 / 3;
}

#main-map {
    grid-column: 2;
    grid-row: 1 / 3;
}

#top-right {
    grid-column: 3;
    grid-row: 1;
}

#bottom-right {
    grid-column: 3;
    grid-row: 2;
}

</style>
""", unsafe_allow_html=True)

THEME_COLOR = {
    'day_colors': ['#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#F44336', '#D32F2F'],
    'night_colors': ['#E1F5FE', '#B3E5FC', '#81D4FA', '#4FC3F7', '#29B6F6', '#039BE5']
}

DEFAULT_SOURCE = ["Road Traffic"]
NOISE_LEVEL_MAPPING = {
    1: 'Mild <55dB', 2: 'Noisy 55-60dB', 3: 'Loud 60-65dB',
    4: 'Louder 65-70dB', 5: 'Very Loud 70-75dB', 6: 'Extremely Loud >75dB',
    11: 'Mild <50dB', 12: 'Noisy 50-55dB', 13: 'Loud 55-60dB',
    14: 'Louder 60-65dB', 15: 'Very Loud 65-70dB', 16: 'Extremely Loud >70dB'
}

# Data loading
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

@st.cache_data
def load_construction_data():
    # Load data with proper coordinate system handling
    construction_df = pd.read_csv('data/cleaned/construction_plan.csv')
    
    # Convert WKT to geometry with original CRS
    construction_df['Geometry'] = construction_df['Geometry'].apply(wkt.loads)
    construction_gdf = gpd.GeoDataFrame(
        construction_df,
        geometry='Geometry',
        crs="EPSG:28992"  # Set original CRS first
    )
    
    # Transform to WGS84 (EPSG:4326)
    construction_gdf = construction_gdf.to_crs(epsg=4326)
    
    # Calculate centroids AFTER transformation
    construction_gdf['center'] = construction_gdf['Geometry'].centroid
    
    # Parse dates
    construction_gdf['Planned_Construction_Start'] = pd.to_datetime(
        construction_gdf['Planned_Construction_Start']
    )
    
    return construction_gdf

def create_custom_map(time_mode, selected_levels, concert_date, show_concerts, show_constructions):
    # Load data with caching
    noise_gdf = load_noise_data()
    concert_df = load_concert_data()
    construction_gdf = load_construction_data()
    
    # Apply filters
    noise_filter = noise_gdf[
        (noise_gdf['period'] == time_mode) &
        (noise_gdf['legend'].isin(selected_levels))
    ]
    
    concert_filter = concert_df[concert_df['Date'].dt.date == concert_date]
    
    # Create base map
    m = folium.Map(
        location=(52.3676, 4.9041),
        zoom_start=12,
        tiles='CartoDB positron',
        control_scale=True,
        prefer_canvas=True,
        zoom_control=False
    )
    
    # Add noise data with original styling
    if not noise_filter.empty:
        for _, row in noise_filter.iterrows():
            level = row['legend']
            color_index = (level - 1) if time_mode == "day" else (level - 11)
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
    
    # Add concert data with original styling
    PURPLE_COLOR = '#9C27B0'
    if show_concerts:
        for _, event in concert_filter.iterrows():
            # Marker with icon
            folium.Marker(
                location=[event['Latitude'], event['Longitude']],
                popup=f"""<b>{event['Artist']}</b><br>
                        {event['Venue']}<br>
                        {event['Date'].strftime('%Y-%m-%d')}""",
                icon=folium.Icon(color='purple', icon='music', prefix='fa')
            ).add_to(m)
            
            # 50m radius circle
            folium.Circle(
                location=[event['Latitude'], event['Longitude']],
                radius=50,
                color=PURPLE_COLOR,
                fill=True,
                fill_color=PURPLE_COLOR,
                fill_opacity=0.2,
                weight=2
            ).add_to(m)
    
    # Add construction data with original styling
    CONSTRUCTION_COLOR = {
        'fill': '#8B4513',
        'border': '#654321',
        'icon': '#CD853F'
    }
    
    if show_constructions:
        construction_filter = construction_gdf[
            construction_gdf['Planned_Construction_Start'] <= pd.Timestamp(concert_date)
        ]
        
        for _, row in construction_filter.iterrows():
            # Construction polygon
            folium.GeoJson(
                row['Geometry'],
                style_function=lambda x: {
                    'fillColor': CONSTRUCTION_COLOR['fill'],
                    'color': CONSTRUCTION_COLOR['border'],
                    'weight': 1.5,
                    'fillOpacity': 0.4
                },
                tooltip=f"Project: {row['Project_Abbreviation']}"
            ).add_to(m)
            
            # Center marker
            folium.Marker(
                location=[row['center'].y, row['center'].x],
                icon=folium.Icon(
                    color='lightgray' if time_mode == 'night' else 'white',
                    icon_color=CONSTRUCTION_COLOR['icon'],
                    icon='wrench',
                    prefix='fa'
                ),
                popup=f"<b>{row['Project_Abbreviation']}</b><br>"
                      f"Start Date: {row['Planned_Construction_Start'].strftime('%Y-%m-%d')}"
            ).add_to(m)
    
    return m

def main_layout():
    col1, col2, col3 = st.columns([3, 12, 3])

    with col1:
        st.markdown('<div id="left-sidebar" class="dashboard-box">', unsafe_allow_html=True)
        
        # Time period selector with emojis
        time_mode = st.radio(
            "time_period",
            options=["Day", "Night"],
            format_func=lambda x: f"🌞 {x}" if x == "Day" else f"🌙 {x}",
            horizontal=True,
            label_visibility="collapsed"
        ).lower()

        # Dynamic CSS for night mode
        if time_mode == "night":
            st.markdown(f"""
            <style>
                #left-sidebar {{
                    background-color: #474747 !important;
                    transition: background-color 0.3s ease;
                }}
                .stMultiSelect label p, 
                .stSlider label,
                .stDateInput label {{
                    color: #E0E0E0 !important;
                }}
            </style>
            """, unsafe_allow_html=True)

        st.markdown("**🔊 Noise Levels**")
        
        # Determine available levels based on time mode
        if time_mode == "day":
            available_levels = [1, 2, 3, 4, 5, 6]
            default_levels = [5, 6]
        else:
            available_levels = [11, 12, 13, 14, 15, 16]
            default_levels = [15, 16]

        # 3-column checkbox layout
        selected_levels = []
        with st.container():
            cols = st.columns(3)
            for idx, level in enumerate(available_levels):
                with cols[idx % 3]:
                    is_checked = level in default_levels
                    if st.checkbox(
                        label=NOISE_LEVEL_MAPPING[level],
                        value=is_checked,
                        key=f"noise_level_{level}"
                    ):
                        selected_levels.append(level)

        # Noise source selection
        st.markdown("**Noise Sources**")
        noise_sources = st.multiselect(
            "Select Noise Sources:",
            options=load_noise_data()['source_type'].unique(),  # Load fresh data
            default=DEFAULT_SOURCE,
            label_visibility="collapsed"
        )

        st.markdown("---")
        
        # Date selection
        concert_date = st.date_input(
            "📅 Date",
            value=datetime.today().date(),
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Visibility toggles
        show_concerts = st.checkbox("🎤 Show Concerts", value=True, key="show_concerts")
        show_constructions = st.checkbox("🚧 Show Constructions", value=True, key="show_constructions")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div id="main-map" class="dashboard-box">', unsafe_allow_html=True)
        st.header("Amsterdam Urban Activity Map")
        folium_static(
            create_custom_map(time_mode, selected_levels, concert_date, show_concerts, show_constructions),
            width=1320,
            height=600
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div id="top-right" class="dashboard-box">', unsafe_allow_html=True)
        st.header("Data Summary")
        
        # Display data statistics
        noise_gdf = load_noise_data()
        concert_df = load_concert_data()
        construction_gdf = load_construction_data()
        
        st.metric("Noise Zones", len(noise_gdf))
        st.metric("Upcoming Concerts", len(concert_df))
        st.metric("Construction Sites", len(construction_gdf))
        
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div id="bottom-right" class="dashboard-box">', unsafe_allow_html=True)
        st.header("Data Source")
        
        # Show recent concerts
        recent_concerts = concert_df.sort_values('Date', ascending=False).head(3)
        for _, row in recent_concerts.iterrows():
            st.write(f"🎵 {row['Event']} on {row['Date'].date()}")
        
        # Show upcoming constructions
        upcoming_constructions = construction_gdf.sort_values('Planned_Construction_Start').head(3)
        for _, row in upcoming_constructions.iterrows():
            st.write(f"🏗️ {row['Project_Name']} starts {row['Planned_Construction_Start'].date()}")
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main_layout()