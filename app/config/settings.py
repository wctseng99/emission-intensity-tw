from absl import flags
from pathlib import Path

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Parameter definition
flags.DEFINE_string("data_dir", str(PROJECT_ROOT / "data/2024"), "Directory for data.")
flags.DEFINE_string(
    "result_dir", str(PROJECT_ROOT / "results/2024"), "Directory for result."
)
flags.DEFINE_string(
    "station_file", "powerplants_info.csv", "File for power plant information."
)
flags.DEFINE_string(
    "capacity_data", "capacity.csv", "File for target energy capacity data."
)
flags.DEFINE_list(
    "raw_pg_data",
    [
        "各機組過去發電量20240501-20240731.json",
        "各機組過去發電量20240801-20241031.json",
    ],
    "File for power generation data.",
)
flags.DEFINE_list(
    "power_flow_data",
    [
        "pg_flow_5_7.json",
        "pg_flow_8_10.json",
    ],
    "File for power flow data.",
)
flags.DEFINE_list(
    "datetime_range",
    [
        "2024-05-01 00:00:00|2024-07-31 23:00:00",
        "2024-08-01 00:00:00|2024-10-31 23:00:00",
    ],
    "Datetime range in format 'start|end'",
)

flags.DEFINE_list(
    "data_period_list",
    [
        # "1~3", "4~6", "7~9", "10~12"
        "5~7",
        "8~10",
    ],
    "Data period for power flow data and raw power generation data",
)
flags.DEFINE_list(
    "fuel_type", ["太陽能", "離岸風電", "陸域風電"], "Names for target fuels"
)
flags.DEFINE_list(
    "capacity_target",
    [
        # "0",
        # "0",
        # "0",
        ## 2021 (GW) ##
        # "9.72",
        # "0.745",
        # "0.836"
        ## 2024 (GW) ##
        "13.2",
        "2.348",
        "0.915",
        ## 2050 GOAL? (GW) ##
    ],
    "Target capacity for each fuel type (GW)",
)
flags.DEFINE_list(
    "figure_limits",
    [[00, 700], [0.0, 0.13], [0.0, 0.20], [0.00, 0.0065]],
    "Fixed y-axis upper and lower bounds for emission intensity figures",
)

FLAGS = flags.FLAGS
