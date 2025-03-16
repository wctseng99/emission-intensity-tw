import json
import numpy as np
import os
import pandas as pd
import logging
import csv
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
    calculate_power_flow,
    # figure
    create_figure_CF,
    create_figure_EI_total,
)


# Parameter definition
flags.DEFINE_string("data_dir", "./data/2024", "Directory for data.") # year!!!
flags.DEFINE_string("result_dir", "./results/2024", "Directory for result.") # year!!!
flags.DEFINE_string("station_file", "powerplants_info.csv","file for power plant information.")
flags.DEFINE_string("capacity_data", "capacity.csv","file for target energy capacity data.")
flags.DEFINE_list("raw_pg_data", 
                  [
                    "各機組過去發電量20240501-20240731.json", 
                    "各機組過去發電量20240801-20241031.json", 
                    # "各機組過去發電量20220101-20220331.json", 
                    # "各機組過去發電量20220401-20220630.json", 
                    # "各機組過去發電量20220701-20220930.json", 
                    # "各機組過去發電量20221001-20221231.json",
                  ],
                  "file for power generation.")
flags.DEFINE_list("power_flow_data", 
                  [
                    "pg_flow_5_7.json", 
                    "pg_flow_8_10.json", 
                    # "pg_flow_1_3.json", 
                    # "pg_flow_4_6.json", 
                    # "pg_flow_7_9.json", 
                    # "pg_flow_10_12.json",
                  ], 
                  "file for power flow data.")
flags.DEFINE_list("datetime_range", 
                  [
                    pd.date_range(start="2024-05-01 00:00:00", end="2024-07-31 23:00:00", freq='h'),
                    pd.date_range(start="2024-08-01 00:00:00", end="2024-10-31 23:00:00", freq='h'),
                #     pd.date_range(start="2021-01-01 00:00:00", end="2021-03-31 23:00:00", freq='h'),
                #     pd.date_range(start="2021-04-01 00:00:00", end="2021-06-30 23:00:00", freq='h'),
                #     pd.date_range(start="2021-07-01 00:00:00", end="2021-09-30 23:00:00", freq='h'),
                #     pd.date_range(start="2021-10-01 00:00:00", end="2021-12-31 23:00:00", freq='h')
                  ],
                  "datetime_range.")

flags.DEFINE_list("data_period_list", 
                  [
                    # "1~3", "4~6", "7~9", "10~12"
                    "5~7", "8~10"
                  ],
                  "data period for power_flow_data and raw_pg_data")
flags.DEFINE_list("fuel_type", 
                  [
                    "太陽能",
                    "離岸風電", 
                    "陸域風電"
                  ], 
                  "names for target fuels.")
flags.DEFINE_list("capacity_target",  
                  [
                    # "0",
                    # "0",
                    # "0",
                    ## 2021 (GW) ##
                    # "9.72",  
                    # "0.745", 
                    # "0.836"
                    ## 2024 (GW) ##
                    "13.2",
                    "2.348",  
                    "0.915",
                    ## 2050 GOAL? (GW) ##
                  ], 
                  "target capacity of target fuel")
flags.DEFINE_list("figure_limits",[[00, 700], [0.0, 0.13], [0.0, 0.20], [0.00, 0.0065]], "fixed y-axis upper and lower bounds for EI figures")
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

    return pg_estimation, region_capacity_factor, national_capacity_factor, capacity_percentage


