"""
Quantum Alpha Swing Pro - Lite Edition
Lightweight Python trading system optimized for older CPUs.
Features: Asyncio Trading Loop, SQLite Database, Flask Web Dashboard (Daemon Thread).
"""
import asyncio
import websockets
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
MODEL_FILE = 'model.pkl'
INITIAL_BALANCE = 10000.0
RISK_PERCENT = 0.02
SYMBOLS = ['btcusdt']

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
    <h1>Quantum Alpha Swing Pro - Lite</h1>
    <div class="dashboard-container">
        <div class="card">
            <h2>Account Balance</h2>
            <h3 id="balance">Loading...</h3>
        </div>
        <div class="card">
            <h2>Active Trades</h2>
            <table id="trades-table">
                <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Entry</th><th>Size</th><th>SL</th><th>TP</th><th>Status</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>
        <div class="card">
            <h2>Recent Signals</h2>
            <table id="signals-table">
                <thead><tr><th>ID</th><th>Time</th><th>Symbol</th><th>Signal</th><th>Price</th></tr></thead>
                <tbody></tbody>
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
                    
                    const tradesTbody = document.querySelector('#trades-table tbody');
                    tradesTbody.innerHTML = '';
                    data.trades.forEach(trade => {
                        tradesTbody.innerHTML += `<tr>
                            <td>${trade.id}</td><td>${trade.symbol}</td><td>${formatSide(trade.side)}</td>
                            <td>$${trade.entry_price.toFixed(2)}</td><td>${trade.amount.toFixed(4)}</td>
                            <td>$${trade.sl.toFixed(2)}</td><td>$${trade.tp.toFixed(2)}</td><td>${trade.status}</td>
                        </tr>`;
                    });

                    const signalsTbody = document.querySelector('#signals-table tbody');
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
        // Auto-refresh every 10 seconds
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ==========================================
# FLASK WEB DASHBOARD (Runs in Daemon Thread)
# ==========================================
app = Flask(__name__)

@app.route('/')
def index():
    # Return raw string, no template engine rendering required
    return HTML_TEMPLATE

@app.route('/api/data')
def api_data():
    """API endpoint for the frontend dashboard to fetch db data."""
    try:
        # Read-only connection to avoid locking issues with Asyncio writer
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
        return jsonify({'account': {'balance': 0}, 'trades': [], 'signals': []})

def run_flask():
    """Starts the Flask server. Designed to be run in a separate thread."""
    logger.info("Starting Flask Dashboard on port 5000...")
    # use_reloader=False is crucial when running in a thread
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

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
    
    # Initialize account if empty
    c.execute("SELECT count(*) FROM account")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO account (balance) VALUES (?)", (INITIAL_BALANCE,))
    
    conn.commit()
    conn.close()

