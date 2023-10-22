import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

fuel_type_mapping = {
    "太陽能": "solar power",
    "陸域風電": "onshore wind power",
    "離岸風電": "offshore wind power"
}

regions_mapping = {
    "南部": "South",
    "北部": "North",
    "中部": "Center",
    "東部": "East",
    "離島": "Island"
}

def create_figure_CF(
    result_dir: str,
    fuel_type: str, 
    target: str
    ):

    fuel_type_name = fuel_type_mapping.get(fuel_type, "Unknown")
    
    fig, axes = plt.subplots(1, 5, figsize=(20, 6), sharex=True, sharey=True)

    for i, region in enumerate(["北部", "中部", "南部", "東部", "離島"]):
        region_name = regions_mapping.get(region, "Unknown")
        ax = axes[i]
        for data_period in ["1~3", "4~6", "7~9", "10~12"]:
            df = pd.read_csv(f'{result_dir}\\{target}_{fuel_type}_{data_period}.csv', encoding="utf-8")
            region_data = []
            for hr in range(24):
                region_data.append(df[region][df.index % 24 == hr].mean())
            ax.plot(range(24), region_data, label=data_period, linewidth=2)  
            ax.set_xlabel("Time of day (hr)", fontsize=20)  
            ax.set_ylabel(f'{target}', fontsize=20)  
            ax.set_title(f'{region_name}', fontsize=20) 
            ax.tick_params(axis="x", labelsize=14)
            ax.tick_params(axis="y", labelsize=14)
            ax.grid(True, linestyle = "--",color = 'gray' ,linewidth = '0.5',axis='both', alpha=0.5)

    plt.tight_layout()
    plt.subplots_adjust(top=0.9, hspace=0.4, wspace=0.4)
    fig.suptitle(f'{fuel_type_name} : {target}', fontsize=16)
    handles, labels = ax.get_legend_handles_labels()
    #legend = fig.legend(handles, labels, loc="lower center", fontsize=20, ncol=4, bbox_to_anchor=(0.5, 0))
    Path(f'{result_dir}\\figure').mkdir(parents=True, exist_ok=True)
    plt.savefig(f'{result_dir}\\figure\\{fuel_type}_{target}.png', bbox_inches='tight')

    return

def create_figure_EI_total(
    result_dir: str, 
    targets: list,
    limits: list,
    ):

    fig, axes = plt.subplots(4, 4, figsize=(20, 16), sharex=True, sharey='row') 
    for i, (target, limit) in enumerate(zip(targets, limits)):
        for j, region in enumerate(["北部", "中部", "南部", "東部"]):
            region_name = regions_mapping.get(region, "Unknown")
            ax = axes[i, j]
            if j == 0:
                ax.set_ylabel(f'{target} (g/kWh)', fontsize=20)  
            for data_period in ["1~3", "4~6", "7~9", "10~12"]:
                df = pd.read_csv(f'{result_dir}\\{target}_{data_period}.csv', encoding="utf-8")
                region_data = []
                for hr in range(24):
                    region_data.append(df[region][df.index % 24 == hr].mean())
                ax.plot(range(24), region_data, label=data_period, linewidth=2) 
                if i == 3:
                    ax.set_xlabel("Time of day (hr)", fontsize=20)  
                if i == 0:
                    ax.set_title(region_name, fontsize=20) 
                ax.tick_params(axis="x", labelsize=14)
                ax.tick_params(axis="y", labelsize=14)
                ax.set_ylim(limit[0], limit[1])
                ax.grid(True, linestyle = "--",color = 'gray' ,linewidth = '0.5',axis='both', alpha=0.5)

    plt.tight_layout()
    plt.subplots_adjust(top=0.9, hspace=0.4, wspace=0.4)
    handles, labels = ax.get_legend_handles_labels()
    #legend = fig.legend(handles, labels, loc="lower center", fontsize=20, ncol=4, bbox_to_anchor=(0.5, 0))
    Path(f'{result_dir}\\figure').mkdir(parents=True, exist_ok=True)
    plt.savefig(f'{result_dir}\\figure\\total_EI.png', bbox_inches='tight')

    return

