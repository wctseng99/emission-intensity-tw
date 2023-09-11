import json
import os
import logging
import numpy as np
import pandas as pd
import functools
from typing import List, Dict, Tuple
from pathlib import Path
from collections import defaultdict

from app.data.base import(
    get_json_file,
    get_station_info,
    get_capacity_info,
    process_power_generation_data,
    compute_hourly_data,
)

@functools.lru_cache(maxsize=None)
def get_hourly_pg_data(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    capacity_file: str 
) -> Dict:
    # Load power generation data
    power_generation_data = get_json_file(
        data_dir=f'{data_dir}/power_generation/',
        pg_file=pg_file
    )

    # Load station info
    station_info = get_station_info(
        data_dir=data_dir, 
        station_file=station_file
    )

    # Load solar power capacity
    solar_capacity_info = get_capacity_info(
        data_dir=data_dir, 
        capacity_file=capacity_file
    )

    # Process power generation data
    pg_data = process_power_generation_data(
        data=power_generation_data,
        station_info=station_info
    )

    hourly_pg_data = compute_hourly_data(
        data=pg_data
    )

    return hourly_pg_data

def get_selected_pg_data(
    pg: Dict,
    exclude_fuel: List
) -> Dict:

    selected_pg = pd.DataFrame()

    for region, fuel_dict in pg.items():
        region_sum = []
        for fuel, unit_dict in fuel_dict.items():
            if fuel not in exclude_fuel:
                for unit, power_values in unit_dict.items():
                    region_sum.append(power_values)
        selected_pg[region] = np.sum(region_sum, axis=0).tolist()

    logging.info(f'The excluded fuel types: {exclude_fuel}.')

    return selected_pg
