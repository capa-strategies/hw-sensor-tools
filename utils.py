import pandas as pd
import numpy as np
import os
import re
import glob
from timezonefinder import TimezoneFinder
import geopandas as gpd

def load_hw_csv(csv_file):
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"File '{csv_file}' does not exist")
    
    dtype_map = {
        0: bool,     # logical, GPS lock
        1: int,    # double, GPS satellites used
        2: str,      # character, date
        3: str,      # character, time
        4: str,      # character, latitude
        5: str,      # character, longitude
        6: float,    # double, altitude
        7: float,    # double, course heading
        8: float,    # double, speed (km/hr)
        9: float,    # double, relative humidity (%)
        10: float,   # double, temperature (degrees C)
        11: float    # double, battery
    }
    
    # Read CSV with specified column types
    try:
        df = pd.read_csv(csv_file, dtype=dtype_map)

        base_name = os.path.basename(csv_file)
        match = re.match(r'^CAPA([0-9]+)_.*$', base_name)
        sensor_number = match.group(1) if match else None
        df['sensor_number'] = sensor_number
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")
    
    return(df)

def deg_to_dec(df):
    # Pad 9-character latitudes
    needs_padding = df['lat'].str.len() == 9
    if needs_padding.any():
        df.loc[needs_padding, 'lat'] = "0" + df.loc[needs_padding, 'lat']
        
    # Remove rows with missing/invalid data
    missing_lat = df['lat'].isna()
    missing_lon = df['lon'].isna() 

    invl_lat = df['lat'].str.len() != 10
    invl_lon = ~df['lon'].str.len().between(10, 11)

    # Format validation
    lat_bad_format = ~df['lat'].str.match(r"^\d{4}\.\d{4}[NS]$", na=False)
    lon_bad_format = (~df['lon'].str.match(r"^\d{4}\.\d{4}[EW]$", na=False) & 
                      ~df['lon'].str.match(r"^\d{5}\.\d{4}[EW]$", na=False))

    rows_to_drop = (
        missing_lat
        | missing_lon
        | invl_lat
        | invl_lon
        | lat_bad_format
        | lon_bad_format
    )
    
    if rows_to_drop.any():
        print(f"Dropping {rows_to_drop.sum()} rows with invalid data")
        df = df[~rows_to_drop].reset_index(drop=True)

    # subset degree, minute, and hemisphere components
    lat_degrees = pd.to_numeric(df['lat'].str[0:2], errors='coerce')
    lat_minutes = pd.to_numeric(df['lat'].str[2:9], errors='coerce')
    lat_hemisphere = df['lat'].str[9]
    
    lon_is_10_char = df['lon'].str.len() == 10
    lon_degrees = np.where(lon_is_10_char,
                          pd.to_numeric(df['lon'].str[0:2], errors='coerce'),
                          pd.to_numeric(df['lon'].str[0:3], errors='coerce'))
    
    lon_minutes = np.where(lon_is_10_char,
                          pd.to_numeric(df['lon'].str[2:9], errors='coerce'),
                          pd.to_numeric(df['lon'].str[3:10], errors='coerce'))
    
    lon_hemisphere = np.where(lon_is_10_char,
                             df['lon'].str[9],
                             df['lon'].str[10])
    
    # Convert coordinates ------
    # Apply hemisphere correction to components
    lat_degrees = np.where(lat_hemisphere == "S", lat_degrees * (-1), lat_degrees)
    lat_minutes = np.where(lat_hemisphere == "S", lat_minutes * (-1), lat_minutes)
    
    lon_degrees = np.where(lon_hemisphere == "W", lon_degrees * (-1), lon_degrees)
    lon_minutes = np.where(lon_hemisphere == "W", lon_minutes * (-1), lon_minutes)
    
    # Convert from degrees, decimal minutes to decimal degrees
    df['lat'] = lat_degrees + (lat_minutes / 60)
    df['lon'] = lon_degrees + (lon_minutes / 60)
    
    # Reset index
    df = df.reset_index(drop=True)

    return df

