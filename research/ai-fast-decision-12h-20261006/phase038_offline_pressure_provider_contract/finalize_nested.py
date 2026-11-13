# -*- coding: utf-8 -*-
from pathlib import Path
import json,shutil,hashlib,datetime
from capsule import *
from test_capsule import synthetic,decay_fixture
P=Path(__file__).resolve().parent
snapshot=P/'pre_nested_guard_snapshot'
for name,state in [('synthetic_continuation',synthetic()),('synthetic_decay',decay_fixture()),('synthetic_cold',decay_fixture(True))]:
 f=P/(name+'_SYNTHETIC_NOT_MODEL_RUN.json')
 if not (snapshot/f.name).exists():shutil.copyfile(f,snapshot/f.name)
 f.write_text(json.dumps({'kind':'SYNTHETIC_NOT_MODEL_RUN','envelope':build_request(state,state['feature_completed_shared_ns']+1000000,state['source'])},indent=2)+'\n')
e=json.loads((P/'historical_offline_request.json').read_text());r=json.loads((P/'results.json').read_text())
r.update(status='OFFLINE_PRESSURE_CONTRACT_V13_STRICT_NESTED_PREPARATION_ONLY',tests=13,historical_compact_draft_bytes=len(canonical(e['offline_draft_payload'])),strict_nested_extra_rejection=True,model_state_rebuilt_known_fields=True,fixture_kind_fixed_enum=True,prepatch_gap_preserved='source diagnostic_note passed oldvalidate and entered offlineonly draft; no network/actualsend; PMO found; now failclosed',natural_language_or_source_authenticity='schema restriction notsemantictruth detector; legalidentifiers notauthenticated livecontent')
(P/'results.json').write_text(json.dumps(r,indent=2)+'\n')
s=(P/'README.md').read_text().replace('11个新增离线测试通过','13个新增离线测试通过').replace('模型草稿约5476字节','当前模型草稿约'+str(r['historical_compact_draft_bytes'])+'字节')
s+='\n## 嵌套隔离修正回执（V1.3）\n\nPMO发现旧版source.diagnostic_note可夹带未来自然语言进入离线draft；旧code/报告/freeze/manifest/results与示例保留在pre_nested_guard_snapshot，未有网络或可发送payload。当前source、book/trade provenance、trade witness、flow/asof/cost legs全部严格嵌套字段白名单；fixture_kind仅历史/合成固定枚举。模型草稿按已验证字段重新构建，不直接透传caller嵌套dict，报价仅保留price/size并附原内容hash。新增八个位置普通diagnostic_note及fixture枚举回归均失败关闭，13tests与原历史/数学/合成核验通过。\n\n本措施是schema限制，不是能自动识别所有自然语言未来内容的语义证明。语法合法run/trade标识、hash格式、caller时钟声明仍不代表真实性；历史实际源内容仅通过275个既存asof ordinal有限原件核验，真正live来源/新book/成交与provider仍未认证。transport保持硬禁、sendable始终null，无策略/经济规则变化或job011动作。\n'
(P/'README.md').write_text(s)
files=[x for x in P.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.relative_to(P).as_posix() not in ['manifest.json','seal_verification.json']]
freeze=json.loads((P/'execution_freeze.json').read_text());assert all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in freeze['hashes'].items())
m={'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'V13 strict nested offline input repair preservedold evidence','files':{x.relative_to(P).as_posix():{'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in files},'count':len(files),'bytes':sum(x.stat().st_size for x in files)}
(P/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');assert all(hashlib.sha256((P/n).read_bytes()).hexdigest()==v['sha256'] for n,v in m['files'].items())
(P/'seal_verification.json').write_text(json.dumps({'status':'PASS','files':len(files),'bytes':m['bytes']},indent=2)+'\n')
print(len(files),m['bytes'],r['historical_compact_draft_bytes'])
