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
            # "溫室氣體排放量係數(kg/kwh)",
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
    # df["CO2e (g/kWh)"] = df["溫室氣體排放量係數(kg/kwh)"].astype(float).mul(1000)

    basic_emission_factors = get_ghg_emission_factor(data_dir, "generation_info.csv")

    df.set_index("電廠名稱", inplace=True)
    df = df.join(basic_emission_factors, how="left")

    df["CO2e (g/kWh)"] = df["Basic Emission Factor"].astype(float).mul(1000)

    output_path = "./emission_factors_test.csv"
    df.to_csv(output_path, encoding="utf-8-sig")

    return df


def get_ghg_emission_factor(data_dir: str, generation_info: str) -> pd.DataFrame:
    """
    Calculate greenhouse gas emission factors called by "get_ap_emission_factor"

    Args:
        data_dir: Path to the data directory
        generation_info: Emission data filename

    Returns:
        DataFrame: DataFrame containing the emission factors
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

    emissions_data = [
        ("carbon_dioxide", "Carbon Dioxide Emissions"),
        ("methane", "Methane Emissions"),
        ("nitrous_oxide", "Nitrous Oxide Emissions"),
    ]

    numeric_columns = [
        "Gross Electricity Generation",
        "Gross Low Heating Value",
        "Net Electricity Generation",
    ]

    # Heat value conversion factor (J to PJ)
    HEAT_CONVERSION_FACTOR = 4.1868 * (10**-9)

    file_path = Path(data_dir, generation_info)
    df = pd.read_csv(file_path)

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Power Generation Heat"] = (
        df["Gross Electricity Generation"]
        * df["Gross Low Heating Value"]
        * HEAT_CONVERSION_FACTOR
    )

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
    df["Basic Emission Factor"] = (
        df["Total GHG Emissions"] / df["Net Electricity Generation"]
    )

    # --------optional: adjusted emission factor----------------------

    # Just demonstrate how to calculate the adjusted emission factor.
    # To align with the paper's methods, we don't use it.
    plant_emissions = df.groupby("Plant")["Total GHG Emissions"].sum().reset_index()
    plant_emissions.columns = ["Plant", "Total GHG Emissions"]

    reference_path = Path(data_dir, "emission_reference.csv")
    reference_df = pd.read_csv(reference_path)

    plant_emissions = plant_emissions.merge(
        reference_df[["Plant", "Reference Emission (kg)"]], on="Plant", how="left"
    )
    plant_emissions["Emission Ratio"] = (
        plant_emissions["Reference Emission (kg)"]
        / plant_emissions["Total GHG Emissions"]
    ).fillna(1)

    ratio_dict = dict(zip(plant_emissions["Plant"], plant_emissions["Emission Ratio"]))

    df["adjusted Emission Factor"] = df.apply(
        lambda row: row["Basic Emission Factor"] * ratio_dict.get(row["Plant"], 1),
        axis=1,
    )

    # ----------End: adjusted emission factor--------------------------

    result_df = df[["Generator", "Basic Emission Factor"]]
    result_df.set_index("Generator", inplace=True)

    return result_df


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
