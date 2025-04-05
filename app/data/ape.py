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

    fuel_emission_factor = {
        "carbon_dioxide": {
            "Coal": float(95237.5),
            "Gas": float(56100),
            "Diesel": float(74100),
            "Oil": float(77400),
        },
        "methane": {
            "Coal": float(1),
            "Gas": float(1),
            "Diesel": float(3),
            "Oil": float(3),
        },
        "nitrous_oxide": {
            "Coal": float(1.5),
            "Gas": float(0.1),
            "Diesel": float(0.6),
            "Oil": float(0.6),
        },
    }

    global_warming_potential = {
        "carbon_dioxide": float(1),
        "methane": float(25),
        "nitrous_oxide": float(298),
    }

    path = Path(data_dir, emission_data)
    raw_emission = pd.read_csv(path)

    for col in ["Gross Electricity Generation", "Gross Low Heating Value"]:
        if col in raw_emission.columns:
            raw_emission[col] = pd.to_numeric(raw_emission[col], errors="coerce")

    raw_emission["Power Generation Heat"] = (
        raw_emission["Gross Electricity Generation"]
        * raw_emission["Gross Low Heating Value"]
        * 4.1868
        * (10**-9)
    )

    emissions_types = ["carbon_dioxide", "methane", "nitrous_oxide"]
    output_columns = [
        "Carbon Dioxide Emissions",
        "Methane Emissions",
        "Nitrous Oxide Emissions",
    ]

    def calculate_emissions_for_type(emission_type, output_column):

        factors = pd.Series(fuel_emission_factor[emission_type])

        raw_emission[output_column] = raw_emission.apply(
            lambda row: row["Power Generation Heat"] * factors.get(row["Type"], 0),
            axis=1,
        )

    for emission_type, output_column in zip(emissions_types, output_columns):
        calculate_emissions_for_type(emission_type, output_column)

    # unit: kg
    raw_emission["Total GHG Emissions"] = sum(
        raw_emission[col] * global_warming_potential[emission_type]
        for col, emission_type in zip(output_columns, emissions_types)
    )

    raw_emission["Emission Factor"] = raw_emission[
        "Total GHG Emissions"
    ] / pd.to_numeric(raw_emission["Net Electricity Generation"], errors="coerce")

    # print(raw_emission)


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
