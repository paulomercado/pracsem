#!/tools/anaconda/redhat/7/2023.07/bin/python
#!/usr/bin/env python

import sys
sys.path.insert(0, "/q/phitopolis/datathon_research_interns/datathon_scripts")

import numpy as np
import pandas as pd
import argparse

import os
from typing import Tuple, List, Optional
import sys

from typing import Dict, Union, Iterable, List, Optional
Datelike = Union[pd.Timestamp, str, int]

from pathlib import Path
sys.path.append(os.getcwd())

import pyalpha
from pyalpha import pipeline_tools as pipetools
from pyalpha import transforms
from pyalpha import utils
from typing import Union, Dict
from datetime import datetime

def create_parser():
    p = argparse.ArgumentParser(description=f'Script to generate the daily logret files')
    p.add_argument('-f','--file_date', default=None, required=True,
                   help='Initial date of file to process in YYYYMMDD format.',
                  #type = str,
                  )
    p.add_argument( '-s','--sid', default=None, required=True, nargs='+',
                   help='cwiq_code')
    p.add_argument( '-o','--output_directory', default=None, required=True,
                   help='output directory path')
    p.add_argument('--debug', action='store_true', help="Set logging level to DEBUG.")

    return p

def adjprice(df):
    sf= df['splits'].replace(0,1).to_numpy()
    sf_c=np.cumprod(sf[::-1])[::-1]
    df['adj']=sf/sf_c
    df['adj_price']=df['closing_price']*df['adj']
    df['adj_div']=df['dividends']*df['adj']
    df['log_ret']=np.log(df['adj_price']/df['adj_price'].shift(1))
    return df

def rev_price(df):
    df = adjprice(df)
    df['new_close'] = df['adj_price']/np.exp(df['log_ret'])
    df['new_close'] = df['new_close'].shift(-1)
    df.loc[df.index[-1], 'new_close'] = df['adj_price'].iloc[-1]
    df['MA10']=df['new_close'].rolling(window=10).mean()
    return df

def get_diff(df: pd.DataFrame, cols: List[str], window, suffix=None,inplace=False) -> pd.DataFrame:
    if not inplace:
        df = df.copy()
    if suffix is None:
        suffix = f'_DF{window}'
    
    diffed_cols = [f'{c}{suffix}' for c in cols]
    df[diffed_cols] = df[cols]-df[cols].shift(window)
    
    return df

def rsi(df):
    df = get_diff(df,cols=['adj_price'],window=1)
    df['gain'] = np.where(df['adj_price_DF1']>0,abs(df['adj_price_DF1']),0)
    df['loss']= np.where(df['adj_price_DF1']<0,abs(df['adj_price_DF1']),0)
    df['RS'] = df['gain'].rolling(window=14).mean()/df['loss'].rolling(window=14).mean()
    df['RSI_14']=100-(100/(1+df['RS']))
    return df
# Sample execution: ./rsi.py -f 20160104 -s 10038243 10029434 10033653 10009241 10036975 -o /q/home/ph.paulo.mercado

if __name__ == '__main__' :
    parser = create_parser()
    kwargs = parser.parse_args()

    output_directory = kwargs.output_directory
    dte    =  kwargs.file_date
    sids = [int(sid) for sid in kwargs.sid]

    PRICES_PATH         = pyalpha.PRICES_PATH

    dates_obj = utils.Dates()
    start_date = dates_obj.trading_day_offset(dte, -15)
    end_date = dates_obj.trading_day_offset(dte, 0)
    dates = dates_obj.date_range(start_date,end_date)
    dte = pd.Timestamp(dte)

    df_temp = utils.read_data(PRICES_PATH, dates)
    df_temp = df_temp[['date','cwiq_code','log_return','closing_price','splits','dividends']].copy()
    df_temp = df_temp.sort_values(['date']).reset_index(drop=True)
    

    ### Create an empty list
    output=[]
    
    for s in sids:
        check= df_temp[df_temp['cwiq_code']==s].copy()
        check = rev_price(check)
        check = rsi(check)
        final = check[['date','cwiq_code','MA10','RSI_14']]
        final = final[final['date'] == dte]
        output.append(final)

    result = pd.concat(output,ignore_index=True)   

    Path(f"{output_directory}/{dte.strftime('%Y')}").mkdir(parents=True, exist_ok=True) ### creates the directory
    result.to_csv(f"{output_directory}/{dte.strftime('%Y')}/{dte.strftime('%Y%m%d')}.rsi.csv",
    index = False,
    header = True,
    )

    print("Writing files...")
    print("Done.")