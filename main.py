import json
import numpy as np
import os
import pandas as pd
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from absl import app, flags, logging

from app.data import (
    # base
    get_json_file,
    get_station_info,
    get_capacity_info,
    process_power_generation_data,
    compute_hourly_data,
    # pg
    get_hourly_pg_data,
    get_selected_pg_data,
    # ape
    get_ap_emission_factor,
    get_emissions_by_region,
)

from app.module import (
    # core
    calculate_capacity_factor,
    calculate_capcity_percentage,
    calculate_pg_with_cf,
    # api
    # calculate_regional_air_pollution,
    calculate_power_generation_with_target,
    calculate_air_pollution_intensity,
    calculate_national_data
)

flags.DEFINE_string("data_dir", "./data", "Directory for data.")
flags.DEFINE_string("result_dir", "./results", "Directory for result.")
FLAGS = flags.FLAGS




def estimate_target_power(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    capcity_file: str
) -> pd.DataFrame:

    hourly_pg_data = get_hourly_pg_data(
        data_dir=data_dir,
        pg_file=pg_file,
        station_file=station_file,
        capcity_file=capcity_file
    )

    station_info = get_station_info(
        data_dir=data_dir,
        station_file=station_file
    )

    solar_capacity_info = get_capacity_info(
        data_dir=data_dir,
        capcity_file=capcity_file
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


def estimate_emissions(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    capcity_file: str,
):

    pg_data = get_hourly_pg_data(
        data_dir=data_dir,
        pg_file=pg_file,
        station_file=station_file,
        capcity_file=capcity_file
    )

    # Specify CSV files and columns
    csv_files = {
        'pg.csv': ['能源別', '電廠名稱', '淨發電量(度)'],
        'AirpollutantEmission.csv': ['硫氧化物排放量(kg)', '氮氧化物排放量(kg)', '粒狀污染物排放量(kg)']
    }

    ap_ef = get_ap_emission_factor(data_dir, csv_files)

    # Calculate emissions by region
    SOx_emissions = get_emissions_by_region(
        region_power_generation=pg_data,
        emission_data=ap_ef,
        target_emission='SOx'
    )

    NOx_emissions = get_emissions_by_region(
        region_power_generation=pg_data,
        emission_data=ap_ef,
        target_emission='NOx'
    )

    PM_emissions = get_emissions_by_region(
        region_power_generation=pg_data,
        emission_data=ap_ef,
        target_emission='PM'
    )

    return SOx_emissions, NOx_emissions, PM_emissions


def emission_intenisty_module(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    capcity_file: str,
    air_pollutant: Dict[str, pd.DataFrame],
    solar_generaion: pd.Series,
    target_fuel: str,
    scale: str = 'regional', # or national
) -> Tuple[pd.DataFrame, pd.DataFrame] | List[float]:

    pg_data = get_hourly_pg_data(
        data_dir=data_dir,
        pg_file=pg_file,
        station_file=station_file,
        capcity_file=capcity_file
    )

    pg_sum_exclude_solar = get_selected_pg_data(
        pg=pg_data,
        exclude_fuel=target_fuel
    )

    # regional_air_pollution = calculate_regional_air_pollution(air_pollutant)
    power_generation = calculate_power_generation_with_target(
        pg_sum_exclude_solar, 
        solar_generaion
    )
    ap_intensity = calculate_air_pollution_intensity(
        air_pollutant, 
        power_generation
    )
    pg_national, ap_national, api_national = calculate_national_data(air_pollutant, power_generation)

    if scale == 'national':
        return ap_national, api_national
    return  ap_intensity

    # flow_data = get_json_file(
    #     data_dir=data_dir,
    #     pg_file=power_flow
    # )

def main(_):

    logging.set_verbosity(logging.INFO)

    solar_pg_estimation = estimate_target_power(
        FLAGS.data_dir,
        '各機組過去發電量20220101-20220331.json',
        'powerplants_info.csv',
        'solarpower_capacity.csv'
    )

    SOx_emissions, NOx_emissions, Pm_emissions = estimate_emissions(
        FLAGS.data_dir,
        '各機組過去發電量20220101-20220331.json',
        'powerplants_info.csv',
        'solarpower_capacity.csv',
    )

    emission_intenisty_module (
        FLAGS.data_dir,
        '各機組過去發電量20220101-20220331.json',
        'powerplants_info.csv',
        'solarpower_capacity.csv',
        SOx_emissions, 
        solar_pg_estimation,
        target_fuel="太陽能"

    )

    


if __name__ == "__main__":
    app.run(main)
