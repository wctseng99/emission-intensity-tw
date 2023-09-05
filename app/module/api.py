import json
import pandas as pd
from typing import List, Dict, Tuple
import numpy as np
import os


def calculate_power_generation_with_target(
    pg_wo_target: pd.DataFrame, 
    target_gen_data: pd.DataFrame
) -> pd.DataFrame:

    power_generation = pd.DataFrame()
    for region in target_gen_data:
        if region == '離島':
            continue
        power_generation[region] = list(map(lambda a,b: a + b, pg_wo_target[region], target_gen_data[region]))
    return power_generation

def calculate_air_pollution_intensity(
    ap_data: pd.DataFrame, 
    pg_data: pd.DataFrame,
    scale: str = "regional"
) -> pd.DataFrame:

    
    if scale == "regional":
        api_regional = pd.DataFrame()
        for region in pg_data.columns:
            api_regional[region] = list(map(lambda a,b: a/b, ap_data[region], pg_data[region]))  
        return api_regional

    else:
        pg_national = pg_data.sum(axis=1)
        ap_national = ap_data.sum(axis=1)
        api_national = list(map(lambda a,b: a/b, ap_national, pg_national))
        return api_national
