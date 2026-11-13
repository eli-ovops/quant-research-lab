import json
from pathlib import Path
def require_authorized():
 p=json.loads((Path(__file__).resolve().parent/'protocol.json').read_text())
 if p.get('mode')!='AUTHORIZED_CLOSED_EVALUATION' or not isinstance(p.get('raw_logical_sha256'),str) or len(p['raw_logical_sha256'])!=64:raise RuntimeError('PREPARE_ONLY_NO_EIGHT_RULE_RUN')
