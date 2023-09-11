import json
import os
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict



def get_ap_emission_factor(
    data_dir: str, 
    csv_files: Dict[str, List[str]]
) -> pd.DataFrame:
    
    dfs: List[pd.DataFrame] = []
    for csv_name, columns in csv_files.items():
        csv_path = f'{data_dir}/{csv_name}'
        df = pd.read_csv(csv_path, usecols=columns)
        dfs.append(df)
    
    merged_df = pd.concat(dfs, axis=1)
    
    # Perform additional processing
    pg: pd.DataFrame = merged_df[['能源別', '電廠名稱', '淨發電量(度)']]
    airPollution: pd.DataFrame = merged_df[['硫氧化物排放量(kg)', '氮氧化物排放量(kg)', '粒狀污染物排放量(kg)', '溫室氣體排放量係數(kg/kwh)']]
    
    df: pd.DataFrame = pg.merge(airPollution, how='inner', left_index=True, right_index=True)
    df['SOx (g/kWh)'] = df['硫氧化物排放量(kg)'].mul(1000) / df['淨發電量(度)']
    df['NOx (g/kWh)'] = df['氮氧化物排放量(kg)'].mul(1000) / df['淨發電量(度)']
    df['PM (g/kWh)'] = df['粒狀污染物排放量(kg)'].mul(1000) / df['淨發電量(度)']
    df['CO2e (g/kWh)'] = df['溫室氣體排放量係數(kg/kwh)'].mul(1000)
    df.set_index('電廠名稱', inplace=True)
    
    return df


# calculate the air pollutant emissions
def get_emissions_by_region(
    region_power_generation: Dict[str, Dict], 
    emission_data: pd.DataFrame,
    target_emission: str
) -> pd.DataFrame:

    emission_label: Dict = {
        'SOx': 'SOx (g/kWh)',
        'NOx': 'NOx (g/kWh)',
        'PM': 'PM (g/kWh)', 
        'CO2e': 'CO2e (g/kWh)'
    }

    emissions: Dict[str, pd.DataFrame] = {}

    for region in region_power_generation:
        regional_emissions: pd.DataFrame = pd.DataFrame()
        for source in emission_data['能源別'].unique():
            for energy in region_power_generation[region]:
                if energy == source:
                    for plant in region_power_generation[region][energy]:
                        plant_data = region_power_generation[region][energy][plant]
                        regional_emissions[plant] = emission_data.loc[plant, emission_label[target_emission]] * pd.Series(plant_data)

        emissions[region] = regional_emissions

    regional_air_pollution = pd.DataFrame()
    for region in emissions:
        regional_air_pollution[region] = emissions[region].sum(axis=1)
    regional_air_pollution.fillna(0, inplace=True)
    regional_air_pollution.drop(columns='離島', inplace=True)

    return regional_air_pollution
