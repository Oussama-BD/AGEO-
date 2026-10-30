"""Resume V3 infrastructure after Docker storage recovery; never resets volumes."""
import subprocess,sys,json,hashlib,os,uuid,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).parent

def cmd(args,log=None):
 r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 if log:(ROOT/'reports'/log).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
 if r.returncode:raise RuntimeError('Command failed: '+args[0]+'; inspect '+str(log))
 return r.stdout

def run():
 cmd(['docker','compose','exec','-T','namenode','/bin/bash','-c','cat /etc/os-release'], 'docker-v3-storage-check.log')
 cmd(['docker','compose','cp','data/experiments/v3/records/.','namenode:/tmp/ageo-v3-records'],'hdfs-v3-copy.log')
 for attempt in range(18):
  try:
   cmd(['docker','compose','exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','hdfs','dfsadmin','-safemode','wait'],'hdfs-v3-readiness.log')
   break
  except RuntimeError:
   if attempt==17:raise
   time.sleep(5)
 cmd(['docker','compose','exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','hdfs','dfs','-mkdir','-p','/knowledge/v3/extracted'],'hdfs-v3-mkdir.log')
 cmd(['docker','compose','exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','/bin/bash','-c','hdfs dfs -put -f /tmp/ageo-v3-records/*.json /knowledge/v3/extracted/'],'hdfs-v3-upload.log')
 remote_readback='/tmp/ageo-v3-readback-'+uuid.uuid4().hex[:12]
 cmd(['docker','compose','exec','-T','-e','HADOOP_CONF_DIR=/config','namenode','hdfs','dfs','-get','/knowledge/v3/extracted',remote_readback],'hdfs-v3-readback.log')
 readback=ROOT/'.runtime/hdfs-v3-readback';readback.mkdir(parents=True,exist_ok=True)
 cmd(['docker','compose','cp','namenode:'+remote_readback+'/.',str(readback)],'hdfs-v3-download.log')
 checks=[]
 for p in sorted((ROOT/'data/experiments/v3/records').glob('*.json')):
  data=(readback/p.name).read_bytes()
  if data!=p.read_bytes():raise ValueError('HDFS readback mismatch '+p.name)
  checks.append({'file':p.name,'sha256':hashlib.sha256(data).hexdigest()})
 (ROOT/'reports/hdfs-v3-verified.json').write_text(json.dumps({'files':checks,'verified_count':len(checks)},indent=2),encoding='utf-8')
 print('HDFS_VERIFIED',len(checks),flush=True)
 cmd(['docker','compose','run','--rm','--entrypoint','/opt/spark/bin/spark-submit','spark','--master','local[2]','--driver-memory','512m','/project/jobs/transform_v3.py'],'spark-v3.log')
 parts=list((ROOT/'data/experiments/v3/spark').glob('part-*.json'))
 rows=[json.loads(line) for p in parts for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
 if len(rows)!=28 or sum(len(r['graph']['relations']) for r in rows)!=382:raise ValueError('Unexpected Spark output counts')
 (ROOT/'reports/spark-v3-success.json').write_text(json.dumps({'documents':len(rows),'relations':382,'mode':'local[2]','timestamp':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
 os.environ['NEO4J_URI']='bolt://127.0.0.1:7687'
 cmd([sys.executable,'-m','app.corpus_v3','--input','spark'],'neo4j-v3-import.log')
 cmd(['docker','compose','up','-d','--no-deps','--no-build','api'],'api-v3-deploy.log')
 print('V3_HDFS_SPARK_NEO4J_DEPLOY_COMPLETE')
if __name__=='__main__':run()
