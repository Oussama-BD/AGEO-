import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from app import pipeline, store, demo

parser = argparse.ArgumentParser(description="Scientific Knowledge Graph")
sub = parser.add_subparsers(dest="command", required=True)
fetch = sub.add_parser("collect")
fetch.add_argument("--search", default="knowledge graph retrieval")
fetch.add_argument("--limit", type=int, default=10)
ingest = sub.add_parser("ingest")
ingest.add_argument("file")
ingest.add_argument("--no-hdfs", action="store_true")
ingest.add_argument("--defer-neo4j", action="store_true")
sub.add_parser("seed")
sub.add_parser("import-spark")
args = parser.parse_args()
if args.command == "collect":
    result = pipeline.fetch_openalex(args.search, args.limit)
elif args.command == "ingest":
    result = pipeline.process(Path(args.file), not args.no_hdfs, not args.defer_neo4j)
elif args.command == "seed":
    result = demo.fixture()
    store.ingest(result["document"], result["graph"])
elif args.command == "import-spark":
    result = pipeline.import_spark()
print(json.dumps(result, ensure_ascii=False, indent=2))
