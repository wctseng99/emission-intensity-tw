from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path

from app.data import (
    get_hourly_pg_data,
    get_ap_emission_factor,
    get_emissions_by_region,
    get_selected_pg_data,
    get_json_file,
)
from app.module import (
    calculate_power_generation_with_target,
    calculate_air_pollution_intensity,
    calculate_power_flow,
)


class EmissionCalculator:
    def __init__(self, data_dir: Path, pg_file: str, station_file: str):
        """Initialize emission calculator with data for a specific period

        Args:
            data_dir: Data directory path
            pg_file: Power generation data file for a specific period
            station_file: Station information file
        """
        self.data_dir = data_dir
        self.pg_file = pg_file
        self.station_file = station_file
        self._init_data()

    def _init_data(self):
        """Initialize required data"""
        self.pg_data = get_hourly_pg_data(
            data_dir=self.data_dir,
            pg_file=self.pg_file,
            station_file=self.station_file,
        )

        # Specify CSV files and columns
        csv_files = {
            "pg.csv": ["能源別", "電廠名稱", "淨發電量(度)"],
            "AirpollutantEmission.csv": [
                "硫氧化物排放量(kg)",
                "氮氧化物排放量(kg)",
                "粒狀污染物排放量(kg)",
                "溫室氣體排放量係數(kg/kwh)",
            ],
        }

        self.ap_ef = get_ap_emission_factor(self.data_dir, csv_files)
        self._calculate_emissions()

    def _calculate_emissions(self):
        """Calculate various emission types"""

        emission_types = ["CO2e", "SOx", "NOx", "PM"]

        for emission_type in emission_types:
            setattr(
                self,
                f"{emission_type}_emissions",
                get_emissions_by_region(
                    region_power_generation=self.pg_data,
                    emission_data=self.ap_ef,
                    target_emission=emission_type,
                ),
            )

    def _get_power_generation(
        self, generation: pd.Series, fuel_type: List[str]
    ) -> pd.DataFrame:
        """Calculate power generation excluding specified fuel types

        Args:
            generation: Target power generation data
            fuel_type: List of fuel types to exclude

        Returns:
            Power generation data
        """
        pg_sum_exclude_fuel_type = get_selected_pg_data(
            pg=self.pg_data, exclude_fuel=fuel_type
        )

        return calculate_power_generation_with_target(
            pg_wo_target=pg_sum_exclude_fuel_type, target_gen_data=generation
        )

    def _calculate_basic_intensities(
        self, power_generation: pd.DataFrame, scale: str
    ) -> Dict[str, pd.Series]:
        """Calculate basic emission intensities without considering power flow

        Args:
            power_generation: Power generation data
            scale: Calculation scale ('regional' or 'national')

        Returns:
            Dictionary of emission intensities
        """
        intensities = {}
        emission_types = ["CO2e", "SOx", "NOx", "PM"]

        for emission_type in emission_types:
            intensities[emission_type] = calculate_air_pollution_intensity(
                ap_data=getattr(self, f"{emission_type}_emissions"),
                pg_data=power_generation,
                scale=scale,
            )

        return intensities

    def calculate_emission_intensity(
        self, generation: pd.Series, fuel_type: List[str], scale: str = "regional"
    ) -> Dict[str, pd.Series]:
        """Calculate emission intensity without power flow

        Args:
            generation: Target power generation data
            fuel_type: List of fuel types
            scale: Calculation scale ('regional' or 'national')

        Returns:
            Dictionary containing various emission intensities
        """
        power_generation = self._get_power_generation(generation, fuel_type)
        return self._calculate_basic_intensities(power_generation, scale)

    def estimate_emission_intensity_with_flow(
        self,
        generation: pd.Series,
        fuel_type: List[str],
        flow_file: str,
        scale: str = "regional",
    ) -> Dict[str, pd.Series]:
        """Calculate emission intensity with power flow consideration

        Args:
            generation: Target power generation data
            fuel_type: List of fuel types
            flow_file: Power flow data file
            scale: Calculation scale ('regional' or 'national')

        Returns:
            Dictionary containing various emission intensities with power flow
        """

        flow_data = get_json_file(data_dir=self.data_dir, pg_file=flow_file)

        power_generation = self._get_power_generation(generation, fuel_type)

        # Get the basic intensities
        initial_intensities = self._calculate_basic_intensities(power_generation, scale)

        # Consider the impacts of power flow
        intensities = {}
        emission_types = ["CO2e", "SOx", "NOx", "PM"]

        for emission_type in emission_types:
            intensities[emission_type] = calculate_power_flow(
                pg=power_generation,
                flow=flow_data,
                intensity=initial_intensities[emission_type],
                emission=getattr(self, f"{emission_type}_emissions"),
                scale=scale,
            )

        return intensities
