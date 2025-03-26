import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Polygon
import streamlit as st

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
    noise_df = gpd.GeoDataFrame(noise_df, geometry='geometry').set_crs(epsg=4326)
    noise_df['centroid'] = noise_df['geometry'].centroid
    return noise_df

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