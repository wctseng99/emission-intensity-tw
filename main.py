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
    calculate_capacity_percentage,
    calculate_pg_with_cf,
    # api
    calculate_power_generation_with_target,
    calculate_air_pollution_intensity,
    calculate_power_flow
)
# Parameter definition
flags.DEFINE_string("data_dir", "./data", "Directory for data.")
flags.DEFINE_string("result_dir", "./results", "Directory for result.")
flags.DEFINE_string(
    "raw_pg_data", "各機組過去發電量20220101-20220331.json", "file for power generation.")
flags.DEFINE_string("station_file", "powerplants_info.csv",
                    "file for power plant information.")
flags.DEFINE_string("capacity_data", "solarpower_capacity.csv",
                    "file for target energy capacity data.")
flags.DEFINE_string("power_flow_data", "pg_flow_1_3.json",
                    "file for power flow data.")
flags.DEFINE_string("target_fuel", "太陽能", "name for target fuel.")
FLAGS = flags.FLAGS



def estimate_target_power(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    capacity_file: str,
    fuel_type: str,
    capacity_target: float
) -> pd.DataFrame:

    hourly_pg_data = get_hourly_pg_data(
        data_dir=data_dir,
        pg_file=pg_file,
        station_file=station_file,
        capacity_file=capacity_file
    )

    station_info = get_station_info(
        data_dir=data_dir,
        station_file=station_file
    )

    solar_capacity_info = get_capacity_info(
        data_dir=data_dir,
        capacity_file=capacity_file
    )

    # Calculate capacity factor of the {fuel type}
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
    solar_capacity_percentage = calculate_capacity_percentage(
        capacity_data=solar_capacity_info,
        station_data=station_info,
        fuel_type=fuel_type
    )

    # Estimate the solar power in different regions with {target} solar power capacity.
    solar_pg_estimation = calculate_pg_with_cf(
        capacity_factor=region_capacity_factor,
        capacity_target=capacity_target,
        unit='GW',
        capacity_percentage=solar_capacity_percentage
    )

    return solar_pg_estimation


def emission_intenisty_module(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    capacity_file: str,
    solar_generation: pd.Series,
    target_fuel: str,
    flow_data: str,
    scale: str = 'regional',  # or national
):
    def estimate_emissions(
    ):

        pg_data = get_hourly_pg_data(
            data_dir=data_dir,
            pg_file=pg_file,
            station_file=station_file,
            capacity_file=capacity_file
        )

        # Specify CSV files and columns
        csv_files = {
            'pg.csv': ['能源別', '電廠名稱', '淨發電量(度)'],
            'AirpollutantEmission.csv': ['硫氧化物排放量(kg)', '氮氧化物排放量(kg)', '粒狀污染物排放量(kg)', '溫室氣體排放量係數(kg/kwh)']
        }

        ap_ef = get_ap_emission_factor(data_dir, csv_files)

        # Calculate emissions by region
        CO2e_emissions = get_emissions_by_region(
            region_power_generation=pg_data,
            emission_data=ap_ef,
            target_emission='CO2e'
        )

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

        return pg_data, CO2e_emissions, SOx_emissions, NOx_emissions, PM_emissions

    def estimate_emission_intensity(
    ):
        pg_sum_exclude_solar = get_selected_pg_data(
            pg=pg_data,
            exclude_fuel=target_fuel
        )

        # regional_air_pollution = calculate_regional_air_pollution(air_pollutant)
        power_generation = calculate_power_generation_with_target(
            pg_wo_target=pg_sum_exclude_solar,
            target_gen_data=solar_generation
        )

        CO2e_intensity = calculate_air_pollution_intensity(
            ap_data=CO2e_emissions,
            pg_data=power_generation,
            scale=scale
        )

        SOx_intensity = calculate_air_pollution_intensity(
            ap_data=SOx_emissions,
            pg_data=power_generation,
            scale=scale
        )

        NOx_intensity = calculate_air_pollution_intensity(
            ap_data=NOx_emissions,
            pg_data=power_generation,
            scale=scale
        )

        PM_intensity = calculate_air_pollution_intensity(
            ap_data=PM_emissions,
            pg_data=power_generation,
            scale=scale
        )

        return power_generation, CO2e_intensity, SOx_intensity, NOx_intensity, PM_intensity

    def power_flow_module():
        pg_flow = get_json_file(
            data_dir=data_dir,
            pg_file=flow_data
        )

        CO2e_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=CO2e_intensity,
            emission=CO2e_emissions
        )

        SOx_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=SOx_intensity,
            emission=SOx_emissions
        )

        NOx_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=NOx_intensity,
            emission=NOx_emissions
        )

        PM_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=PM_intensity,
            emission=PM_emissions
        )

        return CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs

    # emission module
    pg_data, CO2e_emissions, SOx_emissions, NOx_emissions, PM_emissions = estimate_emissions()
    # emission intensity module
    power_generation, CO2e_intensity, SOx_intensity, NOx_intensity, PM_intensity = estimate_emission_intensity()
    # power flow module
    CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs = power_flow_module()

    return CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs


def main(_):

    logging.set_verbosity(logging.INFO)

    # solar power module
    solar_pg_estimation = estimate_target_power(
        data_dir=FLAGS.data_dir,
        pg_file=FLAGS.raw_pg_data,
        station_file=FLAGS.station_file,
        capacity_file=FLAGS.capacity_data,
        fuel_type=FLAGS.target_fuel,
        capacity_target=7.2
    )

    # emission intensity module
    CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs = emission_intenisty_module(
        data_dir=FLAGS.data_dir,
        pg_file=FLAGS.raw_pg_data,
        station_file=FLAGS.station_file,
        capacity_file=FLAGS.capacity_data,
        solar_generation=solar_pg_estimation,
        target_fuel=FLAGS.target_fuel,
        flow_data=FLAGS.power_flow_data
    )
    

    logging.info(f'GHG emission intenisty: {CO2e_EFs.mean()}')
    logging.info(f'SOx emission intenisty: {SOx_EFs.mean()}')
    logging.info(f'NOx emission intenisty: {NOx_EFs.mean()}')
    logging.info(f'PM emission intenisty: {PM_EFs.mean()}')



if __name__ == "__main__":
    app.run(main)
