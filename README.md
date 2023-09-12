# Grid emission intensity

This repository contains the code for the [E3 Research Group@NTU](https://www.e3group.caece.net) **Hourly Grid emission intensity - Taiwan** implementations. For more details, please read the [Article Publication](https://doi.org/10.1016/j.trd.2023.103848).

## Installation

```bash
$ git clone git@github.com:wctseng99/emission-intensity-tw.git && cd emission-intensity-tw
```

## requirements

```bash
pip install -r requirements.txt
```

## Usage

```bash
$ python main.py
```

## Description
- The input data for this program is the Open Government Data: [electricity generation of Taiwan Power Company (TPC)](https://data.gov.tw/dataset/37331), which consists of instantaneous electricity generation data at ten-minute intervals over a three-month period.
- Most of the input data and parameters are manipulated or substituted in **main.py**
- Please check and update the following files: station_file, capacity_data, and [power_flow_data](https://data.gov.tw/en/datasets/37326)(The latest version of power flow data: 2021), if there are any discrepancies with the current information. (Last updated: 2023/08)
- The default target energy is solar power; change or add a new one if needed.
- The selected air pollutants emission factors are based on the emissions and net electricity generation from [Annual Report of TPC](https://www.taipower.com.tw/upload/43/43_05/111年電業年報.pdf?230829).
- The Greenhouse gas emissions and GHG emission factors are calculated by the methodology 2.2.1 and Fig. 1. in the article mentioned above.
- The system boundary of emission factor and emission intensity only include the operating phase (combustion emissions/direct emissions).
- The data only contains the TPC system's generating units.
- Please note that the temporal scope of the power generation data should be synchronized with that of the power flow data.
  
## Contact information
**Author:** Wei-Chun (Jim) Tseng  
**Email:** wctseng99@gmail.com  
Contact me if you have any questions