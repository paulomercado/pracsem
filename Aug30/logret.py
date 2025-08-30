#!/tools/anaconda/redhat/7/2023.07/bin/python

import sys

sys.path.insert(0,"/q/phitopolis/datathon_research_interns/datathon_scripts")  # inserts the scripts to the PATH environment - so we can import the scripts in our notebook

import numpy as np
import pandas as pd
import argparse

import lightgbm as lgb
import matplotlib.pyplot as plt
import statsmodels.api as sm

import os
from typing import Tuple, List, Optional
import sys
import empyrical as em

from typing import Dict, Union, Iterable, List, Optional

Datelike = Union[pd.Timestamp, str, int]  # can be either a pandas timestamp, a string, or an integer

from pathlib import Path

sys.path.append(os.getcwd())

import pyalpha
from pyalpha import pipeline_tools as pipetools
from pyalpha import transforms
from pyalpha import utils
from typing import Union, Dict
from datetime import datetime
import logging


def setup_logging(debug_mode: bool):
    log_level = logging.DEBUG if debug_mode else logging.INFO

    # Configure basic logging to a file
    # The level is now determined by the command-line flag
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='log.log',
        filemode='a'  # 'a' for append, 'w' for overwrite
    )

    # Create a logger instance
    logger = logging.getLogger(__name__)

    # Configure a console handler to also show logs in the terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def create_parser():
    p = argparse.ArgumentParser(description=f'Script to generate the daily logret files')
    p.add_argument('-f', '--file_date', default=None, required=True,
                   help='Initial date of file to process in YYYYMMDD format.',
                   # type = str,
                   )
    p.add_argument('-s', '--sid', default=None, required=True, nargs='+',
                   help='cwiq_code')
    p.add_argument('-o', '--output_directory', default=None, required=True,
                   help='output directory path')
    p.add_argument('--debug', action='store_true', help="Set logging level to DEBUG.")

    return p


# Sample execution: ./logret.py -f 20160104 -s 10038243 10029434 10033653 10009241 10036975 -o /q/home/ph.rod.barit/ateneo_practitioner/logret/

if __name__ == '__main__':
    parser = create_parser()
    kwargs = parser.parse_args()

    logger = setup_logging(kwargs.debug)
    output_directory = kwargs.output_directory
    dte = kwargs.file_date
    dte = pd.to_datetime(dte,format='%Y%m%d')
    PRICES_PATH         = pyalpha.PRICES_PATH
    
    sids = kwargs.sid
    d=utils.Dates()
    dates = d.date_range(d.trading_day_offset(dte,-1),d.trading_day_offset(dte,5))
    data = utils.read_data(PRICES_PATH,dates,columns=['date','cwiq_code','closing_price','splits','dividends'])
    data['date'] = pd.to_datetime(data['date'])
    output = []
    print(data)
    for s in sids:
        sint = int(s)
        df=data[data['cwiq_code']==sint].copy()
        
        sf= df['splits'].replace(0,1).to_numpy()
        sf_c=np.cumprod(sf[::-1])[::-1]
        df['adj']=sf/sf_c
        df['adj_price']=df['closing_price']*df['adj']

        df['log_ret']=np.log((df['adj_price']+df['dividends'])/df['adj_price'].shift(1))
        for k in range(1,6):
            df[f'log_ret_f{k}']=np.log(df['adj_price'].shift(-k)/(df['adj_price'].shift(-k+1)+df['dividends'].shift(-k+1)))
        df['log_ret_sf5']=df.iloc[:,8:13].sum(axis=1)
        
        df_final = df.drop(columns=['closing_price','splits','dividends','adj','adj_price'])
        df_final = df_final[df_final['date'] == dte]
        
        output.append(df_final)
   
    result = pd.concat(output,ignore_index=True)
    
    print(dte)

    print(output_directory)
    print(sids)
    Path(f"{output_directory}/").mkdir(parents=True, exist_ok=True)
    result.to_csv(f"{output_directory}/{dte.strftime('%Y%m%d')}.logret.csv",
                                      index = False,
                                      header = True
                                      )  
    logger.info("Writing files...")
    logger.info("Done.")