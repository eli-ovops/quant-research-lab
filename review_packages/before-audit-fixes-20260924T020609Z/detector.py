"""Public market observation only. No credentials, private endpoints or orders."""
import argparse
import json
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path


def levels(rows):
    result = {}
    for row in rows:
        price, size = D(row[0]), D(row[1])
        if not price.is_finite() or not size.is_finite() or price <= 0 or size < 0:
            raise ValueError('invalid level')
        result[price] = size
    return result


class Book:
    def __init__(self):
        self.bids, self.asks = {}, {}
        self.valid = False
        self.seq = None
        self.ts = 0
        self.received = 0

    def apply(self, bids, asks, ts, seq, snapshot, previous=None):
        if not snapshot:
            if not self.valid:
                raise ValueError('delta before snapshot')
            if previous is not None and previous != self.seq:
                self.valid = False
                raise ValueError('sequence gap')
            if previous is None and seq <= self.seq:
                self.valid = False
                raise ValueError('non-increasing sequence')
        nb, na = levels(bids), levels(asks)
        if snapshot:
            self.bids, self.asks = {}, {}
        for target, updates in [(self.bids, nb), (self.asks, na)]:
            for price, size in updates.items():
                if size == 0:
                    target.pop(price, None)
                else:
                    target[price] = size
        self.seq, self.ts, self.received = seq, int(ts), time.monotonic()
        self.valid = bool(self.bids and self.asks and max(self.bids) < min(self.asks))
        if not self.valid:
            raise ValueError('empty or crossed book')

    def view(self):
        return dict(bids=sorted(self.bids.items(), reverse=True),
                    asks=sorted(self.asks.items()), ts=self.ts,
                    received=self.received, valid=self.valid)


def spend(asks, budget):
    remaining, quantity = budget, D(0)
    for price, size in asks:
        used = min(remaining, price * size)
        quantity += used / price
        remaining -= used
        if remaining == 0:
            return quantity
    return None


def sell(bids, quantity):
    remaining, proceeds = quantity, D(0)
    for price, size in bids:
        used = min(remaining, size)
        proceeds += used * price
        remaining -= used
        if remaining == 0:
            return proceeds
    return None


def evaluate(buy, sale, budget, buy_fee, sell_fee, buffer_bps,
             now_ms=None, mono=None, max_age_ms=2000, max_skew_ms=500):
    now_ms = time.time() * 1000 if now_ms is None else now_ms
    mono = time.monotonic() if mono is None else mono
    for b in [buy, sale]:
        if not b['valid']:
            return {'status': 'INVALID_BOOK'}
        if not -250 <= now_ms - b['ts'] <= max_age_ms or (mono-b['received'])*1000 > max_age_ms:
            return {'status': 'STALE_OR_CLOCK_ERROR'}
    if abs(buy['ts'] - sale['ts']) > max_skew_ms:
        return {'status': 'UNSYNCHRONIZED'}
    qty = spend(buy['asks'], budget)
    revenue = sell(sale['bids'], qty) if qty else None
    if revenue is None:
        return {'status': 'INSUFFICIENT_DEPTH'}
    fees = budget * buy_fee / D(10000) + revenue * sell_fee / D(10000)
    reserve = budget * buffer_bps / D(10000)
    net = revenue - budget - fees - reserve
    return dict(status='ESTIMATE_ONLY', quantity=str(qty), gross_usdt=str(revenue-budget),
                fees_usdt=str(fees), extra_buffer_usdt=str(reserve), net_usdt=str(net),
                net_bps=str(net/budget*10000), buy_vwap=str(budget/qty), sell_vwap=str(revenue/qty),
                depth_impact_included=True, inventory_required=True,
                exchange_skew_ms=abs(buy['ts']-sale['ts']))


