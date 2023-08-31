import json
import numpy as np
import pandas as pd
import logging
from typing import List, Dict, Tuple
from collections import defaultdict
from rich.logging import RichHandler


def load_power_generation_data(
    file_path: str
) -> Dict:
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)
    return data


def load_station_info(
    file_path: str
) -> Dict:
    station_info = {}
    region_fuel_info = pd.read_csv(file_path)
    for _, row in region_fuel_info.iterrows():
        station_info[row['Station Name']] = (row['Location'], row['Type'])
    return station_info


def load_capacity_info(
    file_path: str
) -> Dict[str, float]:
    capacity_data = {}
    capacity_df = pd.read_csv(file_path)
    # print(capacity_df)
    for _, row in capacity_df.iterrows():
        capacity_data[row['Station Name']] = float(row['Installed Capacity(kW)'])
    return capacity_data


def process_power_generation_data(
    data: Dict, 
    station_info: Dict
) -> Dict:

    pg_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    missing_station = defaultdict(list)

    for i in range(len(data['records']['NET_P'])):
        fuel = data['records']['NET_P'][i]['FUEL_TYPE']
        unit = data['records']['NET_P'][i]['UNIT_NAME']
        net_power = data['records']['NET_P'][i]['NET_P']
        date = data['records']['NET_P'][i]['DATE']
        try:
            station_name = unit
            region, _ = station_info[station_name]
            pg_data[region][fuel][unit].append(float(net_power) * 1000)  # Convert from MW to kW
        except:
            missing_station[station_name].append((fuel, date, net_power))
    if missing_station:
        print(f'Please Check the new stations or errors: {missing_station.keys()}.')


    return pg_data


def compute_hourly_data(
    data: Dict[str, Dict[str, Dict[str, List[float]]]]
) -> Dict[str, Dict[str, Dict[str, List[float]]]]:

    hourly_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for region, fuel_dict in data.items():
        for fuel_type, unit_dict in fuel_dict.items():
            for unit, power_values in unit_dict.items():
                hourly_values = []
                for i in range(0, len(power_values), 6):
                    avg_value = np.mean(power_values[i:i+6])
                    hourly_values.append(avg_value)
                hourly_data[region][fuel_type][unit] = hourly_values
                
    return hourly_data


def calculate_capacity_factor(
    hourly_pg: Dict[str, Dict[str, Dict[str, List[float]]]],
    solar_capacity_data: Dict[str, float],
    fuel_type: str = "太陽能",
    scale: str = "regional"
):

    national_power = pd.DataFrame()
    national_capcity: float = 0
    regional_avg_capcity_factor = pd.DataFrame()

    for region, region_data in hourly_pg.items():
        regional_power: float= pd.DataFrame()
        regional_capcity: float = 0
        for station, station_data in region_data[fuel_type].items():
            if station in solar_capacity_data:

                regional_power[station] = station_data
                regional_capcity += solar_capacity_data[station]
                
                national_power[station] = station_data
                national_capcity += solar_capacity_data[station]
                
        regional_capcity_factor = regional_power.sum(axis=1) / regional_capcity
        regional_avg_capcity_factor[region] = regional_capcity_factor  

    # Eastern region is the average of central and southern region, due to the lack of eastern solar power data.
    if regional_avg_capcity_factor['東部'].isna().all():
        regional_avg_capcity_factor['東部'] = regional_avg_capcity_factor[['中部', '南部']].mean(axis=1)
    
    national_capcity_factor = national_power.sum(axis=1) / national_capcity

    # print(f'national: {national_capcity_factor.mean()}')
    # print(f'regional: {regional_avg_capcity_factor.mean()}')

    if scale == 'national':
        return national_capcity_factor
    if scale == 'regional':
        return  regional_avg_capcity_factor

# Load power generation data
data_file_path = '../../data/power_generation/各機組過去發電量20220101-20220331.json'
power_generation_data = load_power_generation_data(data_file_path)

'''
data_dir = '../../data/power_generation'

data_file_names = [
    '各機組過去發電量20220101-20220331.json',
    '各機組過去發電量20220401-20220630.json',
    '各機組過去發電量20220701-20220930.json',
    '各機組過去發電量20221001-20221231.json',
]
'''

# Load station info
station_info_file_path = '../../data/powerplants_info.csv'
station_info = load_station_info(station_info_file_path)

# Load solar power capacity
solar_capacity_file_path = '../../data/solarpower_capacity.csv'
solar_capacity_info = load_capacity_info(solar_capacity_file_path)

# Process power generation data
pg_data = process_power_generation_data(power_generation_data, station_info)
hourly_pg_data = compute_hourly_data(pg_data)

# Calculate capacity facotr of the {fuel type}
region_capacity_facotr = calculate_capacity_factor(hourly_pg_data, solar_capacity_info)
# sclae parameter: regional or nationl. defualt is regional



