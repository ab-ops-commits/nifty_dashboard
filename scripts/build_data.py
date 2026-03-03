\"\"\"
Build dashboard data for Nifty Indices (Broad + Sectoral) - GitHub Pages deployment.
Outputs: data/snapshot.json, data/events.json, data/meta.json, data/charts/*.png
\"\"\"
import argparse
import json
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# Configuration for Nifty Indices
STOCK_GROUPS = {
    \"Broad Indices\": [\"^NSEI\", \"^NSEBANK\", \"NIFTYNXT50.NS\", \"^CNX100\", \"^CNX200\", \"^CNX500\", \"^NSMIDCP100\", \"^NSEMDCP50\"],
    \"Sectoral Indices\": [\"^CNXAUTO\", \"^CNXFIN\", \"^CNXFMCG\", \"^CNXIT\", \"^CNXMETAL\", \"^CNXPHARMA\", \"^CNXREALTY\", \"^CNXENERGY\", \"^CNXINFRA\", \"^CNXMEDIA\", \"^CNXPSUBANK\", \"^CNXSERVICE\"]
}

def get_data(tickers):
    # Fetch 1 year of data
    data = yf.download(tickers, period=\"1y\", interval=\"1d\", group_by='ticker')
    return data

def build_snapshot(data, tickers_groups):
    result = {\"groups\": {}}
    
    # Reference for Relative Strength (Nifty 50)
    nifty_ref = None
    if '^NSEI' in data and not data['^NSEI'].empty:
        nifty_ref = data['^NSEI']['Close'].dropna()
    
    for group_name, tickers in tickers_groups.items():
        group_data = []
        for ticker in tickers:
            try:
                if ticker in data and not data[ticker].empty:
                    df = data[ticker].dropna()
                else:
                    continue
                
                if len(df) < 30: continue
                
                close = df['Close']
                high = df['High']
                low = df['Low']
                
                last_close = close.iloc[-1]
                prev_close = close.iloc[-2]
                
                daily_pct = (last_close - prev_close) / prev_close * 100
                ret_5d = (last_close / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
                ret_20d = (last_close / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
                
                # ATR 14
                tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
                atr = tr.rolling(window=14).mean().iloc[-1]
                atr_pct = (atr / last_close) * 100
                
                # Relative Strength (RS) values for sparkline
                rs_spark = []
                if nifty_ref is not None:
                    # Align dates
                    common_idx = df.index.intersection(nifty_ref.index)
                    if len(common_idx) > 0:
                        rs = (df.loc[common_idx, 'Close'] / nifty_ref.loc[common_idx])
                        rs_spark = rs.iloc[-20:].tolist() # Last 20 days
                
                # Grade based on 20D return
                grade = 'A' if ret_20d > 2 else ('B' if ret_20d > -2 else 'C')
                
                ticker_clean = ticker.replace(\"^\", \"\").replace(\".NS\", \"\")
                group_data.append({
                    \"ticker\": ticker_clean,
                    \"abc\": grade,
                    \"daily\": round(float(daily_pct), 2),
                    \"5d\": round(float(ret_5d), 2),
                    \"20d\": round(float(ret_20d), 2),
                    \"atr_pct\": round(float(atr_pct), 2),
                    \"rs_history\": [round(float(x), 4) for x in rs_spark]
                })
            except Exception as e:
                print(f\"Error processing {ticker}: {e}\")
        
        # Sort by daily performance
        group_data.sort(key=lambda x: x['daily'], reverse=True)
        result[\"groups\"][group_name] = group_data
        
    return result

def save_charts(data, tickers, out_dir):
    charts_dir = os.path.join(out_dir, \"charts\")
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        
    for ticker in tickers:
        try:
            if ticker in data and not data[ticker].empty:
                df = data[ticker].dropna()
                ticker_clean = ticker.replace(\"^\", \"\").replace(\".NS\", \"\")
                
                plt.figure(figsize=(10, 5))
                plt.plot(df.index[-60:], df['Close'][-60:], color='#2196f3', linewidth=2)
                plt.title(f\"{ticker_clean} - Last 60 Trading Days\", fontsize=14)
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.xlabel(\"Date\")
                plt.ylabel(\"Price\")
                plt.tight_layout()
                plt.savefig(os.path.join(charts_dir, f\"{ticker_clean}.png\"))
                plt.close()
        except Exception as e:
            print(f\"Error generating chart for {ticker}: {e}\")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(\"--out-dir\", default=\"data\")
    args = parser.parse_args()
    
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
    
    all_tickers = []
    for tickers in STOCK_GROUPS.values():
        all_tickers.extend(tickers)
    all_tickers = list(set(all_tickers))
    
    print(f\"Fetching data for {len(all_tickers)} tickers...\")
    data = get_data(all_tickers)
    
    print(\"Building snapshot...\")
    snapshot = build_snapshot(data, STOCK_GROUPS)
    
    with open(os.path.join(args.out_dir, \"snapshot.json\"), \"w\") as f:
        json.dump(snapshot, f, indent=2)
        
    with open(os.path.join(args.out_dir, \"meta.json\"), \"w\") as f:
        json.dump({\"last_updated\": datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}, f, indent=2)
        
    with open(os.path.join(args.out_dir, \"events.json\"), \"w\") as f:
        json.dump([], f) # Empty events list
        
    print(\"Generating charts...\")
    save_charts(data, all_tickers, args.out_dir)
    
    print(\"Data build completed successfully.\")

if __name__ == \"__main__\":
    main()
