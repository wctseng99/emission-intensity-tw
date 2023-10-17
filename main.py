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
flags.DEFINE_string("station_file", "powerplants_info.csv","file for power plant information.")
flags.DEFINE_string("capacity_data", "capacity.csv","file for target energy capacity data.")
flags.DEFINE_list("raw_pg_data", 
                  [
                    "各機組過去發電量20220101-20220331.json", 
                    "各機組過去發電量20220401-20220630.json", 
                    "各機組過去發電量20220701-20220930.json", 
                    "各機組過去發電量20221001-20221231.json",
                  ],
                  "file for power generation.")
flags.DEFINE_list("power_flow_data", 
                  [
                    "pg_flow_1_3.json", 
                    "pg_flow_4_6.json", 
                    "pg_flow_7_9.json", 
                    "pg_flow_10_12.json",
                  ], 
                  "file for power flow data.")
flags.DEFINE_list("fuel_type", 
                  [
                    "太陽能", 
                    "陸域風電", 
                    "離岸風電",
                  ], 
                  "names for target fuels.")
flags.DEFINE_list("capacity_target", 
                  [
                    "7.2", 
                    "0.74", 
                    "0.24",
                  ], 
                  "target capacity of target fuel")
#flags.DEFINE_list("figure_limits",[[00, 700], [0.0, 0.13], [0.0, 0.20], [0.00, 0.0065]])
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
    )

    station_info = get_station_info(
        data_dir=data_dir,
        station_file=station_file
    )

    capacity_info = get_capacity_info(
        data_dir=data_dir,
        capacity_file=capacity_file,
        fuel_type=fuel_type
    )

    # Calculate capacity factor of the {fuel type}
    region_capacity_factor = calculate_capacity_factor(
        hourly_pg=hourly_pg_data,
        capacity_data=capacity_info,
        fuel_type=fuel_type,
        scale= "regional"
    )

    national_capacity_factor = calculate_capacity_factor(
        hourly_pg=hourly_pg_data,
        capacity_data=capacity_info,
        fuel_type=fuel_type,
        scale="national"
    )

    # Calculate solar power capacity percentage in different regions.
    capacity_percentage = calculate_capacity_percentage(
        capacity_data=capacity_info,
        station_data=station_info,
        fuel_type=fuel_type
    )

    # Estimate the solar power in different regions with {target} solar power capacity.
    pg_estimation = calculate_pg_with_cf(
        capacity_factor=region_capacity_factor,
        capacity_target=capacity_target,
        unit='GW',
        capacity_percentage=capacity_percentage
    )

    return pg_estimation, region_capacity_factor, national_capacity_factor


def emission_intenisty_module(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    generation: pd.Series,
    fuel_type: list,
    flow_data: str,
    scale: str = 'regional',  # or national
):
    def estimate_emissions(
    ):

        pg_data = get_hourly_pg_data(
            data_dir=data_dir,
            pg_file=pg_file,
            station_file=station_file,
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
        pg_sum_exclude_fuel_type = get_selected_pg_data(
            pg=pg_data,
            exclude_fuel=fuel_type
        )

        # regional_air_pollution = calculate_regional_air_pollution(air_pollutant)
        power_generation = calculate_power_generation_with_target(
            pg_wo_target=pg_sum_exclude_fuel_type,
            target_gen_data=generation
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

    for data_idx, (raw_pg_data, power_flow_data, data_period) in enumerate(zip(FLAGS.raw_pg_data, FLAGS.power_flow_data, ["1~3", "4~6", "7~9", "10~12"])):
        print(data_period)
        pg_estimation_total = pd.DataFrame()
        
        for fuel_idx, (fuel_type, capacity_target) in enumerate(zip(FLAGS.fuel_type, FLAGS.capacity_target)):
            print(fuel_type)
            pg_estimation, region_capacity_factor, national_capacity_factor = estimate_target_power(
                data_dir=FLAGS.data_dir,
                pg_file=raw_pg_data,
                station_file=FLAGS.station_file,
                capacity_file=FLAGS.capacity_data,
                fuel_type=fuel_type,
                capacity_target=float(capacity_target)
            )

            pg_estimation_total = pg_estimation if pg_estimation_total.empty else pg_estimation_total.add(pg_estimation, fill_value=0)

        CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs = emission_intenisty_module(
            data_dir=FLAGS.data_dir,
            pg_file=raw_pg_data,
            station_file=FLAGS.station_file,
            generation=pg_estimation_total,
            fuel_type=FLAGS.fuel_type,
            flow_data=power_flow_data
        )

        for emission, name in zip([CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs], ["CO2e", "SOx", "NOx", "PM"]):
            logging.info(f'{name} emission intensity: \n{emission.mean()}')



if __name__ == "__main__":
    app.run(main)
