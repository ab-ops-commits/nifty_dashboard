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

def build_snapshot(data, tickers):
    snapshot = []
    for ticker in tickers:
        try:
            if ticker in data and not data[ticker].empty:
                df = data[ticker].dropna()
            else:
                continue
                
            if len(df) < 2: continue
            
            close = df['Close']
            last_close = close.iloc[-1]
            prev_close = close.iloc[-2]
            
            pct_change = (last_close - prev_close) / prev_close * 100
            
            ret_1w = (last_close / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0
            ret_1m = (last_close / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
            ret_3m = (last_close / close.iloc[-63] - 1) * 100 if len(close) >= 63 else 0
            ret_1y = (last_close / close.iloc[-252] - 1) * 100 if len(close) >= 252 else 0
            
            snapshot.append({
                "ticker": ticker,
                "name": ticker.replace("^", "").replace(".NS", ""),
                "last": round(float(last_close), 2),
                "change": round(float(pct_change), 2),
                "ret_1w": round(float(ret_1w), 2),
                "ret_1m": round(float(ret_1m), 2),
                "ret_3m": round(float(ret_3m), 2),
                "ret_1y": round(float(ret_1y), 2),
                "color": Industries_COLORS.get(ticker, "#9e9e9e")
            })
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
    return snapshot

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()
    
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
        
    all_tickers = []
    for group in STOCK_GROUPS.values():
        all_tickers.extend(group)
    all_tickers = list(set(all_tickers))
    
    print(f"Fetching data for {len(all_tickers)} tickers...")
    data = get_data(all_tickers)
    
    snapshot = build_snapshot(data, all_tickers)
    
    # Save snapshot
    with open(os.path.join(args.out_dir, "snapshot.json"), "w") as f:
        json.dump(snapshot, f)
        
    # Create dummy events and meta to satisfy dashboard
    with open(os.path.join(args.out_dir, "events.json"), "w") as f:
        json.dump([], f)
        
    with open(os.path.join(args.out_dir, "meta.json"), "w") as f:
        json.dump({"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)
        
    print("Data build completed successfully.")

if __name__ == "__main__":
    main()
