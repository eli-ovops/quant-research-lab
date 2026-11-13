"""Verify an explicitly supplied input/receipt pair. Does not call a model."""
import hashlib
import json
from paper_ledger import ASSETS, validate_decision


def strict_json(text):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('DUPLICATE_JSON_KEY')
            result[key]=value
        return result
    def invalid(value):
        raise ValueError('NONFINITE_JSON')
    return json.loads(text,object_pairs_hook=pairs,parse_constant=invalid)


def verify(input_bytes,expected_sha,receipt,runtime,expected_thread,
           expected_turn,expected_model,expected_effort):
    sha=hashlib.sha256(input_bytes).hexdigest()
    if sha!=expected_sha:raise ValueError('INPUT_HASH_MISMATCH')
    packet=strict_json(input_bytes)
    if receipt['threadId']!=expected_thread or runtime['thread_id']!=expected_thread:
        raise ValueError('WRONG_THREAD')
    if receipt['turnId']!=expected_turn or not receipt.get('messageId'):
        raise ValueError('WRONG_TURN_OR_MESSAGE')
    matches=[r for r in runtime['records'] if r['turn_id']==expected_turn]
    if len(matches)!=1:raise ValueError('AMBIGUOUS_RUNTIME')
    route=matches[0]
    if (route['model'],route['effort'])!=(expected_model,expected_effort):
        raise ValueError('RUNTIME_CHANGED')
    if not expected_model or expected_model=='UNKNOWN' or expected_effort=='UNKNOWN':
        raise ValueError('RUNTIME_UNKNOWN')
    # App receipt timestamps have second precision: allow only that precision margin.
    start_ms=int(receipt['startedAt'])*1000
    end_ms=int(receipt['completedAt'])*1000
    if not packet['prepared_ms']<=start_ms+999 or end_ms<start_ms:
        raise ValueError('INPUT_AFTER_MODEL_START')
    if end_ms+999-packet['prepared_ms']>600000:
        raise ValueError('DECISION_TOO_LATE')
    if set(packet['assets'])!=set(ASSETS):raise ValueError('ASSET_SET_CHANGED')
    for asset in ASSETS:
        rows=packet['assets'][asset]['closed_4h_candles']
        if len(rows)<43 or any(x[8]!='1' for x in rows):
            raise ValueError('UNCONFIRMED_OR_SHORT_HISTORY')
        stamps=[int(x[0]) for x in rows]
        if any(b-a!=14400000 for a,b in zip(stamps,stamps[1:])):
            raise ValueError('CANDLE_GAP_OR_DUPLICATE')
        closed_end=stamps[-1]+14400000
        if not 0<=packet['prepared_ms']-closed_end<14400000:
            raise ValueError('CANDLE_FUTURE_OR_STALE')
    d=strict_json(receipt['text'])
    if d.get('status')=='INPUT_INCOMPLETE':raise ValueError('MODEL_INPUT_INCOMPLETE')
    if set(d)!={'weights','rationale','invalidation','uncertainty'}:
        raise ValueError('RESPONSE_SCHEMA')
    if any(not isinstance(d[k],str) or not d[k].strip()
           for k in ('rationale','invalidation','uncertainty')):
        raise ValueError('MISSING_REASON_FIELDS')
    d.update(input_sha256=sha,source_thread_id=expected_thread,
             source_turn_id=expected_turn,source_message_id=receipt['messageId'],
             model=route['model'],effort=route['effort'])
    validate_decision(d)
    return d
