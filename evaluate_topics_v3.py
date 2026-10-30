import json
from pathlib import Path
from app.core import score
R=Path('.')
refs=json.loads((R/'data/references-v3/topics.proposed.json').read_text(encoding='utf-8'))
pred=json.loads((R/'data/experiments/v3/topics.predicted.json').read_text(encoding='utf-8'))
expected={(a['arxiv_id'],t) for a in refs['papers'] for t in a['topics']}
actual={(aid,t['name']) for aid,ts in pred.items() for t in ts}
report={'model':'gemini-3.1-flash-lite','scope':'25 abstracts; ABOUT only','reference_review':refs['review_status'],'reference_assertions':len(expected),'predicted_assertions':len(actual),'micro_metrics_provisional':score(expected,actual),'missing_provisional_reference':sorted(expected-actual),'extra_vs_provisional_reference':sorted(actual-expected)}
(R/'reports/topics-v3-provisional-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['missing_provisional_reference','extra_vs_provisional_reference']},indent=2))
