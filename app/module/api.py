import json
from typing import List, Dict, Tuple, Union, TypedDict
from enum import Enum
import pandas as pd
import numpy as np
import os
import copy
from absl import logging
from collections import defaultdict

from .constants import UNIT_NAME_TO_LOCATION, EXCLUDED_REGIONS


class CalculationMode(str, Enum):
    """Enum for calculation modes."""

    ORIGINAL = "original"
    PERCENTAGE = "percentage"


class CalculationScale(str, Enum):
    """Enum for calculation scales."""

    REGIONAL = "regional"
    NATIONAL = "national"


class PowerFlowData(TypedDict):
    from_: str
    to: str
    powerkWh: List[float]


def calculate_power_generation_with_target(
    pg_wo_target: pd.DataFrame,
    target_gen_data: pd.DataFrame,
    mode: CalculationMode = CalculationMode.ORIGINAL,
) -> pd.DataFrame:
    """Calculate total power generation including target generation.

    Args:
        pg_wo_target: Power generation data without target
        target_gen_data: Target generation data
        mode: Calculation mode, either 'original' or 'percentage'

    Returns:
        DataFrame containing total power generation
    """
    if mode not in ["original", "percentage"]:
        raise ValueError(f"Invalid mode: {mode}. Must be 'original' or 'percentage'")

    power_generation = pd.DataFrame()
    for region in target_gen_data:
        if region in EXCLUDED_REGIONS:
            continue

        if mode == CalculationMode.ORIGINAL:
            power_generation[region] = [
                a + b for a, b in zip(pg_wo_target[region], target_gen_data[region])
            ]
        else:  # percentage mode
            power_generation[region] = [
                (a - b) + b
                for a, b in zip(pg_wo_target[region], target_gen_data[region])
            ]

    return power_generation


def calculate_air_pollution_intensity(
    ap_data: pd.DataFrame, pg_data: pd.DataFrame, scale: CalculationScale
) -> Union[pd.DataFrame, List[float]]:
    """Calculate air pollution intensity.

    Args:
        ap_data: Air pollution data
        pg_data: Power generation data
        scale: Calculation scale, either 'regional' or 'national'

    Returns:
        Regional or national air pollution intensity
    """
    if scale == CalculationScale.REGIONAL:
        api_regional = pd.DataFrame()
        for region in pg_data.columns:
            if region in EXCLUDED_REGIONS:
                continue

            if (pg_data[region] == 0).any():
                zero_indices = list(pg_data[region][pg_data[region] == 0].index)
                logging.warning(
                    f"Warning: {region} generation has zeros at indices {zero_indices}"
                )
                api_regional[region] = [
                    0 if b == 0 else a / b
                    for a, b in zip(ap_data[region], pg_data[region])
                ]
            else:
                api_regional[region] = [
                    a / b for a, b in zip(ap_data[region], pg_data[region])
                ]
        return api_regional

    pg_national = pg_data.sum(axis=1)
    ap_national = ap_data.sum(axis=1)
    return [a / b if b != 0 else 0 for a, b in zip(ap_national, pg_national)]


def transform_power_data(new_data: Dict) -> Dict[str, PowerFlowData]:
    """Transform power data format.

    Args:
        new_data: Raw power data

    Returns:
        Transformed power data
    """
    flow_data = defaultdict(list)

    for record in new_data["records"]["FLOW_P"]:
        unit_name = record["UNIT_NAME"]
        power_value = float(record["P"]) * 1000  # MW->kW
        location = UNIT_NAME_TO_LOCATION[unit_name]

        flow_data[unit_name].append(power_value)

    result = {}
    for unit_name, power_values in flow_data.items():
        hourly_power = [
            np.mean(power_values[i : i + 6]) for i in range(0, len(power_values), 6)
        ]
        result[unit_name] = {
            "from_": UNIT_NAME_TO_LOCATION[unit_name]["from_"],
            "to": UNIT_NAME_TO_LOCATION[unit_name]["to"],
            "powerkWh": hourly_power,
        }
    return result


def calculate_power_flow(
    pg: pd.DataFrame,
    flow: Dict[str, PowerFlowData],
    intensity: pd.DataFrame,
    emission: pd.DataFrame,
    scale: CalculationScale,
) -> pd.DataFrame:
    """Calculate power flow and emission intensity.

    Args:
        pg: Power generation data
        flow: Power flow data
        intensity: Intensity data
        emission: Emission data
        scale: Calculation scale

    Returns:
        DataFrame containing emission intensity
    """
    pg_flow = copy.deepcopy(pg).fillna(0)
    em_flow = copy.deepcopy(emission).fillna(0)

    try:
        for flow_type, flow_data in flow.items():
            origin = flow_data["from_"]
            destination = flow_data["to"]
            power_values = flow_data["powerkWh"]

            # Power flow calculation
            pg_flow[destination] = [
                x + y for x, y in zip(pg_flow[destination], power_values)
            ]
            pg_flow[origin] = [x - y for x, y in zip(pg_flow[origin], power_values)]

            # Emission flow calculation
            em = [x * y for x, y in zip(power_values, intensity[origin].fillna(0))]
            em_flow[destination] = [x + y for x, y in zip(em_flow[destination], em)]
            em_flow[origin] = [x - y for x, y in zip(em_flow[origin], em)]

    except Exception as e:
        logging.warning(f"Error in power flow calculation: {e}")
        logging.info("Switching to backup method.")
        flow = transform_power_data(flow)
        return calculate_power_flow(pg, flow, intensity, emission, scale)

    # Calculate emission intensity
    EFs = pd.DataFrame()
    for region in em_flow:
        if region in EXCLUDED_REGIONS:
            continue
        EFs[region] = [
            x / y if y != 0 else 0 for x, y in zip(em_flow[region], pg_flow[region])
        ]

    # Calculate national total
    total_em_flow = sum(em_flow[region] for region in em_flow)
    total_pg_flow = sum(pg_flow[region] for region in pg_flow)
    EFs["全台"] = [x / y if y != 0 else 0 for x, y in zip(total_em_flow, total_pg_flow)]

    return EFs
