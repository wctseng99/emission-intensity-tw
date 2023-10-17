import json
import numpy as np
import os
import pandas as pd
import logging
from typing import List, Dict, Tuple
from collections import defaultdict
from rich.logging import RichHandler


def calculate_capacity_factor(
    hourly_pg: Dict[str, Dict[str, Dict[str, List[float]]]],   
    capacity_data: Dict[str, float],
    fuel_type: str,
    scale: str
) -> pd.DataFrame | pd.Series:

    def detect_negative_values(
        data: list
    ) -> list:
        if np.any(np.array(data) < 0):
            logging.info(
                f'There is the station with negative power values: region: {region}, station: {station}.')

            neg_station = np.array(data)
            neg_station[neg_station < 0] = 0
            revised_data = neg_station.tolist()

            return revised_data
        else:
            return data

    national_power = pd.DataFrame()
    national_capacity: float = 0
    regional_avg_capacity_factor = pd.DataFrame()
    if fuel_type in ["陸域風電", "離岸風電"]:
        fuel_type = "風力"
    for region, region_data in hourly_pg.items():
        regional_power = pd.DataFrame()
        regional_capacity: float = 0
        for station, station_data in region_data[fuel_type].items():
            if station in capacity_data:
                # check if there are negative values, and replace them with zeros.
                station_data = detect_negative_values(data=station_data)

                regional_power[station] = station_data 
                regional_capacity += capacity_data[station]

                national_power[station] = station_data
                national_capacity += capacity_data[station]

        regional_capacity_factor = regional_power.sum(axis=1) / regional_capacity

        regional_avg_capacity_factor[region] = regional_capacity_factor

    # Eastern region is the average of central and southern region, due to the lack of eastern solar power data.
    if fuel_type in ["太陽能"]:
        if regional_avg_capacity_factor['東部'].isna().all():
            regional_avg_capacity_factor['東部'] = regional_avg_capacity_factor[['中部', '南部']].mean(axis=1)

    national_capacity_factor = national_power.sum(axis=1) / national_capacity

    if scale == 'national':
        logging.info(f'The avg of regional capacity factor:\n{regional_avg_capacity_factor.mean()}.')
        return national_capacity_factor

    if scale == 'regional':
        logging.info(f'The avg of national capacity factor:\n{national_capacity_factor.mean()}.')
        return regional_avg_capacity_factor


def calculate_capacity_percentage(
    capacity_data: Dict[str, float],
    station_data: Dict[str, Tuple[str, str]],
    fuel_type: str
) -> defaultdict(float):

    region_capacity = defaultdict(float)
    national_capacity: float = 0
    capacity_percentage = defaultdict(float)
    
    if fuel_type in ["陸域風電", "離岸風電"]:
        fuel_type = "風力"

    for station in capacity_data:
        region, fuel = station_data[station]
        if fuel == fuel_type:
            region_capacity[region] += capacity_data[station]
            national_capacity += capacity_data[station]

    for region in region_capacity:
        capacity_percentage[region] = region_capacity[region] / \
            national_capacity

        logging.info(
            f'{region} capacity percentage: {capacity_percentage[region]}.')
    return capacity_percentage


def calculate_pg_with_cf(
    capacity_factor: pd.DataFrame,
    capacity_target: float,
    unit: str,
    capacity_percentage: defaultdict(float)
) -> pd.DataFrame:

    if unit == 'kW':
        capacity_target = capacity_target
    if unit == 'MW':
        capacity_target = capacity_target * (10**3)
    if unit == 'GW':
        capacity_target = capacity_target * (10**6)
    else:
        return logging.info(f"Please input the correct unit: kW, MW, and GW")

    pg_data: pd.DataFrame = pd.DataFrame()
    for region in capacity_factor.columns:
        pg_data[region] = capacity_factor[region] * \
            capacity_target * capacity_percentage[region]
    return pg_data
