# Grid emission intensity

This repository contains the code for the [E3 Research Group@NTU](https://www.e3group.caece.net) **Hourly Grid emission intensity - Taiwan** implementations. For more details, see the [Article Publication](https://doi.org/10.1016/j.trd.2023.103848).

## Installation

```bash
$ git clone git@github.com:CodeGreen-Labs/emission-intensity-tw.git && cd emission-intensity-tw
```

## Usage

```bash
$ python main.py
```

## description
- The input data for this program is the [electricity generation data of Taiwan Power Company](https://data.gov.tw/dataset/37331), which consists of instantaneous electricity generation data at ten-minute intervals over a three-month period.
- Please check and update the following files: station_file, capacity_data, and power_flow_data, if there are any discrepancies with the current information. (Last updated: 2023/08)
- The default target energy is solar power, change or add new one if needed.
