from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path

from app.data import (
    get_json_file,
    get_station_info,
    get_capacity_info,
    get_hourly_pg_data,
)

from app.module import (
    calculate_capacity_factor,
    calculate_capacity_percentage,
    calculate_pg_with_cf,
)


class PowerGenerator:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def estimate_target_power(
        self,
        pg_file: str,
        station_file: str,
        capacity_file: str,
        fuel_type: str,
        capacity_target: float,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Estimate target power generation

        Args:
            pg_file: Power generation data file
            station_file: Power plant information file
            capacity_file: Capacity information file
            fuel_type: Type of fuel
            capacity_target: Target capacity

        Returns:
            Tuple containing:
            - Estimated power generation
            - Regional capacity factors
            - National capacity factor
            - Capacity percentage by region
        """
        hourly_pg_data = get_hourly_pg_data(
            data_dir=self.data_dir,
            pg_file=pg_file,
            station_file=station_file,
        )

        station_info = get_station_info(
            data_dir=self.data_dir, station_file=station_file
        )

        capacity_info = get_capacity_info(
            data_dir=self.data_dir, capacity_file=capacity_file, fuel_type=fuel_type
        )

        # Calculate regional capacity factors
        region_capacity_factor = calculate_capacity_factor(
            hourly_pg=hourly_pg_data,
            capacity_data=capacity_info,
            fuel_type=fuel_type,
            scale="regional",
        )

        national_capacity_factor = calculate_capacity_factor(
            hourly_pg=hourly_pg_data,
            capacity_data=capacity_info,
            fuel_type=fuel_type,
            scale="national",
        )

        # Calculate capacity percentage by region
        capacity_percentage = calculate_capacity_percentage(
            capacity_data=capacity_info, station_data=station_info, fuel_type=fuel_type
        )

        # Estimate power generation by region
        pg_estimation = calculate_pg_with_cf(
            capacity_factor=region_capacity_factor,
            capacity_target=capacity_target,
            unit="GW",
            capacity_percentage=capacity_percentage,
        )

        return (
            pg_estimation,
            region_capacity_factor,
            national_capacity_factor,
            capacity_percentage,
        )
