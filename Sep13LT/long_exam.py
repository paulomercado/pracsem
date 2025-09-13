#!/tools/anaconda/redhat/7/2023.07/bin/python
#!/usr/bin/env python

### alternatively, you can run the .py file using: /tools/anaconda/redhat/7/2023.07/bin/python ./template.py

import sys

sys.path.insert(0, "/q/phitopolis/datathon_research_interns/datathon_scripts")

import numpy as np
import pandas as pd
import argparse
from typing import Tuple, List, Optional


from typing import Dict, Union, Iterable, List, Optional
import os
from pathlib import Path

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
                   help='cwiq_code', type=int)
    p.add_argument('-o', '--output_directory', default=None, required=True,
                   help='output directory path')
    p.add_argument('--debug', action='store_true', help="Set logging level to DEBUG.")

    return p


# Sample execution: ./long_exam.py -f 20160104 -s 10038243 10029434 10033653 10009241 10036975 -o /q/home/ph.rod.barit/ateneo_practitioner/long_exam/
### when debugging you can use pdb
# import pdb; pdb.set_trace()
# n - next
# c - continue
# df - you can print the df as you go along
def adjust(df):
    sf= df['splits'].replace(0,1).to_numpy()
    sf_c=np.cumprod(sf)
    df['adj']=sf/sf_c[-1]
    df['adj_vol']=df['volume']/df['adj']
    df['adj_price']=df['closing_price']*df['adj']
    df['adj_div']=df['dividends']*df['adj']
    df['log_ret']=np.log((df['adj_price']+df['adj_div'])/df['adj_price'].shift(1))
    return df
def turnoverspike(df):
    df['Volume_MA10']=df['adj_vol'].rolling(window=10).mean().shift(1)
    df['turnover_spike10']=df['adj_vol']/df['Volume_MA10']
    df = transforms.rolling_zscore(df,cols=['turnover_spike10'],window=20)
    return df
def amihud(df):
    df['abslogret']=df['log_ret'].abs()
    df['DDTV']=df['volume']*(df['closing_price']+df['dividends'])
    df['ratio']=(df['abslogret']/df['DDTV']).rolling(window=252).sum()
    df['amihud_illiquidity252']=(df['ratio']/252)*1000000000
    
    return df
def get_diff(df: pd.DataFrame, cols: List[str], window, suffix=None,inplace=False) -> pd.DataFrame:
    if not inplace:
        df = df.copy()
    if suffix is None:
        suffix = f'_DF{window}'
    
    diffed_cols = [f'{c}{suffix}' for c in cols]
    df[diffed_cols] = df[cols]-df[cols].shift(window)
    
    return df
def beta(df):
    rolling_cov = df['log_ret'].rolling(window=252).cov(df['marketpremium'])
    rolling_var = df['marketpremium'].rolling(window=252).var()
    df['beta']=rolling_cov/rolling_var
    return df
if __name__ == '__main__':
    parser = create_parser()
    kwargs = parser.parse_args()

    logger = setup_logging(kwargs.debug)
    output_directory = kwargs.output_directory
    dte = kwargs.file_date
    sids = kwargs.sid

    PRICES_PATH = pyalpha.PRICES_PATH
    MACROECONOMIC_PATH = pyalpha.MACROECONOMIC_PATH

    print(dte, type(dte))
    print(sids, type(sids))
    print(output_directory, type(output_directory))
    d=utils.Dates()
    dates = d.date_range(d.trading_day_offset(dte,-252*2),d.trading_day_offset(dte,5))
    dte = pd.Timestamp(dte)
    data = utils.read_data(PRICES_PATH,dates,columns=['date','cwiq_code','closing_price','splits','dividends','volume'])
    macro = utils.read_data(MACROECONOMIC_PATH,dates,columns=['date','SPX','T10YR'])
    data['date'] = pd.to_datetime(data['date'])
    output = []
    
    for s in sids:
        sint = int(s)
        df=data[data['cwiq_code']==sint].copy()
        df_macro = macro.copy()
        df_macro['SPX_log_ret'] = np.log(df_macro['SPX']/df_macro['SPX'].shift(1))
        df =df.merge(df_macro[['date', 'SPX_log_ret','T10YR']], on='date', how='left')
        df = adjust(df)
        df = turnoverspike(df)
        df = amihud(df)

        df['T10YR']=df['T10YR'].ffill()
        df['rf']= ((1+df['T10YR']/100)**(1/252))-1
        df['marketpremium']=df['SPX_log_ret']-df['rf']
    
        df= beta(df)
        df['expected']=df['rf']+df['beta']*df['marketpremium']
        df['resid']=df['log_ret']-df['expected']
        df['vol_resid']=df['resid'].rolling(window=20).std()
        df = get_diff(df,cols=['vol_resid'],window=20)
    
        df = df.rename(columns={'turnover_spike10_RZS':'turnover_spike10_RollingZS20'})
    
        final = df[['date','cwiq_code','turnover_spike10','turnover_spike10_RollingZS20','amihud_illiquidity252','beta','vol_resid','vol_resid_DF20']]
    
        final = final[final['date'] == dte]
        output.append(final)

    result = pd.concat(output,ignore_index=True)
    result = transforms.zscore_bydate(result,cols=['amihud_illiquidity252','vol_resid_DF20'])[result.date==dte]

    # sids = [10038243, 10029434, 10033653, 10009241, 10036975]
    # date = "20160104"
    # output_directory = "/q/home/ph.rod.barit/ateneo_practitioner/long_exam/"

    ### dates

    ### read prices file

    ### compute for the turnover spike

    ### compute for the RollingZS20 of turnover spike

    ### compute for logret

    ### compute for amihud ratio
    
    ### compute for ZSbydate of amihud ratio

    ### read macro file

    ### sort values by date and forward fill the 10 year

    ### compute spx log ret

    ### compute daily return of T10YR - assume 252 days when annualizing

    ### compute rm-rf

    ### merge the two dataframes

    ### compute for the beta

    ### compute for the residual return

    ### compute for the volatility of the residual returns

    ### compute for the DF20 of residual volatility

    ### compute for the ZSbydate of DF20 of residual volatility 
    
    ### filter to desired columns

    Path(f"{output_directory}/").mkdir(parents=True, exist_ok=True)
    result.to_csv(f"{output_directory}/{dte.strftime('%Y%m%d')}.lt.csv",index = False, header = True )  
    logger.info("Writing files...")
    logger.info("Done.")
    