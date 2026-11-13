import json, pathlib, subprocess, time, datetime
P = pathlib.Path(__file__).resolve().parent
records = []
for symbol in ['BTC', 'ETH']:
    for page in range(3):
        end = 1791244800000 - page * 100 * 900000
        url = f'https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history?instId={symbol}-USDT-SWAP&period=15m&begin=1790984699999&end={end}&limit=100'
        name = f'{symbol.lower()}_oi_{page}.json'
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        r = subprocess.run(['curl', '--max-time', '20', '--silent', '--show-error', url], capture_output=True)
        (P/'raw'/name).write_bytes(r.stdout)
        record = {'file': name, 'url': url, 'requested_at_utc': started, 'exit_code': r.returncode, 'stderr': r.stderr.decode()}
        records.append(record)
        print(json.dumps(record), flush=True)
        time.sleep(.5)
(P/'raw'/'oi_requests.json').write_text(json.dumps(records, indent=2))
