exec(open(__file__.replace('fetch_extra.py','fetch_public.py')).read().split('receipts=[]')[0])
REQS={
 'prediction_history':'https://clob.polymarket.com/prices-history?market=17723060028706211434353196815974529233235154894595948093265217171930153234260&startTs=1704672000&endTs=1704931200&fidelity=5',
 'future_tiers':'https://www.okx.com/api/v5/public/position-tiers?instType=FUTURES&tdMode=isolated&instFamily=BTC-USD',
 'option_mark':'https://www.okx.com/api/v5/public/mark-price?instType=OPTION&instId=BTC-USD-261009-85500-C'
}
exec(open(__file__.replace('fetch_extra.py','fetch_public.py')).read().split('receipts=[]')[1].replace("'fetch_receipts.json'","'extra_receipts.json'").join(['receipts=[]','']))
