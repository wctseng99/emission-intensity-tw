import json
import pandas as pd
from typing import List, Dict, Tuple
import numpy as np
import os
import copy


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


def calculate_power_flow(
    pg: dict, 
    flow: dict, 
    intensity: pd.DataFrame ,
    emission: pd.DataFrame
):

    pg_flow = copy.deepcopy(pg).fillna(0)
    em_flow = copy.deepcopy(emission).fillna(0)
    for type in flow:    
        origin = flow[type]['from']
        destination = flow[type]['to']
        #electricity flow
        pg_flow[destination] = list(map(lambda x,y: x+y, pg_flow[destination], flow[type]['powerkWh']))
        pg_flow[origin] = list(map(lambda x,y: x-y, pg_flow[origin], flow[type]['powerkWh']))
        # emission flow  
        em = list(map(lambda x,y: x*y, flow[type]['powerkWh'], intensity[origin].fillna(0))) 
        em_flow[destination] = list(map(lambda x,y: x+y, em_flow[destination], em))
        em_flow[origin] =list(map(lambda x,y: x-y, em_flow[origin], em))
    # intensity flow
    EFs  = pd.DataFrame()
    for region in em_flow:
        if region == '離島':
            continue
        EFs[region] = list(map(lambda x,y: x/y, em_flow[region], pg_flow[region]))
    return EFs