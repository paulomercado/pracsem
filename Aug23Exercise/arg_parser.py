#!/usr/bin/env python3
#!/usr/bin/python3
"""
    to run the file you might have to activate conda: conda activate base
    you might also need to add execute permission to the file: chmod +x ./arg_parser.py
    
    sample command: ./sample.py -f 20150104 -t ADBE -o /Users/rodbarit/Documents/Ateneo_seminar/2025/20250823/
    choose only from these stocks: [ADBE, COST, CSCO, MAR, MCD]

"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import re
from typing import Dict, Union, Iterable, List, Optional
Datelike = Union[pd.Timestamp, str, int]
import argparse
from pathlib import Path


def create_parser():
    """
    sample command: ./sample.py -f 20150104 -t ADBE -o /Users/rodbarit/Documents/Ateneo_seminar/2025/20250823/

    """
    p = argparse.ArgumentParser(description=f'Script to generate the daily prices files')
    p.add_argument('-f','--file_date', default=None, required=True,
                   help='Initial date of file to process in YYYYMMDD format.',
                  #type = str,
                  ) 
    p.add_argument( '-t','--ticker', default=None, required=True,
                   help='ticker name')   
    p.add_argument( '-o','--output_directory', default=None, required=True,
                   help='output directory path')    
    return p


if __name__ == '__main__' :
    parser = create_parser()
    kwargs = parser.parse_args()
    
    
    ticker = kwargs.ticker
    output_directory = kwargs.output_directory
    file_date = kwargs.file_date
    dte = pd.Timestamp(file_date)
    
    print('You entered file date: ', file_date )
    print('You entered ticker: ', ticker )
    print('You entered output directory: ', output_directory )