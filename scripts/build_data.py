\"\"\"
Build dashboard data for Nifty Indices (Broad + Sectoral) - GitHub Pages deployment.
Run from repo root: python scripts/build_data.py [--out-dir data]
Outputs: data/snapshot.json, data/events.json, data/meta.json, data/charts/*.png
\"\"\"
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

STOCK_GROUPS = {
    \"Broad Indices\": [\"^NSEI\", \"^NSEBANK\", \"NIFTYNXT50.NS\", \"^CNX100\", \"^CNX200\", \"^CNX500\", \"^NSMIDCP100\", \"^NSMIDCP150\", \"^CNXSC\", \"^NSEMDCP50\", \"^CNXSC250\"],
    \"Sectoral Indices\": [\"^CNXAUTO\", \"^NSEBANK\", \"^CNXFIN\", \"^CNXFMCG\", \"^CNXIT\", \"^CNXMETAL\", \"^CNXPHARMA\", \"^CNXREALTY\", \"^CNXENERGY\", \"^CNXINFRA\", \"^CNXMEDIA\", \"^CNXPSUBANK\", \"^CNXPVTBANK\", \"^CNXCONSDUR\", \"^CNXHEALTH\"]
}
SECTOR_COLORS = {
    \"Broad Market\": \"#9e9e9e\", \"Banking\": \"#ff5722\", \"Financial Services\": \"#ff9800\", \"Information Technology\": \"#3f51b5\",
    \"Pharma & Healthcare\": \"#e91e63\", \"Energy & Oil\": \"#795548\", \"FMCG\": \"#8bc34a\", \"Metal & Mining\": \"#607d8b\",
    \"Auto\": \"#4caf50\", \"Realty\": \"#673ab7\", \"Media\": \"#9c27b0\", \"Infrastructure\": \"#333333\", \"Consumer Durables\": \"#00bcd4\"
}
Industries_COLORS = {
    \"^CNXAUTO\": \"#4caf50\", \"^NSEBANK\": \"#ff5722\", \"^CNXFIN\": \"#ff9800\", \"^CNXFMCG\": \"#8bc34a\", \"^CNXIT\": \"#3f51b5\",
    \"^CNXMETAL\": \"#607d8b\", \"^CNXPHARMA\": \"#e91e63\", \"^CNXREALTY\": \"#673ab7\", \"^CNXENERGY\": \"#795548\", \"^CNXINFRA\": \"#333333\",
    \"^CNXMEDIA\": \"#9c27b0\", \"^CNXPSUBANK\": \"#ff5722\", \"^CNXPVTBANK\": \"#ff9800\", \"^CNXCONSDUR\": \"#00bcd4\", \"^CNXHEALTH\": \"#e91e63\"
}
def get_ticker_to_sector_mapping():
    color_to_sector = {c: s for s, c in SECTOR_COLORS.items()}
    return {t: color_to_sector.get(c, \"Broad Market\") for t, c in Industries_COLORS.items()}
TICKER_TO_SECTOR = get_ticker_to_sector_mapping()
def calculate_atr(hist_data, period=14):
    try:
        hl = hist_data['High'] - hist_data['Low']
        hc = (hist_data['High'] - hist_data['Close'].shift()).abs()
        lc = (hist_data['Low'] - hist_data['Close'].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.ewm(alpha=1/period, adjust=False).mean().iloc[-1]
    except: return None
def calculate_rrs(stock_data, bench_data):
    try:
        merged = pd.merge(stock_data[['High','Low','Close']], bench_data[['High','Low','Close']], left_index=True, right_index=True, suffixes=('_s','_b'), how='inner')
        for p in ['s','b']:
            h,l,c = merged[f'High_{p}'], merged[f'Low_{p}'], merged[f'Close_{p}']
            tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
            merged[f'atr_{p}'] = tr.ewm(alpha=1/14, adjust=False).mean()
        rrs = ((merged['Close_s']-merged['Close_s'].shift(1)) - (merged['Close_b']-merged['Close_b'].shift(1))/merged['atr_b']*merged['atr_s'])/merged['atr_s']
        roll = rrs.rolling(window=50, min_periods=1).mean()
        sma = roll.rolling(window=20, min_periods=1).mean()
        return pd.DataFrame({'rollingRRS': roll, 'RRS_SMA': sma}, index=merged.index)
    except: return None
def calculate_sma(d, p=50): return d['Close'].rolling(window=p).mean().iloc[-1]
def calculate_ema(d, p=10): return d['Close'].ewm(span=p, adjust=False).mean().iloc[-1]
def calculate_abc_rating(d):
    e10, e20, s50 = calculate_ema(d, 10), calculate_ema(d, 20), calculate_sma(d, 50)
    if e10 > e20 > s50: return \"A\"
    if e10 < e20 < s50: return \"C\"
    return \"B\"
def create_rs_chart_png(rrs, t, d):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8, 2))
    fig.patch.set_facecolor('#1a1a1a'); ax.set_facecolor('#1a1a1a')
    rec = rrs.tail(20); roll, sma = rec['rollingRRS'].values, rec['RRS_SMA'].values
    ax.bar(range(len(roll)), roll, color=['#4ade80' if i==roll.argmax() else '#b0b0b0' for i in range(len(roll))], width=0.8)
    ax.plot(range(len(sma)), sma, color='yellow', lw=2); ax.axhline(0, color='#808080', ls='--', lw=1)
    ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
    fig.savefig(os.path.join(d, f\"{re.sub(r'[^a-zA-Z0-9]', '_', t)}.png\"), format='png', dpi=80, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close(fig); return f\"data/charts/{re.sub(r'[^a-zA-Z0-9]', '_', t)}.png\"
def main():
    parser = argparse.ArgumentParser(); parser.add_argument(\"--out-dir\", default=\"data\"); args = parser.parse_args()
    cd = os.path.join(args.out_dir, \"charts\"); os.makedirs(cd, exist_ok=True)
    bench = yf.Ticker(\"^NSEI\").history(period=\"120d\")
    g_data = {}
    for gn, ts in STOCK_GROUPS.items():
        rows = []
        for t in ts:
            s = yf.Ticker(t); h = s.history(period=\"21d\"); d = s.history(period=\"60d\")
            if len(h)<2 or len(d)<50: continue
            atr = calculate_atr(d); cp = h['Close'].iloc[-1]; ap = (atr/cp)*100
            rrs = calculate_rrs(s.history(period=\"120d\"), bench)
            rows.append({\"ticker\":t, \"daily\":round((h['Close'].iloc[-1]/h['Close'].iloc[-2]-1)*100,2), \"intra\":round((h['Close'].iloc[-1]/h['Open'].iloc[-1]-1)*100,2), \"5d\":round((h['Close'].iloc[-1]/h['Close'].iloc[-6]-1)*100,2), \"20d\":round((h['Close'].iloc[-1]/h['Close'].iloc[-21]-1)*100,2), \"atr_pct\":round(ap,1), \"dist_sma50_atr\":round((100*(cp/calculate_sma(d)-1)/ap),2), \"rs\":round(((rankdata(rrs['rollingRRS'].tail(21))[-1]-1)/20)*100,0), \"rs_chart\":create_rs_chart_png(rrs, t, cd), \"long\":[], \"short\":[], \"abc\":calculate_abc_rating(d)})
        g_data[gn] = rows
    snap = {\"built_at\": datetime.utcnow().isoformat()+\"Z\", \"groups\": g_data, \"column_ranges\": {gn: {\"daily\":(min([r['daily'] for r in rs]), max([r['daily'] for r in rs])), \"intra\":(min([r['intra'] for r in rs]), max([r['intra'] for r in rs])), \"5d\":(min([r['5d'] for r in rs]), max([r['5d'] for r in rs])), \"20d\":(min([r['20d'] for r in rs]), max([r['20d'] for r in rs]))} for gn, rs in g_data.items()}}
    meta = {\"SECTOR_COLORS\": SECTOR_COLORS, \"TICKER_TO_SECTOR\": TICKER_TO_SECTOR, \"Industries_COLORS\": Industries_COLORS, \"SECTOR_ORDER\": list(SECTOR_COLORS.keys()), \"default_symbol\": \"^NSEI\"}
    with open(os.path.join(args.out_dir, \"snapshot.json\"), \"w\") as f: json.dump(snap, f, indent=2)
    with open(os.path.join(args.out_dir, \"meta.json\"), \"w\") as f: json.dump(meta, f, indent=2)
    with open(os.path.join(args.out_dir, \"events.json\"), \"w\") as f: json.dump([], f)
if __name__ == \"__main__\": main()
