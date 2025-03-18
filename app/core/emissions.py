from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path

from app.data import (
    get_hourly_pg_data,
    get_ap_emission_factor,
    get_emissions_by_region,
    get_selected_pg_data,
)
from app.module import (
    calculate_power_generation_with_target,
    calculate_air_pollution_intensity,
)


class EmissionCalculator:
    def __init__(self, data_dir: Path, pg_file: str, station_file: str):
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
        self.CO2e_emissions = get_emissions_by_region(
            region_power_generation=self.pg_data,
            emission_data=self.ap_ef,
            target_emission="CO2e",
        )

        self.SOx_emissions = get_emissions_by_region(
            region_power_generation=self.pg_data,
            emission_data=self.ap_ef,
            target_emission="SOx",
        )

        self.NOx_emissions = get_emissions_by_region(
            region_power_generation=self.pg_data,
            emission_data=self.ap_ef,
            target_emission="NOx",
        )

        self.PM_emissions = get_emissions_by_region(
            region_power_generation=self.pg_data,
            emission_data=self.ap_ef,
            target_emission="PM",
        )

    def calculate_emission_intensity(
        self, generation: pd.Series, fuel_type: List[str], scale: str = "regional"
    ) -> Dict[str, pd.Series]:
        """Calculate emission intensity

        Args:
            generation: Target power generation data
            fuel_type: List of fuel types
            scale: Calculation scale ('regional' or 'national')

        Returns:
            Dictionary containing various emission intensities
        """
        pg_sum_exclude_fuel_type = get_selected_pg_data(
            pg=self.pg_data, exclude_fuel=fuel_type
        )

        power_generation = calculate_power_generation_with_target(
            pg_wo_target=pg_sum_exclude_fuel_type, target_gen_data=generation
        )

        intensities = {}

        # Calculate various emission intensities
        intensities["CO2e"] = calculate_air_pollution_intensity(
            ap_data=self.CO2e_emissions, pg_data=power_generation, scale=scale
        )

        intensities["SOx"] = calculate_air_pollution_intensity(
            ap_data=self.SOx_emissions, pg_data=power_generation, scale=scale
        )

        intensities["NOx"] = calculate_air_pollution_intensity(
            ap_data=self.NOx_emissions, pg_data=power_generation, scale=scale
        )

        intensities["PM"] = calculate_air_pollution_intensity(
            ap_data=self.PM_emissions, pg_data=power_generation, scale=scale
        )

        return intensities
