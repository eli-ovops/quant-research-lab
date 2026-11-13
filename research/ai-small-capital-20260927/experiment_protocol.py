"""Finite daily window checks. Does not create timers or start experiments."""
DAY_MS=86400000


def validate_protocol(p):
    if p['days']!=30 or p['interval_ms']!=DAY_MS:
        raise ValueError('INVALID_DURATION')
    if not isinstance(p['start_ms'],int) or p['end_ms']!=p['start_ms']+30*DAY_MS:
        raise ValueError('INVALID_DEADLINE')
    if not 0<p['window_ms']<DAY_MS:
        raise ValueError('INVALID_WINDOW')
    if not p.get('model_identifier') or p['model_identifier']=='UNKNOWN':
        raise ValueError('MODEL_NOT_FROZEN')
    if not p.get('prompt_sha256'):
        raise ValueError('PROMPT_NOT_FROZEN')


def validate_window(p,decision,now_ms):
    validate_protocol(p)
    if now_ms>=p['end_ms']:
        raise ValueError('EXPERIMENT_ENDED')
    i=decision.get('window_index')
    if type(i) is not int or not 0<=i<p['days']:
        raise ValueError('INVALID_WINDOW_INDEX')
    start=p['start_ms']+i*DAY_MS
    if not start<=decision['committed_ms']<=now_ms<start+p['window_ms']:
        raise ValueError('MISSED_OR_EARLY_WINDOW')
    if decision['slot']!=str(start):
        raise ValueError('SLOT_WINDOW_MISMATCH')


def coverage(p,decisions,now_ms):
    """Compute missed windows without inventing a replacement decision or trade."""
    validate_protocol(p)
    observed=set()
    for d in decisions:
        i=d['window_index']
        if i in observed:
            raise ValueError('DUPLICATE_WINDOW_INDEX')
        validate_window(p,d,d['committed_ms'])
        observed.add(i)
    missed=[i for i in range(p['days']) if i not in observed and
            p['start_ms']+i*DAY_MS+p['window_ms']<=now_ms]
    return {'observed_windows':len(observed),'missing_windows':missed,
            'deadline_reached':now_ms>=p['end_ms'],
            'all_windows_present':len(observed)==p['days']}
