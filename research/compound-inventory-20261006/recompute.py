"""Offline coverage/error audit. Does not call RPC or manufacture observations."""
import json,pathlib,hashlib
P=pathlib.Path(__file__).parent
p=json.loads((P/'protocol.json').read_text());m=json.loads((P/'raw/archive_probe.meta.json').read_text());blocks=p['blocks']
assert len(blocks)==12 and len(set(blocks))==12
assert blocks[0]==p['start_block_approx_30_days'] and blocks[-1]==p['end_block']
steps=[b-a for a,b in zip(blocks,blocks[1:])];assert max(steps)-min(steps)<=1
assert p['frozen_unix']<=m['started_unix']
assert '403' in m['error']
r={'status':'BLOCKED_HTTP_403_BEFORE_HISTORICAL_OBSERVATIONS','routing':{'requested':'astra medium','actual':'UNKNOWN'},'public_request_operations':1,'rpc_submethods_requested':3,'rpc_submethods_successful':0,'historical_probe_block':26123665,'probe_original_error':m['error'],'error_response_body':'NOT_CAPTURED; exception string and request metadata retained','historical_RPC_support':'UNKNOWN; HTTP refusal is not proof that archival state is unsupported','frozen_blocks':blocks,'block_intervals':steps,'actual_start_header_timestamp':'UNKNOWN','actual_end_header_timestamp':'2026-10-06T04:11:59Z from sealed prior snapshot; not re-fetched this run','continuous_30_day_coverage':False,'sampled_states':0,'sufficient_inventory_examples':None,'profitable_examples':None,'logs_coverage':'NOT_REQUESTED due probe refusal','same_block_DEX':'NOT_RUN','next_block_state_and_DEX':'NOT_RUN','full_execution_and_gas':'NOT_RUN','inventory_ledger':{'initial_balance':'UNKNOWN','absorb_inflows':'UNKNOWN','buy_outflows':'UNKNOWN','simulated_buys':0,'simulated_inventory_consumption':0,'note':'No fabricated balances or profits. Zero simulated orders is a workflow count, not evidence of no historical opportunities.'},'samples':[{'block':b,'inventory':'UNKNOWN','reserves':'UNKNOWN','target_reserves':'UNKNOWN','buy_paused':'UNKNOWN','quote_100_USDC':'UNKNOWN','status':'NOT_REQUESTED_AFTER_PROBE_BLOCK'} for b in blocks],'next_required':'Documented supported archive access acceptable under existing no-bypass rule, then resume frozen sample set without overwriting this evidence.'}
r['public_request_operations']=4
r['logs_coverage']='REQUESTED_FROM_INDEPENDENT_BLOCKSCOUT_HTTP403_1010_NO_LOGS_RETURNED'
r['independent_public_probes']=[{'provider':'Etherscan official contract events page','error':'HTTP403 Forbidden'},{'provider':'LlamaRPC official website/documentation','error':'HTTP526 Unknown Status Code'},{'provider':'Blockscout Ethereum official public log API','error':'HTTP403 Forbidden; response body: error code: 1010'}]
(P/'results.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k] for k in ['status','public_request_operations','rpc_submethods_requested','sampled_states','sufficient_inventory_examples']},indent=2))
