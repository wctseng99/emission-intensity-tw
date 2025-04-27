import pandas as pd
from pathlib import Path
from absl import app, logging

from app.config.settings import FLAGS
from app.core.emissions import EmissionCalculator
from app.core.power import PowerGenerator
from app.module import (
    create_figure_CF,
    create_figure_EI_total,
)


def main(argv):
    # Initialize paths
    data_dir = Path(FLAGS.data_dir)
    result_dir = Path(FLAGS.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    # Initialize power generator
    power_generator = PowerGenerator(data_dir)

    # Process data for each period
    for period_idx, period in enumerate(FLAGS.data_period_list):
        logging.info(f"start working on {period}:\n")
        pg_file = FLAGS.raw_pg_data[period_idx]
        flow_file = FLAGS.power_flow_data[period_idx]

        emission_calculator = EmissionCalculator(
            data_dir=data_dir,
            pg_file=pg_file,
            station_file=FLAGS.station_file,
        )

        pg_estimation_total = pd.DataFrame()

        # Process each fuel type
        for fuel_idx, fuel_type in enumerate(FLAGS.fuel_type):
            capacity_target = float(FLAGS.capacity_target[fuel_idx])

            # Estimate target power generation
            pg_estimation, region_cf, national_cf, capacity_percentage = (
                power_generator.estimate_target_power(
                    pg_file=pg_file,
                    station_file=FLAGS.station_file,
                    capacity_file=FLAGS.capacity_data,
                    fuel_type="陸域風電" if fuel_type == "離岸風電" else fuel_type,
                    capacity_target=capacity_target,
                )
            )

            # Add to total power generation
            pg_estimation_total = (
                pg_estimation
                if pg_estimation_total.empty
                else pg_estimation_total.add(pg_estimation, fill_value=0)
            )

            logging.info(f"Month={period}, Fuel={fuel_type}")
            # need to check: the mean of regional cf and the national cf.
            logging.info(f"The avg of national capacity factor:{national_cf.mean()}.")
            logging.info(
                f"national power generation (kWh): {pg_estimation.sum().sum()}."
            )

            # Todo:
            # for displaying real result of offshore wind power

            # Output the regional capacity factors
            for region in capacity_percentage:
                logging.info(
                    f"{region} capacity percentage: {capacity_percentage[region]}."
                )
            region_cf.to_csv(
                result_dir / f"region_capacity_factor_{fuel_type}_{period}.csv",
                index=False,
                encoding="utf-8-sig",
            )

        # Calculate emission intensity for total power generation
        emission_intensities = (
            emission_calculator.estimate_emission_intensity_with_flow(
                generation=pg_estimation_total,
                fuel_type=FLAGS.fuel_type,
                flow_file=flow_file,
                scale="regional",
            )
        )

        # Log emission intensities and save to CSV files
        logging.info(f"\nEmission intensities for period {period}:")
        for emission_type, intensity in emission_intensities.items():
            logging.info(f"\n{emission_type}:")
            logging.info(f"{intensity.mean()}")
            # Add datetime index
            start_time, end_time = FLAGS.datetime_range[period_idx].split("|")
            datetime_index = pd.date_range(start=start_time, end=end_time, freq="h")
            intensity.index = datetime_index
            # Save each emission type to a separate CSV file
            intensity.to_csv(
                result_dir / f"{emission_type}_EI_{period}.csv",
                encoding="utf-8-sig",
                index=True,
            )
        logging.info("\n---")

    # Create figures
    for fuel_type in FLAGS.fuel_type:
        create_figure_CF(
            result_dir=result_dir,
            data_period_list=FLAGS.data_period_list,
            fuel_type=fuel_type,
            target="region_capacity_factor",
        )

    create_figure_EI_total(
        result_dir=result_dir,
        data_period_list=FLAGS.data_period_list,
        targets=["CO2e_EI", "SOx_EI", "NOx_EI", "PM_EI"],
        limits=FLAGS.figure_limits,
    )


if __name__ == "__main__":
    app.run(main)
