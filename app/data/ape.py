import json
import os
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict
from pathlib import Path


def get_ap_emission_factor(
    data_dir: str, csv_files: Dict[str, List[str]]
) -> pd.DataFrame:

    dfs: List[pd.DataFrame] = []
    for csv_name, columns in csv_files.items():
        csv_path = f"{data_dir}/{csv_name}"
        df = pd.read_csv(csv_path, usecols=columns)
        dfs.append(df)

    merged_df = pd.concat(dfs, axis=1)

    # Perform additional processing
    pg: pd.DataFrame = merged_df[["能源別", "電廠名稱", "淨發電量(度)"]]
    airPollution: pd.DataFrame = merged_df[
        [
            "硫氧化物排放量(kg)",
            "氮氧化物排放量(kg)",
            "粒狀污染物排放量(kg)",
            "溫室氣體排放量係數(kg/kwh)",
        ]
    ]

    df: pd.DataFrame = pg.merge(
        airPollution, how="inner", left_index=True, right_index=True
    )
    df["SOx (g/kWh)"] = df["硫氧化物排放量(kg)"].astype(float).mul(1000) / df[
        "淨發電量(度)"
    ].astype(float)
    df["NOx (g/kWh)"] = df["氮氧化物排放量(kg)"].astype(float).mul(1000) / df[
        "淨發電量(度)"
    ].astype(float)
    df["PM (g/kWh)"] = df["粒狀污染物排放量(kg)"].astype(float).mul(1000) / df[
        "淨發電量(度)"
    ].astype(float)
    df["CO2e (g/kWh)"] = df["溫室氣體排放量係數(kg/kwh)"].astype(float).mul(1000)
    df.set_index("電廠名稱", inplace=True)

    return df


def get_ghg_emission_factor(data_dir: str, emission_data: str) -> pd.DataFrame:
    """
    Calculate greenhouse gas emission factors

    Args:
        data_dir: Path to the data directory
        emission_data: Emission data filename

    Returns:
        DataFrame: DataFrame containing the calculation results
    """

    EMISSION_FACTORS = {
        "carbon_dioxide": {
            "Coal": 95237.5,
            "Gas": 56100,
            "Diesel": 74100,
            "Oil": 77400,
        },
        "methane": {
            "Coal": 1.0,
            "Gas": 1.0,
            "Diesel": 3.0,
            "Oil": 3.0,
        },
        "nitrous_oxide": {
            "Coal": 1.5,
            "Gas": 0.1,
            "Diesel": 0.6,
            "Oil": 0.6,
        },
    }

    GWP = {
        "carbon_dioxide": 1.0,
        "methane": 25.0,
        "nitrous_oxide": 298.0,
    }

    # Heat value conversion factor (J to PJ)
    HEAT_CONVERSION_FACTOR = 4.1868 * (10**-9)

    file_path = Path(data_dir, emission_data)
    df = pd.read_csv(file_path)

    numeric_columns = [
        "Gross Electricity Generation",
        "Gross Low Heating Value",
        "Net Electricity Generation",
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Power Generation Heat"] = (
        df["Gross Electricity Generation"]
        * df["Gross Low Heating Value"]
        * HEAT_CONVERSION_FACTOR
    )

    emissions_data = [
        ("carbon_dioxide", "Carbon Dioxide Emissions"),
        ("methane", "Methane Emissions"),
        ("nitrous_oxide", "Nitrous Oxide Emissions"),
    ]

    for emission_type, column_name in emissions_data:
        # Create emission factor mapping
        factors = pd.Series(EMISSION_FACTORS[emission_type])

        # Calculate emissions
        df[column_name] = df.apply(
            lambda row: row["Power Generation Heat"] * factors.get(row["Type"], 0),
            axis=1,
        )

    # Calculate total greenhouse gas emissions (CO2 equivalent)
    df["Total GHG Emissions"] = sum(
        df[col] * GWP[emission_type]
        for emission_type, col in zip(
            ["carbon_dioxide", "methane", "nitrous_oxide"],
            [
                "Carbon Dioxide Emissions",
                "Methane Emissions",
                "Nitrous Oxide Emissions",
            ],
        )
    )

    # Calculate emission factor (kg/kWh)
    df["Emission Factor"] = df["Total GHG Emissions"] / df["Net Electricity Generation"]

    # print(df)
    return df


# calculate the air pollutant emissions
def get_emissions_by_region(
    region_power_generation: Dict[str, Dict],
    emission_data: pd.DataFrame,
    target_emission: str,
) -> pd.DataFrame:

    emission_label: Dict = {
        "SOx": "SOx (g/kWh)",
        "NOx": "NOx (g/kWh)",
        "PM": "PM (g/kWh)",
        "CO2e": "CO2e (g/kWh)",
    }

    emissions: Dict[str, pd.DataFrame] = {}

    for region in region_power_generation:
        regional_emissions: pd.DataFrame = pd.DataFrame()
        for source in emission_data["能源別"].unique():
            for energy in region_power_generation[region]:
                if energy == source:
                    for plant in region_power_generation[region][energy]:
                        plant_data = region_power_generation[region][energy][plant]
                        regional_emissions[plant] = emission_data.loc[
                            plant, emission_label[target_emission]
                        ] * pd.Series(plant_data)

        emissions[region] = regional_emissions

    regional_air_pollution = pd.DataFrame()
    for region in emissions:
        regional_air_pollution[region] = emissions[region].sum(axis=1)
    regional_air_pollution.fillna(0, inplace=True)
    regional_air_pollution.drop(columns="離島", inplace=True)

    return regional_air_pollution