def ingest(venue, message, books):
    if venue == 'gate' and message.get('channel') == 'spot.order_book' and message.get('event') == 'update':
        d = message['result']
        symbol = d['s'].replace('_', '')
        books[symbol].apply(d['bids'], d['asks'], d['t'], d['lastUpdateId'], True)
        return symbol
    if venue == 'okx' and 'arg' in message and 'data' in message:
        symbol = message['arg']['instId'].replace('-', '')
        for d in message['data']:
            books[symbol].apply(d['bids'], d['asks'], d['ts'], d['seqId'],
                                message['action'] == 'snapshot', d.get('prevSeqId'))
        return symbol
    if venue == 'bybit' and message.get('topic', '').startswith('orderbook.'):
        d = message['data']
        books[d['s']].apply(d['b'], d['a'], message.get('cts', message['ts']),
                            d['u'], message['type'] == 'snapshot' or d['u'] == 1)
        return d['s']


def worker(venue, symbols, books, lock, stop, output, proxy_port, retain_raw=True, log_tag=''):
    import websocket
    url = {'okx': 'wss://ws.okx.com:8443/ws/v5/public',
           'gate': 'wss://api.gateio.ws/ws/v4/',
           'bybit': 'wss://stream.bybit.com/v5/public/spot'}[venue]
    payload = {'op': 'subscribe', 'args': (
        [{'channel': 'books', 'instId': s[:-4]+'-USDT'} for s in symbols]
        if venue == 'okx' else ['orderbook.50.'+s for s in symbols])}
    delay = 1
    with (output/(venue+log_tag+'-events.jsonl')).open('a') as log:
        while not stop.is_set():
            ws = None
            try:
                kwargs = dict(timeout=8)
                if proxy_port:
                    kwargs.update(http_proxy_host='127.0.0.1', http_proxy_port=proxy_port, proxy_type='http')
                ws = websocket.create_connection(url, **kwargs)
                if venue == 'gate':
                    for s in symbols:
                        ws.send(json.dumps({'time': int(time.time()), 'channel': 'spot.order_book',
                                            'event': 'subscribe', 'payload': [s[:-4]+'_USDT', '100', '100ms']}))
                        if stop.wait(0.1): break
                else:
                    ws.send(json.dumps(payload))
                ping_at = time.monotonic()
                while not stop.is_set():
                    raw = ws.recv()
                    if raw == 'pong':
                        continue
                    d = json.loads(raw)
                    if retain_raw:
                        log.write(json.dumps({'received_ms':time.time()*1000, 'message':d})+'\n')
                    if d.get('event') == 'error' or d.get('success') is False or d.get('error'):
                        raise ValueError('subscription rejected')
                    with lock:
                        ingest(venue, d, books)
                    delay = 1
                    if time.monotonic()-ping_at > 15:
                        ping = json.dumps({'time': int(time.time()), 'channel': 'spot.ping'}) if venue == 'gate' else '{"op":"ping"}'
                        ws.send('ping' if venue == 'okx' else ping)
                        ping_at = time.monotonic()
            except Exception as exc:
                # Never log exception payloads, proxy environment, or request headers.
                log.write(json.dumps({'received_ms':time.time()*1000, 'error':type(exc).__name__})+'\n')
                log.flush()
            finally:
                with lock:
                    for b in books.values():
                        b.valid = False
                if ws:
                    ws.close()
            if stop.wait(delay):
                break
            delay = min(delay*2, 15)


