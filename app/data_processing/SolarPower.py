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
) -> Dict[str, Tuple[str, str]]:
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
        capacity_data[row['Station Name']] = float(
            row['Installed Capacity(kW)'])
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
        print(
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


def calculate_capacity_factor(
    hourly_pg: Dict[str, Dict[str, Dict[str, List[float]]]],
    solar_capacity_data: Dict[str, float],
    fuel_type: str = "太陽能",
    scale: str = "regional"
) -> pd.DataFrame | pd.Series:

    national_power = pd.DataFrame()
    national_capcity: float = 0
    regional_avg_capcity_factor = pd.DataFrame()

    for region, region_data in hourly_pg.items():
        regional_power: float = pd.DataFrame()
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
        regional_avg_capcity_factor['東部'] = regional_avg_capcity_factor[[
            '中部', '南部']].mean(axis=1)

    national_capacity_factor = national_power.sum(axis=1) / national_capcity

    if scale == 'national':
        return national_capacity_factor
    if scale == 'regional':
        return regional_avg_capcity_factor


def calculate_capcity_percentage(
    capacity_data: Dict[str, float],
    station_data: Dict[str, Tuple[str, str]],
    fuel_type: str
) -> defaultdict(float):

    region_capcity = defaultdict(float)
    national_capacity: float = 0
    capacity_percentage = defaultdict(float)
    for station in capacity_data:
        region, fuel = station_data[station]
        if fuel == fuel_type:
            region_capcity[region] += capacity_data[station]
            national_capacity += capacity_data[station]

    for region in region_capcity:
        capacity_percentage[region] = region_capcity[region] / \
            national_capacity
    print(capacity_percentage)

    return capacity_percentage


def calculate_pg_with_cf(
    capacity_factor: pd.DataFrame,
    capcity_target: float,
    unit: str,
    capcity_percentage: defaultdict(float)
) -> pd.DataFrame:
    if unit == 'kW':
        capcity_target = capcity_target
    if unit == 'MW':
        capcity_target = capcity_target * (10**3)
    if unit == 'GW':
        capcity_target = capcity_target * (10**6)
    else:
        return "Please input the correct unit: kW, MW, and GW"

    pg_data: pd.DataFrame = pd.DataFrame()
    for region in capacity_factor.columns:
        pg_data[region] = capacity_factor[region] * \
            capcity_target * capcity_percentage[region]
    print(pg_data.sum())
    return pg_data


# Load power generation data
data_file_path = '../../data/power_generation/各機組過去發電量20220101-20220331.json'
power_generation_data = load_power_generation_data(file_path=data_file_path)

'''
data_dir = '../../data/power_generation'

data_file_names = [
    '各機組過去發電量20220101-20220331.json',
    '各機組過去發電量20220401-20220630.json',
    '各機組過去發電量20220701-20220930.json',
    '各機組過去發電量20221001-20221231.json',
]
'''


station_info_file_path = '../../data/powerplants_info.csv'
solar_capacity_file_path = '../../data/solarpower_capacity.csv'

# Load station info
station_info = load_station_info(
    file_path=station_info_file_path
)

# Load solar power capacity
solar_capacity_info = load_capacity_info(
    file_path=solar_capacity_file_path
)

# Process power generation data
pg_data = process_power_generation_data(
    data=power_generation_data,
    station_info=station_info
)

hourly_pg_data = compute_hourly_data(
    data=pg_data
)

# Calculate capacity facotr of the {fuel type}
region_capacity_factor = calculate_capacity_factor(
    hourly_pg=hourly_pg_data,
    solar_capacity_data=solar_capacity_info
    # fuel_type: defualt is "太陽能"
    # sclae: regional or nationl. defualt is regional
)

print(region_capacity_factor)

national_capacity_facotr = calculate_capacity_factor(
    hourly_pg=hourly_pg_data,
    solar_capacity_data=solar_capacity_info,
    scale="national"
)

solar_capacity_percentage = calculate_capcity_percentage(
    capacity_data=solar_capacity_info,
    station_data=station_info,
    fuel_type="太陽能"
)


calculate_pg_with_cf(
    capacity_factor=region_capacity_factor,
    capcity_target=80,
    unit='GW',
    capcity_percentage=solar_capacity_percentage
)
