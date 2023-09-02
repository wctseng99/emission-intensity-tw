import json
import numpy as np
import os
import pandas as pd
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from absl import app, flags, logging

from app.data import (
    load_json_file,
    load_station_info,
    load_capacity_info,
    process_power_generation_data,
    compute_hourly_data
)

from app.module import (
    calculate_capacity_factor,
    calculate_capcity_percentage,
    calculate_pg_with_cf
)

flags.DEFINE_string("data_dir", "./data", "Directory for data.")
flags.DEFINE_string("result_dir", "./results", "Directory for result.")
FLAGS = flags.FLAGS



def estimate_target_power(
    dir_dir: Path,
    pg_file: str,
    station_file: str,
    capcity_file: str 
) -> pd.DataFrame:

    # Load power generation data
    power_generation_data = load_json_file(
        data_dir=f'{dir_dir}/power_generation/',
        pg_file=pg_file
    )

    # Load station info
    station_info = load_station_info(
        data_dir=dir_dir, 
        station_file=station_file
    )

    # Load solar power capacity
    solar_capacity_info = load_capacity_info(
        data_dir=dir_dir, 
        capcity_file=capcity_file
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
    )

    national_capacity_facotr = calculate_capacity_factor(
        hourly_pg=hourly_pg_data,
        solar_capacity_data=solar_capacity_info,
        scale="national"
    )

    # Calculate solar power capacity percentage in different regions.
    solar_capacity_percentage = calculate_capcity_percentage(
        capacity_data=solar_capacity_info,
        station_data=station_info,
        fuel_type="太陽能"
    )

    # Estimate the solar power in different regions with {target} solar power capacity.
    solar_pg_estimation = calculate_pg_with_cf(
        capacity_factor=region_capacity_factor,
        capcity_target=80,
        unit='GW',
        capcity_percentage=solar_capacity_percentage
    )

    return solar_pg_estimation



def main(_):

    logging.set_verbosity(logging.INFO)

    solar_pg_estimation = estimate_target_power(
        FLAGS.data_dir,
        '各機組過去發電量20220101-20220331.json',
        'powerplants_info.csv',
        'solarpower_capacity.csv'
    )
    
    logging.info(f'solar_pg_estimation: {solar_pg_estimation}')



if __name__ == "__main__":
    app.run(main)