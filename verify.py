"""Journal de verification reproductible, sans appels LLM."""
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from app import pipeline
ROOT=Path(__file__).parent
class Result(unittest.TextTestResult):
    def addSuccess(self,test):
        super().addSuccess(test)
        self.details.append({"test":test.id(),"status":"passed"})
    def addError(self,test,err):
        super().addError(test,err)
        self.details.append({"test":test.id(),"status":"error"})
    def addFailure(self,test,err):
        super().addFailure(test,err)
        self.details.append({"test":test.id(),"status":"failed"})
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.details=[]

def main():
    reports=ROOT/"reports"
    reports.mkdir(exist_ok=True)
    with (reports/"tests.log").open("w",encoding="utf-8") as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(
            unittest.defaultTestLoader.discover(str(ROOT/"tests")))
    sources=[]
    for path in sorted((ROOT/"data"/"raw").iterdir()):
        if path.suffix in {".pdf",".html",".txt"}:
            text=pipeline.read_file(path)
            sources.append({"file":path.name,"bytes":path.stat().st_size,"characters":len(text),
                            "preview":text[:300]})
    integration=reports/"integration.json"
    docker_evidence=json.loads(integration.read_text(encoding="utf-8")) if integration.exists() else {}
    compose=subprocess.run(["docker","compose","config","--quiet"],capture_output=True,text=True)
    data={"verified_at":datetime.now(timezone.utc).isoformat(),
          "tests":{"run":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors),
                   "details":result.details},
          "sources":sources,
          "docker":{"integration_evidence":docker_evidence},
          "compose":{"exit_code":compose.returncode,"output":(compose.stdout+compose.stderr).strip()},
          "gemini":"live_extraction_and_benchmark; see real-extraction.json and real-benchmark.json"}
    (reports/"verification.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in data.items() if k!="sources"},ensure_ascii=False,indent=2))
    if not result.wasSuccessful(): sys.exit(1)
if __name__=="__main__": main()
