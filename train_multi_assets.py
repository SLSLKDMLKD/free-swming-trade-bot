import pickle
import yfinance as yf
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
import os

# ══════════════════════════════════════════
# ASSETS CONFIGURATION (Yahoo Finance Symbols)
# ══════════════════════════════════════════
ASSETS = {
    "BTCUSDT": "BTC-USD",
    "GOLD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "APPLE": "AAPL"
}

TIMEFRAME = "1h"      # H1 Timeframe
PERIOD = "730d"       # දවස් 730ක ඉතිහාස දත්ත

print("🚀 Multi-Asset Training Engine ආරම්භ වුණා...\n")

for name, ticker in ASSETS.items():
    print(f"📥 {name} ({ticker}) සඳහා Yahoo Finance වෙතින් දත්ත ඩවුන්ලෝඩ් වෙමින් පවතිනවා...")
    
    # Yahoo Finance එකෙන් දත්ත ලබාගැනීම
    data = yf.download(tickers=ticker, period=PERIOD, interval=TIMEFRAME)
    
    if data.empty or len(data) < 50:
        print(f"❌ {name} සඳහා ප්‍රමාණවත් දත්ත නැත. Skipping...")
        continue
        
    df = data.copy()
    
    # --- STRONGEST TUPLE STRING BUG FIX ---
    # කොලම් නම ඇතුළේ තියෙන වචන අනුව අලුත් සරල කොලම් වගුවක් සෑදීම
    clean_df = pd.DataFrame(index=df.index)
    
    for col in df.columns:
        col_str = str(col).lower()
        if 'open' in col_str:
            clean_df['open'] = df[col]
        elif 'high' in col_str:
            clean_df['high'] = df[col]
        elif 'low' in col_str:
            clean_df['low'] = df[col]
        elif 'close' in col_str:  # 'adj close' හෝ 'close' දෙකෙන් මොකක් ආවත් මේකට අහුවේ
            clean_df['close'] = df[col]
        elif 'volume' in col_str:
            clean_df['volume'] = df[col]
            
    # අත්‍යවශ්‍ය කෝලම් ටික තියෙනවද බලන්න
    required = ['open', 'high', 'low', 'close']
    if not all(x in clean_df.columns for x in required):
        print(f"❌ {name} හි අවශ්‍ය columns සොයාගත නොහැකි විය. Skipping...")
        continue
        
    df = clean_df
    # --------------------------------------

    print(f"📊 {name} සඳහා RSI සහ ATR ගණනය වෙමින් පවතිනවා...")
    
    # RSI(14) ගණනය කිරීම
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR(14) ගණනය කිරීම
    tr = df['high'] - df['low']
    df['atr'] = tr.rolling(window=14).mean()
    
    # හිස් පේළි අයින් කිරීම
    df = df.dropna()
    
    if len(df) < 10:
        print(f"❌ {name} පිරිසිදු කිරීමෙන් පසු දත්ත මදි. Skipping...")
        continue
        
    # Features (X) සහ Labels (y) සකස් කිරීම
    X = df[['rsi', 'atr', 'close']].values
    
    # සරල උපායමාර්ග නීතියක් (RSI < 40 නම් BUY, RSI > 60 නම් SELL, නැත්නම් HOLD)
    y = np.where(df['rsi'] < 40, 1, np.where(df['rsi'] > 60, 2, 0))
    
    print(f"🤖 {name} සඳහා වෙනම XGBoost මොඩලයක් පුහුණු වෙනවා...")
    model = XGBClassifier(n_estimators=50, max_depth=3, random_state=42)
    model.fit(X, y)
    
    # එක් එක් ඇසට් එකට වෙන වෙනම පිකල් ෆයිල් සෑදීම
    model_filename = f"model_{name}.pkl"
    with open(model_filename, "wb") as f:
        pickle.dump(model, f)
        
    print(f"✅ සාර්ථකයි! {model_filename} සෑදී අවසන්.\n-----------------------------------")

print("🎯 සියලුම ඇසට් සඳහා AI මොඩල් සාදා නිමයි!")