import pickle
import requests
import pandas as pd
import numpy as np
from xgboost import XGBClassifier

SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 1000  # ඩවුන්ලෝඩ් කරන පැරණි කැන්ඩල් ගණන

print(f"📥 Binance එකෙන් {SYMBOL} පැරණි දත්ත ඩවුන්ලෝඩ් වෙමින් පවතිනවා...")
url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit={LIMIT}"

try:
    resp = requests.get(url).json()
    df = pd.DataFrame(resp, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    
    # දත්ත ටික float බවට පත් කිරීම
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)

    print("📊 Indicators (RSI / ATR) ගණනය වෙමින් පවතිනවා...")
    # සරල RSI ගණනය කිරීම
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # සරල ATR ගණනය කිරීම
    tr = df['high'] - df['low']
    df['atr'] = tr.rolling(window=14).mean()

    # Empty rows අයින් කිරීම
    df = df.dropna()

    # Features (X) සහ Fake Labels (y) සකස් කිරීම
    # (සැබෑ label එකක් විදිහට rsi < 40 නම් 1 [BUY], rsi > 60 නම් 2 [SELL], නැත්නම් 0 [HOLD] ලෙස AI එකට කියාදීම)
    X = df[['rsi', 'atr', 'close']].values
    y = np.where(df['rsi'] < 40, 1, np.where(df['rsi'] > 60, 2, 0))

    print("🤖 XGBoost ML මොඩලය පුහුණු වෙමින් පවතිනවා...")
    model = XGBClassifier()
    model.fit(X, y)

    # model.pkl ලෙස සේව් කිරීම
    with open("model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("✅ සාර්ථකයි! සැබෑ 'model.pkl' ෆයිල් එක සෑදී අවසන්.")

except Exception as e:
    print(f"❌ Error: දත්ත ලබාගැනීමට නොහැකි වුණා: {e}")