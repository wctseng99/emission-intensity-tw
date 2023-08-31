import json
import pandas as pd
from typing import List, Dict, Tuple
import numpy as np

def load_json_files(
    data_dir: str, 
    file_names: List[str]
) -> Dict[str, Dict]:

    loaded_data: Dict[str, Dict] = {}
    for file_name in file_names:
        file_path = f"{data_dir}/{file_name}"
        with open(file_path) as f:
            data = json.load(f)
        key = file_name.split(".")[0]  # Extract the key by removing the file extension
        loaded_data[key] = data
    return loaded_data


def process_data(
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
    airPollution: pd.DataFrame = merged_df[['硫氧化物排放量(kg)', '氮氧化物排放量(kg)', '粒狀污染物排放量(kg)']]
    
    df: pd.DataFrame = pg.merge(airPollution, how='inner', left_index=True, right_index=True)
    df['SOx (g/kWh)'] = df['硫氧化物排放量(kg)'].mul(1000) / df['淨發電量(度)']
    df['NOx (g/kWh)'] = df['氮氧化物排放量(kg)'].mul(1000) / df['淨發電量(度)']
    df['PM (g/kWh)'] = df['粒狀污染物排放量(kg)'].mul(1000) / df['淨發電量(度)']
    df['能源別'] = df['能源別'].replace(regex={'燃煤':'COAL', '燃氣':'LNG', '燃油':'OIL'})
    df.set_index('電廠名稱', inplace=True)
    
    return df


# calculate the air pollutant emissions
def calculate_emissions_by_region(
    region_power_generation: Dict[str, Dict], 
    emission_data: pd.DataFrame
) -> tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:

    SOx_emissions: Dict[str, pd.DataFrame] = {}
    NOx_emissions: Dict[str, pd.DataFrame] = {}
    Pm_emissions: Dict[str, pd.DataFrame] = {}

    for region in region_power_generation:
        SOx_region: pd.DataFrame = pd.DataFrame()
        NOx_region: pd.DataFrame = pd.DataFrame()
        Pm_region: pd.DataFrame = pd.DataFrame()


        for source in emission_data['能源別'].unique():
            for energy in region_power_generation[region]:
                if energy == source:
                    for plant in region_power_generation[region][energy]:
                        plant_data = region_power_generation[region][energy][plant]

                        SOx_region[plant] = emission_data.loc[plant, 'SOx (g/kWh)'] * pd.Series(plant_data)
                        NOx_region[plant] = emission_data.loc[plant, 'NOx (g/kWh)'] * pd.Series(plant_data)
                        Pm_region[plant] = emission_data.loc[plant, 'PM (g/kWh)'] * pd.Series(plant_data)

        SOx_emissions[region] = SOx_region
        NOx_emissions[region] = NOx_region
        Pm_emissions[region] = Pm_region

    return SOx_emissions, NOx_emissions, Pm_emissions


# Calculate the air polluatnt emission intensity
def calculate_regional_air_pollution(
    air_pollutant_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:

    regional_air_pollution: pd.DataFrame = pd.DataFrame()
    for region in air_pollutant_data:
        regional_air_pollution[region] = air_pollutant_data[region].sum(axis=1)
    regional_air_pollution.fillna(0, inplace=True)
    regional_air_pollution.drop(columns='離島', inplace=True)
    return regional_air_pollution

def calculate_power_generation_with_solar(
    pg_type: pd.DataFrame, 
    solar_gen_data: pd.Series
) -> pd.DataFrame:

    power_generation = pd.DataFrame()
    for region in solar_gen_data:
        if region == '離島':
            continue
        if pg_type is pg_fossil and region == '東部':
            continue
        power_generation[region] = list(map(lambda a,b: a+b, pg_type[region], solar_gen_data[region]))
    return power_generation

def calculate_air_pollution_intensity(
    ap_data: pd.DataFrame, 
    pg_data: pd.DataFrame
) -> pd.DataFrame:

    ap_intensity: pd.DataFrame = pd.DataFrame()
    for region in pg_data.columns:
        ap_intensity[region] = list(map(lambda a,b: a/b, ap_data[region], pg_data[region]))  
    return ap_intensity

def calculate_national_data(
    ap_data: pd.DataFrame, 
    pg_data: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series, List[float]]:

    pg_national = pg_data.sum(axis=1)
    ap_national = ap_data.sum(axis=1)
    api_national = list(map(lambda a,b: a/b, ap_national, pg_national))
    
    return pg_national, ap_national, api_national

    
def emission_intenisty_module(
    air_pollutant: Dict[str, pd.DataFrame], 
    pg_type: pd.DataFrame, 
    solar_generaion: pd.Series,
    scale: str = 'regional' # or national
    ) -> Tuple[pd.DataFrame, pd.DataFrame] | Tuple[pd.Series, List[float]]:
    
    regional_air_pollution = calculate_regional_air_pollution(air_pollutant)
    power_generation = calculate_power_generation_with_solar(pg_type, solar_generaion)
    ap_intensity = calculate_air_pollution_intensity(regional_air_pollution, power_generation)
    pg_national, ap_national, api_national = calculate_national_data(regional_air_pollution, power_generation)
    
    if scale == 'national':
        return ap_national, api_national
    return regional_air_pollution, ap_intensity




# List of file names, excluding paths
file_names = [
    'Regional_PGs.json',
    'pg_all_wo_solar.json',
    'solar_gen.json',
    'flow_data.json',
    'pg_fossil.json'
]

# Directory path for data files
data_dir = '../../data'

loaded_json_data = load_json_files(data_dir, file_names)

# Specify CSV files and their columns
csv_files = {
    'pg.csv': ['能源別', '電廠名稱', '淨發電量(度)'],
    'AirpollutantEmission.csv': ['硫氧化物排放量(kg)', '氮氧化物排放量(kg)', '粒狀污染物排放量(kg)']
}

PGs = loaded_json_data['Regional_PGs']
PGs_all_wo_solar = loaded_json_data['pg_all_wo_solar']
solar_gen = loaded_json_data['solar_gen']
flow_data = loaded_json_data['flow_data']
pg_fossil = loaded_json_data['pg_fossil']

# Read CSV files and process data
processed_df = process_data(data_dir, csv_files)

# Calculate emissions by region
SOx_emissions, NOx_emissions, Pm_emissions = calculate_emissions_by_region(PGs, processed_df)
# print(ＮOx_emissions['北部'])


SOx_ap, SOx_api = emission_intenisty_module(
    air_pollutant=SOx_emissions, 
    pg_type=PGs_all_wo_solar, 
    solar_generaion=solar_gen['7.2'],
    )

NOx_ap, NOx_api = emission_intenisty_module(
    air_pollutant=NOx_emissions, 
    pg_type=PGs_all_wo_solar, 
    solar_generaion=solar_gen['7.2'],
    )

Pm_ap, Pm_api = emission_intenisty_module(
    air_pollutant=Pm_emissions, 
    pg_type=PGs_all_wo_solar, 
    solar_generaion=solar_gen['7.2'],
    )

# power flow 