# ==========================================
# ASYNC TRADING BOT
# ==========================================
class TradingBot:
    def __init__(self):
        # Dataframes to hold recent klines for indicators
        self.klines = {
            '1h': pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']),
            '4h': pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']),
            '1d': pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        }
        self.model = self.load_model()
        # Connection for the writer thread
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        
    def load_model(self):
        """Loads pre-trained XGBoost model decoupled from training logic."""
        if os.path.exists(MODEL_FILE):
            try:
                import xgboost as xgb # Import inside function to avoid strict dependencies if missing
                with open(MODEL_FILE, 'rb') as f:
                    model = pickle.load(f)
                logger.info(f"Loaded ML model from {MODEL_FILE}")
                return model
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return None
        else:
            logger.warning(f"No pre-trained model found at {MODEL_FILE}. Using dummy logic.")
            return None

    def get_balance(self):
        c = self.conn.cursor()
        c.execute("SELECT balance FROM account ORDER BY id DESC LIMIT 1")
        res = c.fetchone()
        return res[0] if res else INITIAL_BALANCE

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
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        return atr.iloc[-1]

    def calc_rsi(self, df, period=14):
        if len(df) < period + 1:
            return 50.0
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def execute_trade(self, symbol, side, price, atr):
        balance = self.get_balance()
        risk_amount = balance * RISK_PERCENT
        
        # SL distance based on ATR
        sl_dist = atr * 2.0
        
        if sl_dist == 0:
            logger.warning("ATR is zero, skipping trade execution.")
            return

        position_size = risk_amount / sl_dist
        
        if side == 'BUY':
            sl = price - sl_dist
            tp = price + (sl_dist * 2.0) # 1:2 Risk to Reward
        else:
            sl = price + sl_dist
            tp = price - (sl_dist * 2.0)
            
        self.record_trade(symbol, side, price, position_size, sl, tp)
        logger.info(f"Executed {side} on {symbol} at {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f} | Size: {position_size:.4f}")

    def get_ml_prediction(self, features):
        """Uses pre-trained XGBoost model to get signals"""
        if self.model is None:
            # Fallback dummy logic for demonstration purposes
            rsi = features.get('rsi_1h', 50)
            if rsi < 30: return 'BUY'
            if rsi > 70: return 'SELL'
            return 'HOLD'
            
        try:
            # Assumes model takes these standardized features
            df_features = pd.DataFrame([features])
            pred = self.model.predict(df_features)[0]
            # Mapping assumed standard binary/ternary classification outputs
            if pred == 1: return 'BUY'
            elif pred == -1 or pred == 2: return 'SELL'
            return 'HOLD'
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return 'HOLD'

    def process_closed_candle(self, symbol, tf, kline):
        """Processes a closed candle and runs the trading logic on H1 close."""
        df = self.klines[tf]
        new_row = pd.DataFrame([{
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v'])
        }])
        
        # Append and keep memory footprint extremely lightweight (last 100 rows)
        self.klines[tf] = pd.concat([df, new_row], ignore_index=True).tail(100)
        
        # Evaluate logic strictly on H1 close
        if tf == '1h' and len(self.klines['1h']) >= 15:
            df_1h = self.klines['1h']
            
            atr_1h = self.calc_atr(df_1h)
            rsi_1h = self.calc_rsi(df_1h)
            close_price = float(kline['c'])
            
            # Form feature array for ML model
            features = {
                'rsi_1h': rsi_1h,
                'atr_1h': atr_1h,
                'close': close_price
                # Other indicators/features from H4/D1 can be added here
            }
            
            signal = self.get_ml_prediction(features)
            
            if signal in ['BUY', 'SELL']:
                logger.info(f"Signal Generated: {signal} for {symbol} at {close_price}")
                self.record_signal(symbol, signal, close_price)
                self.execute_trade(symbol, signal, close_price, atr_1h)

    async def run(self):
        """Main async loop for WebSocket ingestion"""
        # Listen to 1h, 4h, and 1d public klines for symbols
        streams = [f"{s}@kline_1h" for s in SYMBOLS] + \
                  [f"{s}@kline_4h" for s in SYMBOLS] + \
                  [f"{s}@kline_1d" for s in SYMBOLS]
                  
        stream_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        logger.info(f"Connecting to Binance WebSocket: {stream_url}")
        
        while True:
            try:
                async with websockets.connect(stream_url) as ws:
                    logger.info("Successfully connected to Binance WebSocket.")
                    while True:
                        payload = await ws.recv()
                        data = json.loads(payload)
                        
                        stream_name = data.get('stream', '')
                        kline_data = data.get('data', {}).get('k', {})
                        
                        # Process only when candle has closed ('x' = True)
                        if kline_data.get('x'):
                            tf = stream_name.split('_')[-1]
                            symbol = kline_data.get('s', 'UNKNOWN')
                            self.process_closed_candle(symbol, tf, kline_data)
                            
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket disconnected ({e}). Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in WS loop: {e}")
                await asyncio.sleep(5)

# ==========================================
# APPLICATION ENTRY POINT
# ==========================================
if __name__ == '__main__':
    # 1. Initialize SQLite Database
    init_db()
    
    # 2. Start Flask Dashboard in a background daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # 3. Start Asyncio Trading Bot in the main thread
    bot = TradingBot()
    
    try:
        # Run event loop
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down gracefully...")
        sys.exit(0)
