"""
Build dashboard data for Nifty Indices (Broad + Sectoral) - GitHub Pages deployment.
Run from repo root: python scripts/build_data.py [--out-dir data]
Outputs: data/snapshot.json, data/events.json, data/meta.json, data/charts/*.png
"""
from __future__ import print_function
import argparse
import json
import os
import re
import time
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.stats import rankdata

# Configuration for Nifty Indices
STOCK_GROUPS = {
    "Broad Indices": ["^NSEI", "^NSEBANK", "NIFTYNXT50.NS", "^CNX100", "^CNX200", "^CNX500", "^NSMIDCP100", "^NSMIDCP150", "^CNXSC", "^NSEMDCP50", "^CNXSC250"],
    "Sectoral Indices": ["^CNXAUTO", "^NSEBANK", "^CNXFIN", "^CNXFMCG", "^CNXIT", "^CNXMETAL", "^CNXPHARMA", "^CNXREALTY", "^CNXENERGY", "^CNXINFRA", "^CNXMEDIA", "^CNXPSUBANK", "^CNXPVTBANK", "^CNXCONSDUR", "^CNXHEALTH"]
}

Industries_COLORS = {
    "^CNXAUTO": "#4caf50", "^NSEBANK": "#ff5722", "^CNXFIN": "#ff9800", "^CNXFMCG": "#8bc34a", "^CNXIT": "#3f51b5",
    "^CNXMETAL": "#607d8b", "^CNXPHARMA": "#e91e63", "^CNXREALTY": "#673ab7", "^CNXENERGY": "#795548", "^CNXINFRA": "#333333",
    "^CNXMEDIA": "#9c27b0", "^CNXPSUBANK": "#ff5722", "^CNXPVTBANK": "#ff9800", "^CNXCONSDUR": "#00bcd4", "^CNXHEALTH": "#e91e63"
}

def get_data(tickers):
    data = yf.download(tickers, period="2y", interval="1d", group_by='ticker')
    return data

def build_snapshot(data, tickers_groups):
    result = {"groups": {}}
    for group_name, tickers in tickers_groups.items():
        group_data = []
        for ticker in tickers:
            try:
                if ticker in data and not data[ticker].empty:
                    df = data[ticker].dropna()
                else:
                    continue
                    
                if len(df) < 21: continue
                
                close = df['Close']
                last_close = close.iloc[-1]
                prev_close = close.iloc[-2]
                
                daily_pct = (last_close - prev_close) / prev_close * 100
                ret_5d = (last_close / close.iloc[-6] - 1) * 100
                ret_20d = (last_close / close.iloc[-21] - 1) * 100
                
                # Dummy Grade
                grade = 'A' if ret_20d > 5 else ('B' if ret_20d > 0 else 'C')
                
                group_data.append({
                    "ticker": ticker.replace("^", "").replace(".NS", ""),
                    "abc": grade,
                    "daily": round(float(daily_pct), 2),
                    "5d": round(float(ret_5d), 2),
                    "20d": round(float(ret_20d), 2),
                    "atr_pct": 0,
                    "rs_chart": ""
                })
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
        result["groups"][group_name] = group_data
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()
    
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
        
    all_tickers = []
    for tickers in STOCK_GROUPS.values():
        all_tickers.extend(tickers)
    all_tickers = list(set(all_tickers))
    
    print(f"Fetching data for {len(all_tickers)} tickers...")
    data = get_data(all_tickers)
   
    snapshot = build_snapshot(data, STOCK_GROUPS)
    
    with open(os.path.join(args.out_dir, "snapshot.json"), "w") as f:
        json.dump(snapshot, f)
        
    with open(os.path.join(args.out_dir, "events.json"), "w") as f:
        json.dump([], f)
        
    with open(os.path.join(args.out_dir, "meta.json"), "w") as f:
        json.dump({"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)
        
    print("Data build completed successfully.")

if __name__ == "__main__":
    main()
