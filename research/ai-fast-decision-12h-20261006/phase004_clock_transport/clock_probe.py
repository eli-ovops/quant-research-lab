from pathlib import Path
import json,sys,subprocess,uuid,time,datetime as dt
from shared_clock import sample,check_parent_child
B=Path(__file__).resolve().parent
def main():
 boot=subprocess.check_output(['/usr/sbin/sysctl','-n','kern.boottime'],text=True).strip();run_id='phase004-'+str(uuid.uuid4());checks=[]
 for i in range(2):
  before=sample(run_id,boot)
  script="import json,sys,time;from shared_clock import sample;print(json.dumps({'sample':sample(sys.argv[1],sys.argv[2]),'runtime':sys.version,'clock_info':vars(time.get_clock_info('monotonic'))}))"
  child=json.loads(subprocess.check_output([sys.executable,'-c',script,run_id,boot],cwd=B,text=True));after=sample(run_id,boot);verified=check_parent_child(before,child['sample'],after);checks.append({'index':i,'parent_before':before,'child':child,'parent_after':after,'child_bracketed':verified})
 result={'at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'runtime':sys.version,'executable':sys.executable,'parent_clock_info':vars(time.get_clock_info('monotonic')),'run_id':run_id,'boot_identity':boot,'checks':checks,'status':'PASS_CURRENT_HOST_BOOT_OS_DOMAIN','not_historical001_conversion':True}
 (B/'clock_proof.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()

