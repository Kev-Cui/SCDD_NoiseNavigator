import streamlit as st
import pandas as pd
import folium
from datetime import timedelta, date
from streamlit_folium import folium_static
import plotly.express as px
from data_loader import load_noise_data, load_concert_data, load_construction_data

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
    height: 80vh;
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
    'day_colors': ['#2ECC71', '#F1C40F', '#E67E22', '#E74C3C', '#C0392B', '#7B241C'],
    'night_colors': ['#1ABC9C', '#3498DB', '#9B59B6', '#8E44AD', '#34495E', '#2C3E50']
}

DEFAULT_SOURCE = ["Road Traffic"]
NOISE_LEVEL_MAPPING = {
    1: 'Mild', 2: 'Low', 3: 'Med',
    4: 'Loud', 5: 'High', 6: 'Max',
    11: 'Mild', 12: 'Low', 13: 'Med',
    14: 'Loud', 15: 'High', 16: 'Max'
}

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

        st.markdown("**Date**")
        # Date selection
        concert_date = st.date_input(
            "Date",
            value=date.today(),
            label_visibility="collapsed"
        )

        st.markdown("---")

        show_alerts = st.checkbox(
            "🔴 Noise Alerts", 
            value=True,
            help="Toggle noise alert markers on/off"
        )
        alert_level = st.selectbox(
            "Alert Sensitivity:",
            options=["Low", 
                    "Med", 
                    "High"],
            index=0,
            help="Adjust sensitivity for noise alerts"
        )

        ALERT_LEVELS = {
            "Low": [6] if time_mode == 'day' else [16],
            "Med": [5,6] if time_mode == 'day' else [15,16],
            "High": [4,5,6] if time_mode == 'day' else [14,15,16]
        }

        # Store in session state for persistence
        st.session_state.alert_level = ALERT_LEVELS[alert_level]

        st.markdown("**Noise Levels**")
        
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
        st.markdown("---")
        # Noise source selection
        st.markdown("**Noise Sources**")
        noise_sources = st.multiselect(
            "Select Noise Sources:",
            options=load_noise_data()['source_type'].unique(),  # Load fresh data
            default=DEFAULT_SOURCE,
            label_visibility="collapsed"
        )
        
        # Visibility toggles
        show_concerts = st.checkbox("Show Concerts", value=True, key="show_concerts")
        show_constructions = st.checkbox("Show Constructions", value=True, key="show_constructions")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        def create_custom_map(time_mode, selected_levels, concert_date, show_concerts, show_constructions):
            # Load data with caching
            noise_gdf = load_noise_data()
            concert_df = load_concert_data()
            construction_gdf = load_construction_data()
            
            # Apply filters
            noise_filter = noise_gdf[
                (noise_gdf['source_type'].isin(noise_sources)) &
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
            significant_noise = noise_gdf[
                noise_gdf['legend'].isin([6] if time_mode == 'day' else [16])
            ]
            
            if show_alerts and not significant_noise.empty:
                for _, row in significant_noise.iterrows():
                    # Determine alert severity
                    alert_value = row['legend']
                    if alert_value == st.session_state.alert_level[0]:
                        color = 'red'
                        icon = 'exclamation-triangle'
                    elif alert_value == st.session_state.alert_level[-1]:
                        color = 'darkred'
                        icon = 'exclamation-triangle'
                    else:
                        color = 'orange'
                        icon = 'exclamation-circle'

                    folium.Marker(
                        location=[row['centroid'].y, row['centroid'].x],
                        icon=folium.Icon(
                            color=color,
                            icon=icon,
                            prefix='fa'
                        ),
                        popup=f"""
                        <b>{icon.replace('-', ' ').title()} Alert!</b><br>
                        Severity: {alert_value - (5 if time_mode=='day' else 15)}/3<br>
                        Source: {row['source_type']}<br>
                        Radius: {row.geometry.area:.1f} km²
                        """,
                        tooltip=f"{['High','Higher','Highest'][alert_value%10 -6]} Noise Zone"
                    ).add_to(m)
            
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
                                'color': 'transparent',
                                'weight': 0,
                                'fillOpacity': 0.7
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
                            color='F7F9FC' if time_mode == 'night' else 'white',
                            icon_color=CONSTRUCTION_COLOR['icon'],
                            icon='wrench',
                            prefix='fa'
                        ),
                        popup=f"<b>{row['Project_Abbreviation']}</b><br>"
                            f"Start Date: {row['Planned_Construction_Start'].strftime('%Y-%m-%d')}"
                    ).add_to(m)
            
            return m
        st.markdown('<div id="main-map" class="dashboard-box">', unsafe_allow_html=True)
        folium_static(
            create_custom_map(time_mode, selected_levels, concert_date, show_concerts, show_constructions),
            width=1320,
            height=650
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div id="top-right" class="dashboard-box">', unsafe_allow_html=True)

        # Load data
        concert_df = load_concert_data()
        
        # 7-day concert count based on selected date
        dates = [concert_date + timedelta(days=i) for i in range(7)]
        date_labels = [date.strftime('%a %d') for date in dates]
        
        # Create Plotly figure
        fig = px.bar(
            x=date_labels,
            y=[len(concert_df[concert_df['Date'].dt.date == date]) for date in dates],
            color_discrete_sequence=['#9C27B0']
        )
        
        # Customize appearance
        fig.update_traces(width=0.4, marker_line_width=1, marker_line_color='white')
        fig.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=200,
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=False, showline=False),
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=30),
            autosize=False
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("**Concerts in Next 7 Days**")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div id="bottom-right" class="dashboard-box">', unsafe_allow_html=True)
        st.markdown("**Data Source**")
        with st.popover("ℹ️ Info"):
            st.write("""
            ### Data Sources

            **Amsterdam Concert Plan Data (Songkick)**  
            - **Source:** [Songkick Metro Area - Amsterdam](https://www.songkick.com/metro-areas/31366-netherlands-amsterdam)  
            - **Description:** This dataset was scraped from Songkick and provides up-to-date information on concerts and music events in Amsterdam, including details on venues and event dates.

            **Amsterdam Noise Map Data**  
            - **Source:** [Amsterdam Open Geodata](https://maps.amsterdam.nl/open_geodata/?k=492)  
            - **Description:** Publicly available noise mapping data provided by the Municipality of Amsterdam. This dataset is used to monitor and visualize noise levels across the city, supporting urban noise management initiatives.

            **Amsterdam Noise Zones Data**  
            - **Source:** [Amsterdam API - Geluidszones](https://api.data.amsterdam.nl/v1/docs/datasets/geluidszones.html)  
            - **Description:** Data from the Amsterdam API that delineates different noise zones within the city. It helps in categorizing areas based on noise levels and is useful for both regulatory purposes and urban planning.

            **Amsterdam Construction Plans**  
            - **Source:** [Amsterdam API - Nieuwbouwplannen](https://api.data.amsterdam.nl/v1/docs/datasets/nieuwbouwplannen.html)  
            - **Description:** This dataset, also from the Amsterdam API, contains information on new construction projects throughout the city. It provides insights into planned urban developments which may affect noise levels and city infrastructure.
            """)
        
        # Show recent concerts
        # recent_concerts = concert_df.sort_values('Date', ascending=False).head(3)
        # for _, row in recent_concerts.iterrows():
        #     st.write(f"🎵 {row['Venue']} on {row['Date'].date()}")
        
        # # Show upcoming constructions
        # upcoming_constructions = construction_gdf.sort_values('Planned_Construction_Start').head(3)
        # for _, row in upcoming_constructions.iterrows():
        #     st.write(f"🏗️ {row['Project_Abbreviation']} starts {row['Planned_Construction_Start'].date()}")
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main_layout()