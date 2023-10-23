# Grid emission intensity

This repository contains the code for the [E3 Research Group@NTU](https://www.e3group.caece.net) **Hourly Grid emission intensity - Taiwan** implementations. For more details, please read the [Article Publication](https://doi.org/10.1016/j.trd.2023.103848).

## Installation

```bash
$ git clone git@github.com:wctseng99/emission-intensity-tw.git && cd emission-intensity-tw
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
  

## Results
2021 (capacity target: solar 7.2 GW, onshore wind 0.74 GW, offshore wind 0.24 GW)

2050 (capacity target: solar 40-80 GW, onshore wind 1.2 GW, offshore wind 40-55 GW)



 - National Capacity Factor:

|       | solar  | wind   |
|-------|--------|--------|
| 1~3   | 0.1384 | 0.4345 |
| 4~6   | 0.1642 | 0.2089 |
| 7~9   | 0.1984 | 0.1204 |
| 10~12 | 0.1418 | 0.4332 |


 - Region Capacity percentage: 

| Region   | Solar         | Wind          |
| -------- | ------------- | ------------- |
| 南部     | 58.67%        | 1.66%         |
| 北部     | 0.99%         | 21.36%        |
| 中部     | 39.99%        | 71.73%        |
| 東部     | 0%            | 0%            |
| 離島     | 0.35%         | 5.24%         |


 - Annual power generation (GWh): 

|        | NONTH   | Solar        | Onshore Wind          | Offshore Wind          |
|--------|---------|--------------|-----------------------|------------------------|
|2021    | 1~3     | 1.860        | 0.069                 | 0.023                  |
|        | 4~6     | 1.903        | 0.033                 | 0.010                  |
|        | 7~9     | 3.153        | 0.192                 | 0.062                  |
|        | 10~12   | 2.255        | 0.070                 | 0.023                  |
|2050_min| 1~3     | 10.332       | 1.128                 | 3.761                  |
|        | 4~6     | 10.574       | 0.544                 | 5.172                  |
|        | 7~9     | 17.520       | 0.312                 | 1.815                  |
|        | 10~12   | 12.526       | 1.139                 | 10.399                 |
|2050_max| 1~3     | 20.665       | 1.128                 | 3.800                  |
|        | 4~6     | 21.147       | 0.544                 | 2.495                  |
|        | 7~9     | 35.039       | 0.312                 | 1.430                  |
|        | 10~12   | 25.052       | 1.139                 | 5.224                  |


 - Emission Intensity (National)

|           | CO2e (g/kWh) | SOx (g/kWh) | NOx (g/kWh) | PM (g/kWh) |
|-----------|-------------|------------|------------|------------|
| 2021      | 453.26      | 0.069534   | 0.12055176 | 0.00402305 |
| 2050min   | 313.06      | 0.046971   | 0.08207807 | 0.00272495 |
| 2050max   | 279.83      | 0.041918   | 0.07321427 | 0.00243117 |
| DECREASE  | 30.93%~38.26% | 32.45%~39.72% | 31.91%~39.27% | 32.27%~39.57% |


## Contact information
**Author:** Wei-Chun (Jim) Tseng  
**Email:** wctseng99@gmail.com  
Contact me if you have any questions