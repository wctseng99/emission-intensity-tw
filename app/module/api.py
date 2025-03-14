import json
import pandas as pd
from typing import List, Dict, Tuple
import numpy as np
import os
import copy
from absl import logging
from collections import defaultdict


def calculate_power_generation_with_target(
    pg_wo_target: pd.DataFrame, 
    target_gen_data: pd.DataFrame,
    mode: str = 'original'
) -> pd.DataFrame:
    
    if mode == 'original':

        power_generation = pd.DataFrame()
        for region in target_gen_data:
            if region == '離島':
                continue
            power_generation[region] = list(map(lambda a,b: a + b, pg_wo_target[region], target_gen_data[region]))

        return power_generation # net electricity generation
    elif mode == 'percentage':
        power_generation = pd.DataFrame()
        for region in target_gen_data:
            if region == '離島':
                continue
            power_generation[region] = list(map(lambda a,b: (a - b) + b, pg_wo_target[region], target_gen_data[region]))

        return power_generation # net electricity generation
    

def calculate_air_pollution_intensity(
    ap_data: pd.DataFrame, 
    pg_data: pd.DataFrame,
    scale: str
) -> pd.DataFrame:

    if scale == "regional":
        api_regional = pd.DataFrame()
        for region in pg_data.columns:

            if (pg_data[region] == 0).any():
                logging.warning(f"Please Check Errors: {region} generation having 0 at {list(pg_data[region][pg_data[region] == 0].index)}")
                api_regional[region] = [0 if b == 0 else a / b for a, b in zip(ap_data[region], pg_data[region])]
            else:
                api_regional[region] = list(map(lambda a, b: a / b, ap_data[region], pg_data[region]))
        return api_regional

    else:
        pg_national = pg_data.sum(axis=1)
        ap_national = ap_data.sum(axis=1)
        api_national = list(map(lambda a,b: a/b, ap_national, pg_national))
        return api_national


# for new pg_flow format
def transform_power_data(new_data):
    unit_name_to_location = {
        "北送中潮流": {"from": "北部", "to": "中部"},
        "東送中潮流": {"from": "東部", "to": "中部"},
        "南送中潮流": {"from": "南部", "to": "中部"},
        "北送東潮流": {"from": "北部", "to": "東部"},
        "中送東潮流": {"from": "中部", "to": "東部"},
        "南送東潮流": {"from": "南部", "to": "東部"},
        "北送南潮流": {"from": "北部", "to": "南部"},
        "中送南潮流": {"from": "中部", "to": "南部"},
        "東送南潮流": {"from": "東部", "to": "南部"},
        "中送北潮流": {"from": "中部", "to": "北部"},
        "東送北潮流": {"from": "東部", "to": "北部"},
        "南送北潮流": {"from": "南部", "to": "北部"},     
    }

    flow_data = defaultdict(list)

    for record in new_data["records"]["FLOW_P"]:
        unit_name = record["UNIT_NAME"]
        power_value = float(record["P"])*1000  # MW->kW
        from_region = unit_name_to_location[unit_name]["from"]
        to_region = unit_name_to_location[unit_name]["to"]

        flow_data[unit_name].append(power_value)

    result = {}
    for unit_name, power_values in flow_data.items():
        hourly_power = [np.mean(power_values[i:i+6]) for i in range(0, len(power_values), 6)]
        result[unit_name] = {
            "from": unit_name_to_location[unit_name]["from"],
            "to": unit_name_to_location[unit_name]["to"],
            "powerkWh": hourly_power,
        }
        # print(f"{len(result[unit_name]['powerkWh'])} = {len(result[unit_name]['powerkWh'])/24} days *24hours")
    return result


def calculate_power_flow(
    pg: dict, 
    flow: dict, 
    intensity: pd.DataFrame ,
    emission: pd.DataFrame,
    scale: str
):


    pg_flow = copy.deepcopy(pg).fillna(0)
    em_flow = copy.deepcopy(emission).fillna(0)

    try:
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
        # national
        total_em_flow = sum(em_flow[region] for region in em_flow)
        total_pg_flow = sum(pg_flow[region] for region in pg_flow)
        EFs['全台'] = list(map(lambda x, y: x / y if y != 0 else 0, total_em_flow, total_pg_flow))
        return EFs

    except Exception as e:
        logging.warning(f"New Data format: Switching to backup method.")
        flow = transform_power_data(flow)  
        for unit_name, flow_data in flow.items():
            origin = flow_data['from']
            destination = flow_data['to']
            power_values = flow_data['powerkWh']
            #electricity flow
            pg_flow[destination] = list(map(lambda x, y: x + y, pg_flow[destination], power_values))
            pg_flow[origin] = list(map(lambda x, y: x - y, pg_flow[origin], power_values))
            # emission flow  
            em = list(map(lambda x, y: x * y, power_values, intensity[origin].fillna(0)))  
            em_flow[destination] = list(map(lambda x, y: x + y, em_flow[destination], em))
            em_flow[origin] = list(map(lambda x, y: x - y, em_flow[origin], em))
        # intensity flow
        EFs = pd.DataFrame()
        for region in em_flow:
            if region == '離島': 
                continue
            EFs[region] = list(map(lambda x, y: x / y if y != 0 else 0, em_flow[region], pg_flow[region]))  
        # national
        total_em_flow = sum(em_flow[region] for region in em_flow)
        total_pg_flow = sum(pg_flow[region] for region in pg_flow)
        EFs['全台'] = list(map(lambda x, y: x / y if y != 0 else 0, total_em_flow, total_pg_flow))
        return EFs