"""
Quantum Alpha Swing Pro - Lite Edition (Multi-Asset AI Engine)
Lightweight Python trading system optimized for older CPUs and Free Cloud Hosting.
Features: Asyncio Trading Loop, SQLite Database, Flask Web Dashboard (Daemon Thread).
"""
import asyncio
import aiohttp
import json
import sqlite3
import threading
import logging
import os
import pickle
import pandas as pd
import numpy as np
from flask import Flask, jsonify
import sys

# ==========================================
# CONFIGURATION
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('QuantumAlphaLite')

DB_FILE = 'trading.db'
INITIAL_BALANCE = 10000.0
RISK_PERCENT = 0.02

# Binance එකෙන් ලයිව් දුවන්න පුළුවන් Crypto විතරක් නිසා ප්‍රධාන Crypto යුගල 2ක් ඇතුළත් කර ඇත.
SYMBOLS = ['btcusdt', 'ethusdt']

# ==========================================
# HTML TEMPLATE (FLASK UI)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Quantum Alpha Swing Pro - Lite</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #ffffff; margin: 0; padding: 20px; }
        h1 { color: #bb86fc; text-align: center; }
        .dashboard-container { display: flex; flex-direction: column; gap: 20px; max-width: 1200px; margin: 0 auto; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background-color: #2c2c2c; color: #bb86fc; }
        tr:hover { background-color: #252525; }
        .buy { color: #03dac6; font-weight: bold; }
        .sell { color: #cf6679; font-weight: bold; }
        #balance { font-size: 2em; color: #03dac6; margin: 0; }
    </style>
</head>
<body>
    <h1>Quantum Alpha Swing Pro - Lite (AI Multi-Model)</h1>
    <div class="dashboard-container">
        <div class="card">
            <h2>Account Balance</h2>
            <h3 id="balance">Loading...</h3>
        </div>
        <div class="card">
            <h2>Active Trades</h2>
            <table id="trades-table">
                <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Entry</th><th>Size</th><th>SL</th><th>TP</th><th>Status</th></tr></thead>
                <tbody id="trades-body"></tbody>
            </table>
        </div>
        <div class="card">
            <h2>Recent Signals</h2>
            <table id="signals-table">
                <thead><tr><th>ID</th><th>Time</th><th>Symbol</th><th>Signal</th><th>Price</th></tr></thead>
                <tbody id="signals-body"></tbody>
            </table>
        </div>
    </div>
    <script>
        function formatSide(side) {
            if(side === 'BUY') return '<span class="buy">BUY</span>';
            if(side === 'SELL') return '<span class="sell">SELL</span>';
            return side;
        }
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('balance').innerText = '$' + data.account.balance.toFixed(2);
                    
                    const tradesTbody = document.getElementById('trades-body');
                    tradesTbody.innerHTML = '';
                    data.trades.forEach(trade => {
                        tradesTbody.innerHTML += `<tr>
                            <td>${trade.id}</td><td>${trade.symbol}</td><td>${formatSide(trade.side)}</td>
                            <td>$${trade.entry_price.toFixed(2)}</td><td>${trade.amount.toFixed(4)}</td>
                            <td>$${trade.sl.toFixed(2)}</td><td>$${trade.tp.toFixed(2)}</td><td>${trade.status}</td>
                        </tr>`;
                    });

                    const signalsTbody = document.getElementById('signals-body');
                    signalsTbody.innerHTML = '';
                    data.signals.forEach(sig => {
                        signalsTbody.innerHTML += `<tr>
                            <td>${sig.id}</td><td>${sig.timestamp}</td><td>${sig.symbol}</td>
                            <td>${formatSide(sig.signal)}</td><td>$${sig.price.toFixed(2)}</td>
                        </tr>`;
                    });
                })
                .catch(err => console.error("Error fetching data:", err));
        }
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ==========================================
# FLASK WEB DASHBOARD
# ==========================================
app = Flask(__name__)

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/data')
def api_data():
    try:
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT balance FROM account ORDER BY id DESC LIMIT 1")
        acc = c.fetchone()
        balance = acc['balance'] if acc else INITIAL_BALANCE
        
        c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 15")
        trades = [dict(row) for row in c.fetchall()]
        
        c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 15")
        signals = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return jsonify({
            'account': {'balance': balance},
            'trades': trades,
            'signals': signals
        })
    except sqlite3.OperationalError as e:
        logger.warning(f"Database read locked/unavailable: {e}")
        return jsonify({'account': {'balance': INITIAL_BALANCE}, 'trades': [], 'signals': []})

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask Dashboard on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==========================================
# DATABASE SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS account
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, balance REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, entry_price REAL, 
                  amount REAL, sl REAL, tp REAL, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS signals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, signal TEXT, price REAL, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute("SELECT count(*) FROM account")
    if c.fetchone() == 0:
        c.execute("INSERT INTO account (balance) VALUES (?)", (INITIAL_BALANCE,))
    
    conn.commit()
    conn.close()

# ==========================================
# ASYNC TRADING BOT ENGINE
# ==========================================
class TradingBot:
    def __init__(self):
        # එක් එක් සිම්බල් එකට වෙන වෙනම klines ගබඩා කරගැනීම
        self.klines = {}
        for sym in SYMBOLS:
            self.klines[sym.upper()] = {
                '1h': pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']),
                '4h': pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']),
                '1d': pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            }
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        
    def load_model_for_asset(self, asset_name):
        """ඇසට් එකේ නම අනුව අදාළ .pkl ෆයිල් එක ක්ෂණිකව ලෝඩ් කරගැනීම"""
        model_file = f"model_{asset_name}.pkl"
        if os.path.exists(model_file):
            try:
                with open(model_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load model for {asset_name}: {e}")
                return None
        return None

    def get_balance(self):
        c = self.conn.cursor()
        c.execute("SELECT balance FROM account ORDER BY id DESC LIMIT 1")
        res = c.fetchone()
        return res if res else INITIAL_BALANCE

    def record_signal(self, symbol, signal, price):
        c = self.conn.cursor()
        c.execute("INSERT INTO signals (symbol, signal, price) VALUES (?, ?, ?)", (symbol, signal, price))
        self.conn.commit()

    def record_trade(self, symbol, side, entry_price, amount, sl, tp, status='OPEN'):
        c = self.conn.cursor()
        c.execute("INSERT INTO trades (symbol, side, entry_price, amount, sl, tp, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (symbol, side, entry_price, amount, sl, tp, status))
        self.conn.commit()

    def calc_atr(self, df, period=14):
        if len(df) < period + 1:
            return 0.0
        high, low, close = df['high'], df['low'], df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1/period, adjust=False).mean().iloc[-1]

    def calc_rsi(self, df, period=14):
        if len(df) < period + 1:
            return 50.0
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss
        return (100 - (100 / (1 + rs))).iloc[-1]

    def execute_trade(self, symbol, side, price, atr):
        balance = self.get_balance()
        risk_amount = balance * RISK_PERCENT
        sl_dist = atr * 2.0
        
        if sl_dist == 0:
            sl_dist = price * 0.02
            
        position_size = risk_amount / sl_dist
        
        if side == 'BUY':
            sl = price - sl_dist
            tp = price + (sl_dist * 2.0)
        else:
            sl = price + sl_dist
            tp = price - (sl_dist * 2.0)
            
        self.record_trade(symbol, side, price, position_size, sl, tp)
        logger.info(f"[TRADE EXECUTED] {side} on {symbol} | Entry: {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")

    def get_ml_prediction(self, asset_name, features):
        """ලෝඩ් කරගත් නිවැරදි ඇසට් මොඩලය පාවිච්චි කර සිග්නල් ගැනීම"""
        current_model = self.load_model_for_asset(asset_name)
        
        if current_model is None:
            # මොඩල් එක නැත්නම් ආරක්ෂිත ක්‍රමය (RSI Fallback)
            rsi = features.get('rsi_1h', 50)
            if rsi < 30: return 'BUY'
            if rsi > 70: return 'SELL'
            return 'HOLD'
            
        try:
            df_features = pd.DataFrame([features])
            pred = current_model.predict(df_features)
            if pred == 1: return 'BUY'
            elif pred == -1 or pred == 2: return 'SELL'
            return 'HOLD'
        except Exception as e:
            logger.error(f"ML prediction error for {asset_name}: {e}")
            return 'HOLD'

    def process_closed_candle(self, symbol, tf, kline):
        sym_upper = symbol.upper()
        if sym_upper not in self.klines:
            return
            
        df = self.klines[sym_upper][tf]
        new_row = pd.DataFrame([{
            'open': float(kline['o']), 'high': float(kline['h']),
            'low': float(kline['l']), 'close': float(kline['c']), 'volume': float(kline['v'])
        }])
        
        self.klines[sym_upper][tf] = pd.concat([df, new_row], ignore_index=True).tail(100)
        
        if tf == '1h' and len(self.klines[sym_upper]['1h']) >= 15:
            df_1h = self.klines[sym_upper]['1h']
            atr_1h = self.calc_atr(df_1h)
            rsi_1h = self.calc_rsi(df_1h)
            close_price = float(kline['c'])
            
            features = {'rsi_1h': rsi_1h, 'atr_1h': atr_1h, 'close': close_price}
            
            # මෙතැනදී symbol එක upper කරලා නිවැරදි මොඩලය වෙත යවයි (උදා: BTCUSDT)
            signal = self.get_ml_prediction(sym_upper, features)
            
            if signal in ['BUY', 'SELL']:
                logger.info(f"[SIGNAL] {signal} triggered for {sym_upper} at {close_price}")
                self.record_signal(sym_upper, signal, close_price)
                self.execute_trade(sym_upper, signal, close_price, atr_1h)

    async def run(self):
        streams = [f"{s}@kline_1h" for s in SYMBOLS] + \
                  [f"{s}@kline_4h" for s in SYMBOLS] + \
                  [f"{s}@kline_1d" for s in SYMBOLS]
                  
        stream_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        logger.info("Connecting to Binance Multi-Asset WebSocket Feed...")
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.ws_connect(stream_url) as ws:
                        logger.info("Successfully connected to Binance Network.")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                stream_name = data.get('stream', '')
                                kline_data = data.get('data', {}).get('k', {})
                                
                                if kline_data.get('x'):
                                    tf = stream_name.split('_')[-1]
                                    symbol = kline_data.get('s', 'UNKNOWN')
                                    self.process_closed_candle(symbol, tf, kline_data)
                                    
                except Exception as e:
                    logger.warning(f"WebSocket network lag/disconnection: {e}. Reconnecting in 5s...")
                    await asyncio.sleep(5)

# ==========================================
# APPLICATION ENTRY POINT
# ==========================================
if __name__ == '__main__':
    init_db()
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Core engine shut down gracefully.")
        sys.exit(0)
