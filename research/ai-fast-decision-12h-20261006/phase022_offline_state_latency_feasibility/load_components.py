from pathlib import Path
import json,gzip,hashlib
from measure import timed,clock
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'loading_component_freeze.json').read_text());assert hashlib.sha256((B/'load_components.py').read_bytes()).hexdigest()==freeze['code_sha256']
 compressed,read=timed(lambda:Path(p['source']).read_bytes());hash_,hash_time=timed(lambda:hashlib.sha256(compressed).hexdigest());assert hash_==p['source_gzip_sha256'];uncompressed,decomp=timed(lambda:gzip.decompress(compressed));lines,split=timed(lambda:uncompressed.splitlines());rows=[];start=clock();checkpoints=[]
 for index,line in enumerate(lines,1):
  rows.append(json.loads(line))
  if index in p['prefix_points']:
   end=clock();checkpoints.append({'rows':index,'parse_start_actual_OS_ns':start,'parse_end_actual_OS_ns':end,'JSON_parse_cumulative_ms':(end-start)/1e6})
  if index==max(p['prefix_points']):break
 result={'compressed_file_read_only':read,'SHA_integrity_only':hash_time,'whole_closed_source_gzip_decompress_only':decomp,'whole_closed_source_splitlines_only':split,'JSON_parse_fixedprefix_checkpoints':checkpoints,'compressed_bytes':len(compressed),'decompressed_bytes':len(uncompressed),'whole_decompress_extra_rows_not_factory_points':len(lines)-max(p['prefix_points']),'cache_conditions':'after priorbenchmark; OS/cache/load uncontrolled warmcontext, notcoldIO or livepipeline','factory_timing_unchanged':'timing_records.json original9 receipts retained'};(B/'loading_components.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':main()
