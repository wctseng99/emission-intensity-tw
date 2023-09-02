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
    solar_capacity_data: Dict[str, float],
    fuel_type: str = "太陽能",
    scale: str = "regional"
) -> pd.DataFrame | pd.Series:

    def detect_negitive_values(
        data: list
    ) -> list:
        if np.any(np.array(data) < 0):
            print(
                f'There is the station with negative power values: region: {region}, station: {station}.')
            neg_station = np.array(data)
            neg_station[neg_station < 0] = 0
            revised_data = neg_station.tolist()

            return revised_data
        else:
            return data

    national_power = pd.DataFrame()
    national_capcity: float = 0
    regional_avg_capcity_factor = pd.DataFrame()

    for region, region_data in hourly_pg.items():
        regional_power = pd.DataFrame()
        regional_capcity: float = 0
        for station, station_data in region_data[fuel_type].items():
            if station in solar_capacity_data:
                # check if there are negative values, and replace them with zeros.
                station_data = detect_negitive_values(
                    data=station_data)

                regional_power[station] = station_data
                regional_capcity += solar_capacity_data[station]

                national_power[station] = station_data
                national_capcity += solar_capacity_data[station]

        regional_capacity_factor = regional_power.sum(
            axis=1) / regional_capcity

        regional_avg_capcity_factor[region] = regional_capacity_factor

    # Eastern region is the average of central and southern region, due to the lack of eastern solar power data.
    if regional_avg_capcity_factor['東部'].isna().all():
        regional_avg_capcity_factor['東部'] = regional_avg_capcity_factor[[
            '中部', '南部']].mean(axis=1)

    national_capacity_factor = national_power.sum(axis=1) / national_capcity

    logging.info(
        f'The avg of regional capcity factor: {regional_avg_capcity_factor.mean()}.')
    logging.info(
        f'The avg of national capcity factor: {national_capacity_factor.mean()}.')

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

        logging.info(
            f'{region} capacity percentage: {capacity_percentage[region]}.')
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
    return pg_data