def convert_gps_time(df, tz_str, convert_tz=False):
    date_col = df['date']
    time_col = df['time']

    date_clean = pd.to_datetime(
        date_col.str.pad(width=6, side='left', fillchar='0').where(date_col.str.len() == 5, date_col),
        format='%d%m%y',
        errors='coerce'
    )

    time_padded = time_col.str.pad(width=6, side='left', fillchar='0').where(time_col.str.len() <= 6, time_col)
    datetime_str = date_clean.dt.strftime('%Y-%m-%d') + ' ' + time_padded
    datetime_utc = pd.to_datetime(datetime_str, format='%Y-%m-%d %H%M%S', errors='coerce', utc=True)
    
    # Optionally convert to target timezone
    if convert_tz:
        datetime_result = datetime_utc.dt.tz_convert(tz_str)
    else:
        datetime_result = datetime_utc

    df['datetime'] = datetime_result
    df.drop(columns=['date','time'], inplace=True)
    
    return df

def process_file(csv_path, output_dir='formatted', convert_tz=False, convert_units=True, 
    driver='CSV', export=True):

    print(f"Processing file: {csv_path}")

    # Clean lat/lon
    df = load_hw_csv(csv_path)
    
    if len(df) == 0:
        print("Warning: Input dataframe is empty, skipping file")
        return

    df_clean = deg_to_dec(df) 
    
    # Clean and convert date/time 
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=df_clean['lat'].mean(), lng=df_clean['lon'].mean())
    df_out = convert_gps_time(df_clean, timezone_str, convert_tz)

    if convert_units:
        df_out['temperature'] = df_out['temperature']*(1.8) + 32
        df_out['speedkmhr'] = df_out['speedkmhr'] * 0.621371
        df_out['altitude'] = df_out['altitude'] * 3.28084
        df_out.rename(columns={"speedkmhr": "speedmph"}, inplace=True)

    # floating point handling
    df_out['lat'] = df_out['lat'].map(lambda x: f"{x:.6f}")
    df_out['lon'] = df_out['lon'].map(lambda x: f"{x:.6f}")
    for col in df_out.select_dtypes(include=['float']).columns:
        if col not in ['lat', 'lon']:
            df_out[col] = df_out[col].map(lambda x: f"{x:.2f}")

    if not export:
        return(df_out)
    else:
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(csv_path) 
        if driver == 'GeoJSON' and not base_name.lower().endswith('.geojson'):
            base_name = os.path.splitext(base_name)[0] + '.geojson'
        elif driver == 'GPKG' and not base_name.lower().endswith('.gpkg'):
            base_name = os.path.splitext(base_name)[0] + '.gpkg'

        output_path = os.path.join(output_dir, base_name)
        if driver in ['GPKG', 'GeoJSON']:
            geometry = gpd.points_from_xy(df_out.lon, df_out.lat)
            gdf = gpd.GeoDataFrame(df_out, geometry=geometry, crs="EPSG:4326")
            gdf.to_file(output_path, driver=driver)
        else:
            df_out.to_csv(output_path, index=False)


def process_folder(folder_path, output_dir='formatted', convert_tz=False, convert_units=True, driver='CSV', merge_files=False):
    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    
    if not csv_files:
        print("No CSV files found in the specified folder")
        return
    
    if merge_files:
        print(f"Grouping {len(csv_files)} CSV files into a single output")
        
        # Process all files and collect dataframes
        all_dataframes = []
        for f in csv_files:
            df_clean = process_file(f, output_dir, convert_tz, convert_units, driver='CSV', export=False)
            all_dataframes.append(df_clean)
        
        if not all_dataframes:
            print("No valid data found in any CSV files")
            return

        df_out = pd.concat(all_dataframes, ignore_index=True)

        # Save combined output if output_dir specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # Create output filename based on folder name
            folder_name = os.path.basename(folder_path.rstrip('/'))
            base_name = f"{folder_name}_combined"
            
            if driver == 'GeoJSON' and not base_name.lower().endswith('.geojson'):
                base_name = base_name + '.geojson'
            elif driver == 'GPKG' and not base_name.lower().endswith('.gpkg'):
                base_name = base_name + '.gpkg'
            elif (driver is None or driver == 'CSV') and not base_name.lower().endswith('.csv'):
                base_name = base_name + '.csv'

            output_path = os.path.join(output_dir, base_name)
            if driver in ['GPKG', 'GeoJSON']:
                geometry = gpd.points_from_xy(df_out.lon, df_out.lat)
                gdf = gpd.GeoDataFrame(df_out, geometry=geometry, crs="EPSG:4326")
                gdf.to_file(output_path, driver=driver)
            else:
                df_out.to_csv(output_path, index=False)
                
            print(f"Combined output saved to: {output_path}")
    else:
        # Process files individually as before
        for f in csv_files:
            process_file(f, output_dir, convert_tz, convert_units, driver)