def main():
    p = argparse.ArgumentParser(description='只读套利观察；不加载账户，不下单')
    p.add_argument('--seconds', type=int, default=60)
    p.add_argument('--proxy-port', type=int, default=0)
    p.add_argument('--fee-bps', type=D, default=D('10'), help='每边假设手续费，10 bps=0.1%%')
    p.add_argument('--buffer-bps', type=D, default=D('5'), help='额外双腿合计安全余量；不是已观测滑点')
    p.add_argument('--amounts', default='100,500,1000')
    p.add_argument('--symbols', default='ZECUSDT,UNIUSDT', help='逗号分隔的 USDT 现货币对，如 ZECUSDT,UNIUSDT')
    p.add_argument('--venues', default='okx,gate')
    p.add_argument('--fee-source', default='假设费率，未核实账户')
    a = p.parse_args()
    venues = [v.strip().lower() for v in a.venues.split(',')]
    if len(venues) != 2 or len(set(venues)) != 2 or any(v not in ['okx','gate','bybit'] for v in venues):
        p.error('选择两个不同交易所：okx,gate,bybit')
    amounts = [D(x) for x in a.amounts.split(',')]
    symbols = list(dict.fromkeys(x.strip().upper() for x in a.symbols.split(',')))
    if not symbols or len(symbols) > 10 or any(not s.isascii() or not s.isalnum() or not s.endswith('USDT') or len(s) <= 4 for s in symbols):
        p.error('使用 1–10 个 USDT 现货币对')
    if not 1 <= a.seconds <= 86400 or any(not x.is_finite() or x <= 0 for x in amounts):
        p.error('invalid duration or amounts')
    if any(not x.is_finite() or x < 0 for x in [a.fee_bps, a.buffer_bps]):
        p.error('fees and buffer must be finite and nonnegative')
    output = Path(__file__).parent/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True)
    config = dict(duration_seconds=a.seconds, fee_bps=str(a.fee_bps), buffer_bps=str(a.buffer_bps),
                  amounts=[str(x) for x in amounts], fee_source=a.fee_source, actual_fill_fees_verified=False, live_trading=False,
                  symbols=symbols, venues=venues)
    (output/'config.json').write_text(json.dumps(config,indent=2))
    lock, stop = threading.Lock(), threading.Event()
    books = {v:{s:Book() for s in config['symbols']} for v in config['venues']}
    threads = [threading.Thread(target=worker,args=(v,config['symbols'],books[v],lock,stop,output,a.proxy_port),daemon=True) for v in books]
    for t in threads:t.start()
    counts, best = {}, {}
    deadline = time.monotonic()+a.seconds
    try:
        with (output/'samples.jsonl').open('w') as log:
            while time.monotonic() < deadline:
                with lock:
                    views = {v:{s:b.view() for s,b in bs.items()} for v,bs in books.items()}
                for symbol in config['symbols']:
                    for buy,sale in [venues, venues[::-1]]:
                        for amount in amounts:
                            r = evaluate(views[buy][symbol],views[sale][symbol],amount,a.fee_bps,a.fee_bps,a.buffer_bps)
                            r.update(symbol=symbol,buy=buy,sell=sale,amount_usdt=str(amount),observed_ms=time.time()*1000)
                            log.write(json.dumps(r)+'\n')
                            counts[r['status']] = counts.get(r['status'],0)+1
                            key = f'{symbol} {buy}→{sale} {amount} USDT'
                            if r['status']=='ESTIMATE_ONLY' and (key not in best or D(r['net_usdt'])>D(best[key]['net_usdt'])):
                                best[key]=r
                stop.wait(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for t in threads:t.join(timeout=10)
    summary = {'config':config,'counts':counts,'best':best,'positive_samples_are_not_trades':True}
    (output/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    lines = ['# 套利观察结果（非交易回测）','',
             '仅公开现货盘口；卖出侧必须预持有币。没有下单，没有验证最小订单及精度。',
             f'费率来源：{a.fee_source}；每边 {a.fee_bps} bps，额外缓冲合计 {a.buffer_bps} bps。',
             '净值已计多档盘口价格、双边输入手续费及额外缓冲；未计实际再平衡费用、单边失败损失。',
             '重复正值采样不代表独立机会；本报告最大值不能用于估算日收益。','',
             f'样本状态：{counts}', '', '|方向 / 金额|最高估算净额 USDT|净基点|','|---|---:|---:|']
    for k,r in sorted(best.items()):
        lines.append(f"|{k}|{D(r['net_usdt']):.4f}|{D(r['net_bps']):.2f}|")
    if not best:lines.append('\n未取得可比较的有效盘口，不能判断有无盈利空间。')
    (output/'报告.md').write_text('\n'.join(lines),encoding='utf-8')
    print(output/'报告.md')
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
