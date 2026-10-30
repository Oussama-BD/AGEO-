"""Scan source files before publication; does not print candidate secret values."""
from pathlib import Path
import re,sys,subprocess
ROOT=Path(__file__).parent
patterns=[('API token format',rb'AQ\.[0-9A-Za-z_-]{35,}'),('Google API key',rb'AIza[0-9A-Za-z_-]{30,}'),('GitHub token',rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),('private key',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),('private Windows path',rb'C:[/\\]Users[/\\]AdMin')]
issues=[]
# Scan the publication set; ignored runtime logs are not part of the repository.
if (ROOT/'.git').exists():
 result=subprocess.run(['git','-c','safe.directory='+str(ROOT.resolve()),'ls-files','-z'],cwd=ROOT,capture_output=True,check=True)
 files=[ROOT/name for name in result.stdout.decode().split('\0') if name]
else:
 files=[p for p in ROOT.rglob('*') if '.runtime' not in p.relative_to(ROOT).parts and (p.parent.name!='reports' or p.name=='corpus-graph-v3.json')]
for p in files:
 if not p.is_file() or any(part in {'.git','.venv','__pycache__','.test-tmp'} for part in p.relative_to(ROOT).parts):continue
 if p.name.startswith('.env') and p.name!='.env.example':issues.append((str(p.relative_to(ROOT)),'local environment file'));continue
 if p.name==Path(__file__).name or p.suffix.lower() in {'.pdf','.png','.jpg'}:continue
 data=p.read_bytes()
 for label,pattern in patterns:
  if re.search(pattern,data):issues.append((str(p.relative_to(ROOT)),label))
for path,label in issues:print(label+': '+path)
print('PUBLICATION_SCAN', 'FAIL' if issues else 'PASS')
sys.exit(bool(issues))