def emission_intenisty_module(
    data_dir: Path,
    pg_file: str,
    station_file: str,
    generation: pd.Series, # =pg_estimation
    fuel_type: list,
    flow_data: str,
    scale: str = 'regional',  # regional or national
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
            emission=CO2e_emissions,
            scale=scale
        )

        SOx_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=SOx_intensity,
            emission=SOx_emissions,
            scale=scale
        )

        NOx_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=NOx_intensity,
            emission=NOx_emissions,
            scale=scale
        )

        PM_EFs = calculate_power_flow(
            pg=power_generation,
            flow=pg_flow,
            intensity=PM_intensity,
            emission=PM_emissions,
            scale=scale
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

    CO2e_EI_year, SOx_EI_year, NOx_EI_year, PM_EI_year = [], [], [], [] 

    for data_idx, (raw_pg_data, power_flow_data, data_period, datetime_range) in enumerate(zip(FLAGS.raw_pg_data, FLAGS.power_flow_data, FLAGS.data_period_list, FLAGS.datetime_range)):
        pg_estimation_total = pd.DataFrame()
        for fuel_idx, (fuel_type, capacity_target) in enumerate(zip(FLAGS.fuel_type, FLAGS.capacity_target)):     
            pg_estimation, region_capacity_factor, national_capacity_factor, capacity_percentage = estimate_target_power(
                data_dir=FLAGS.data_dir,
                pg_file=raw_pg_data,
                station_file=FLAGS.station_file,
                capacity_file=FLAGS.capacity_data,
                # Because offshore wind power data is lacking, it is being replaced with onshore wind power data.
                fuel_type='陸域風電' if fuel_type == '離岸風電' else fuel_type,
                capacity_target=float(capacity_target)
            )  
            pg_estimation_total = pg_estimation if pg_estimation_total.empty else pg_estimation_total.add(pg_estimation, fill_value=0)            
            logging.info(f'Month={data_period}, Fuel={fuel_type}') 
            logging.info(f'The avg of national capacity factor:{national_capacity_factor.mean()}.')
            logging.info(f'national power generation (kWh): {pg_estimation.sum().sum()}.')

            # for displaying real result of offshore wind power
            if fuel_type == '離岸風電':
                pg_estimation, region_capacity_factor, national_capacity_factor, capacity_percentage = estimate_target_power(
                data_dir=FLAGS.data_dir,
                pg_file=raw_pg_data,
                station_file=FLAGS.station_file,
                capacity_file=FLAGS.capacity_data,
                fuel_type=fuel_type,
                capacity_target=float(capacity_target)
                )
            #logging.info(f'The avg of regional capacity factor:\n{region_capacity_factor.mean()}.')
            for region in capacity_percentage:
                logging.info(f'{region} capacity percentage: {capacity_percentage[region]}.')
            region_capacity_factor.to_csv(rf'{FLAGS.result_dir}/region_capacity_factor_{fuel_type}_{data_period}.csv', index=False, encoding='utf-8-sig') 
            

        CO2e_EFs, SOx_EFs, NOx_EFs, PM_EFs = emission_intenisty_module(
            data_dir=FLAGS.data_dir,
            pg_file=raw_pg_data,
            station_file=FLAGS.station_file,
            generation=pg_estimation_total,
            fuel_type=FLAGS.fuel_type,
            flow_data=power_flow_data
        )

        CO2e_EFs_kg = CO2e_EFs / 1000 # gCO2e/kWh -> kgCO2e/kWh
        CO2e_EFs_kg.index = datetime_range
        CO2e_EFs_kg.columns = [f"{col} (kgCO2e/kWh)" for col in CO2e_EFs_kg.columns]
        CO2e_EFs_kg.to_csv(rf'{FLAGS.result_dir}/CO2e_EI_{data_period}_kg.csv', index=True, encoding='utf-8-sig')
        CO2e_EFs.index = datetime_range
        CO2e_EFs.to_csv(rf'{FLAGS.result_dir}/CO2e_EI_{data_period}.csv', index=True, encoding='utf-8-sig')
        SOx_EFs.to_csv(rf'{FLAGS.result_dir}/SOx_EI_{data_period}.csv', index=True, encoding='utf-8-sig')
        NOx_EFs.to_csv(rf'{FLAGS.result_dir}/NOx_EI_{data_period}.csv', index=True, encoding='utf-8-sig')
        PM_EFs.to_csv(rf'{FLAGS.result_dir}/PM_EI_{data_period}.csv', index=True, encoding='utf-8-sig')
        
        CO2e_EI_year.append(CO2e_EFs.mean())
        SOx_EI_year.append(SOx_EFs.mean())
        NOx_EI_year.append(NOx_EFs.mean())
        PM_EI_year.append(PM_EFs.mean())

    create_figure_CF(FLAGS.result_dir, FLAGS.data_period_list, "太陽能", "region_capacity_factor")
    create_figure_CF(FLAGS.result_dir, FLAGS.data_period_list, "陸域風電", "region_capacity_factor")
    create_figure_CF(FLAGS.result_dir, FLAGS.data_period_list, "離岸風電", "region_capacity_factor")
    create_figure_EI_total(FLAGS.result_dir, FLAGS.data_period_list, ["CO2e_EI", "SOx_EI", "NOx_EI", "PM_EI",], FLAGS.figure_limits)

    logging.info(f'The excluded fuel types: {FLAGS.fuel_type}.')
    for (data, EI_name) in zip([CO2e_EI_year, SOx_EI_year, NOx_EI_year, PM_EI_year], ["CO2e", "SOx", "NOx", "PM"]):
        for i, data_period in enumerate(FLAGS.data_period_list):
            logging.info(f'{data_period}, {EI_name} emission intensity (g/kWh): \n{data[i]}')
        logging.info(f'Annual average {EI_name} emission intensity (g/kWh): \n{pd.DataFrame(data).mean()}')
        # Calculate national average directly 
        data = pd.DataFrame(data).select_dtypes(include=['number'])
        logging.info(f'Annual national average {EI_name} emission intensity (g/kWh): {pd.DataFrame(data).mean().mean()}') #

if __name__ == "__main__":
    app.run(main)
