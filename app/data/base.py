import json
import os
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict



def get_json_file(
    data_dir: str,
    pg_file: str
) -> Dict:
    file_path = os.path.join(data_dir, pg_file)
    # file_path = f"{data_dir}/{file_name}"
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)
    return data


def get_station_info(
    data_dir: str,
    station_file: str
) -> Dict[str, Tuple[str, str]]:
    station_info = {}
    file_path = os.path.join(data_dir, station_file)
    region_fuel_info = pd.read_csv(file_path)
    for _, row in region_fuel_info.iterrows():
        station_info[row['Station Name']] = (row['Location'], row['Type'])
    return station_info


def get_capacity_info(
    data_dir: str,
    capacity_file: str,
    fuel_type: str
) -> Dict[str, float]:
    capacity_data = {}
    file_path = os.path.join(data_dir, capacity_file)
    capacity_df = pd.read_csv(file_path, encoding='utf-8')
    
    for _, row in capacity_df.iterrows():
        if row['Fuel Type'] == fuel_type:
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
            pg_data[region][fuel][unit].append(
                float(net_power) * 1000)  # Convert from MW to kW
        except:
            missing_station[station_name].append((fuel, date, net_power))

    if missing_station:
        logging.info(
            f'Please Check the new stations or errors: {missing_station.keys()}.')

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



