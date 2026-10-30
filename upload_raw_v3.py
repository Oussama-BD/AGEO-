"""Persist and verify original HTML sources for the expanded HDFS corpus."""
import subprocess,json,hashlib,uuid
from pathlib import Path
ROOT=Path(__file__).parent

def command(args):
 r=subprocess.run(['docker','compose']+args,cwd=ROOT,capture_output=True)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[:500])
 return r.stdout
command(['cp','data/raw/abstracts-v3/.','namenode:/tmp/ageo-v3-raw-html'])
command(['exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','hdfs','dfs','-mkdir','-p','/knowledge/v3/raw-html'])
command(['exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','/bin/bash','-c','hdfs dfs -put -f /tmp/ageo-v3-raw-html/*.html /knowledge/v3/raw-html/'])
remote_readback='/tmp/ageo-v3-raw-readback-'+uuid.uuid4().hex[:12]
command(['exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','hdfs','dfs','-get','/knowledge/v3/raw-html',remote_readback])
local=ROOT/'.runtime/hdfs-v3-raw-readback';local.mkdir(parents=True,exist_ok=True)
command(['cp','namenode:'+remote_readback+'/.',str(local)])
rows=[]
for p in sorted((ROOT/'data/raw/abstracts-v3').glob('*.html')):
 data=(local/p.name).read_bytes()
 if data!=p.read_bytes():raise ValueError('Raw source mismatch '+p.name)
 rows.append({'file':p.name,'sha256':hashlib.sha256(data).hexdigest()})
(ROOT/'reports/hdfs-v3-raw-verified.json').write_text(json.dumps({'count':len(rows),'hdfs_path':'/knowledge/v3/raw-html','files':rows},indent=2),encoding='utf-8')
print('RAW_HTML_HDFS_VERIFIED',len(rows))
