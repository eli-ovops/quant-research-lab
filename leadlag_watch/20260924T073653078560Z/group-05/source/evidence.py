"""Bounded public-data evidence journal and websocket capture. No private API."""
import gzip
import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path
from detector import ingest


class EvidenceFailure(RuntimeError):
    pass


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    tmp.replace(path)


class Journal:
    """Caller serializes append/close with the book lock; gzip shards close every minute."""
    def __init__(self, root, max_bytes=4*1024**3, min_free=20*1024**3, shard_seconds=60):
        self.root = Path(root)
        self.max_bytes, self.min_free = max_bytes, min_free
        self.shard_seconds = shard_seconds
        self.seq = self.total = 0
        self.files = []
        self.stream = self.raw = None
        self.failure = None

    def check(self):
        size = self.total + (self.raw.tell() if self.raw else 0)
        if size >= self.max_bytes or shutil.disk_usage(self.root).free < self.min_free:
            raise EvidenceFailure('evidence storage limit')

    def append(self, kind, **data):
        try:
            self.check()
            if self.stream and time.monotonic()-self.opened >= self.shard_seconds:
                self._close_shard()
            if self.stream is None:
                self.path = self.root / ('journal-%06d.jsonl.gz' % len(self.files))
                self.raw = self.path.open('xb')
                self.stream = gzip.GzipFile(fileobj=self.raw, mode='wb', mtime=0)
                self.opened = time.monotonic()
            self.seq += 1
            row = dict(journal_seq=self.seq, kind=kind, **data)
            self.stream.write((json.dumps(row, separators=(',', ':'))+'\n').encode())
            return self.seq
        except Exception as exc:
            self.failure = type(exc).__name__
            raise EvidenceFailure(self.failure) from exc

    def flush(self):
        self.stream.flush() if self.stream else None

    def _close_shard(self):
        if self.stream is None:
            return
        self.stream.close()
        self.raw.close()
        size = self.path.stat().st_size
        self.total += size
        self.files.append(dict(file=self.path.name, bytes=size,
                               sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                               last_seq=self.seq))
        self.stream = self.raw = None
        atomic_json(self.root/'journal_manifest.json', dict(files=self.files, last_seq=self.seq))

    def close(self):
        self._close_shard()


def audit_worker(venue, symbols, books, lock, stop, journal, proxy_port):
    import websocket
    url = {'okx':'wss://ws.okx.com:8443/ws/v5/public',
           'gate':'wss://api.gateio.ws/ws/v4/'}[venue]
    delay = 1
    while not stop.is_set():
        ws, connection = None, str(uuid.uuid4())
        try:
            kwargs = dict(timeout=8)
            if proxy_port:
                kwargs.update(http_proxy_host='127.0.0.1', http_proxy_port=proxy_port, proxy_type='http')
            ws = websocket.create_connection(url, **kwargs)
            with lock:
                for book in books.values():
                    book.reset(connection)
                journal.append('connect', venue=venue, connection_id=connection,
                               received_ms=time.time()*1000, mono=time.monotonic())
            payloads = ([{'time':int(time.time()), 'channel':'spot.order_book', 'event':'subscribe',
                          'payload':[s[:-4]+'_USDT','100','100ms']} for s in symbols] if venue=='gate' else
                        [{'op':'subscribe','args':[{'channel':'books','instId':s[:-4]+'-USDT'} for s in symbols]}])
            for payload in payloads:
                ws.send(json.dumps(payload))
                with lock:
                    journal.append('subscribe', venue=venue, connection_id=connection, payload=payload)
            ping_at = time.monotonic()
            while not stop.is_set():
                raw = ws.recv()
                received_ms, mono = time.time()*1000, time.monotonic()
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8')
                with lock:
                    ref = journal.append('frame', venue=venue, connection_id=connection,
                                         received_ms=received_ms, mono=mono,
                                         processed_ms=time.time()*1000, raw=raw)
                    if raw != 'pong':
                        try:
                            msg = json.loads(raw)
                            if msg.get('event')=='error' or msg.get('success') is False or msg.get('error'):
                                raise ValueError('subscription rejected')
                            symbol = ingest(venue, msg, books)
                        except Exception:
                            for book in books.values():
                                book.valid = False
                            raise
                        if symbol:
                            book = books[symbol]
                            book.ref, book.received, book.received_ms = ref, mono, received_ms
                delay = 1
                if time.monotonic()-ping_at > 15:
                    ws.send('ping' if venue=='okx' else json.dumps({'time':int(time.time()),'channel':'spot.ping'}))
                    ping_at = time.monotonic()
        except EvidenceFailure:
            stop.set()
        except Exception as exc:
            with lock:
                try:
                    journal.append('connection_error', venue=venue, connection_id=connection,
                                   received_ms=time.time()*1000, error=type(exc).__name__)
                except EvidenceFailure:
                    stop.set()
        finally:
            with lock:
                for book in books.values():
                    book.valid = False
                try:
                    journal.append('disconnect', venue=venue, connection_id=connection,
                                   received_ms=time.time()*1000)
                except EvidenceFailure:
                    stop.set()
            if ws:
                ws.close()
        if stop.wait(delay):
            break
        delay = min(delay*2, 15)
