"""Offline TradingAgents component trial on recorded public OKX candles.

Overrides the input loader in this process only. No installed files are edited.
No LLM call, no credentials, no trade, no claim of a full agent run.
"""
import hashlib
import importlib.metadata
import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def blocked(*args, **kwargs):
    raise RuntimeError('NETWORK_DISABLED_IN_COMPONENT_TRIAL')

socket.socket.connect = blocked
socket.create_connection = blocked

import pandas as pd
from tradingagents.dataflows.vendors.yahoo import market

raw = json.loads((ROOT / 'public-candles.json').read_text())
rows = sorted((r for r in raw['data'] if r[-1] == '1'), key=lambda r: int(r[0]))
assert len(rows) >= 50
assert all(int(b[0]) - int(a[0]) == 86400000 for a, b in zip(rows, rows[1:]))
frame = pd.DataFrame({
    'Date': pd.to_datetime([int(r[0]) for r in rows], unit='ms', utc=True).tz_localize(None),
    **{name: [float(r[i]) for r in rows] for i, name in enumerate(['Open', 'High', 'Low', 'Close', 'Volume'], start=1)},
})
as_of = frame['Date'].iloc[-1].strftime('%Y-%m-%d')
def local_loader(symbol, date):
    assert symbol == 'ETH-USDT-SWAP' and date == as_of
    return frame.copy(deep=True)

market.load_ohlcv = local_loader
indicators = {}
for name in ['close_50_sma', 'close_10_ema', 'rsi', 'macd', 'atr']:
    indicators[name] = float(market.get_stockstats_indicator('ETH-USDT-SWAP', name, as_of))

out = {
    'package_version': importlib.metadata.version('tradingagents'),
    'scope': 'OFFLINE_TECHNICAL_COMPONENT_ONLY',
    'source': 'OKX ETH-USDT-SWAP confirmed 1D candles; exchange day boundary retained',
    'data_sha256': hashlib.sha256((ROOT / 'public-candles.json').read_bytes()).hexdigest(),
    'rows': len(rows), 'last_bar_start': str(frame['Date'].iloc[-1]),
    'last_close': float(frame['Close'].iloc[-1]), 'indicators': indicators,
    'llm_run': False, 'orders': 0, 'profitability_validated': False,
    'limitations': ['Daily module, not 15m futures execution.', 'No 200-bar SMA: insufficient warmup.', 'No liquidation, fees or funding model in this component.'],
}
(ROOT / 'component-result.json').write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
