import copy
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.core import validate_graph, resolve, entity_id, chunks, score
from app import demo, local_demo, rag, pipeline
from app.api import app
from benchmark import CASES

class ProjectTests(unittest.TestCase):
    def test_fixture_provenance(self):
        record=demo.fixture()
        validate_graph(record["graph"],demo.TEXT)
        self.assertEqual(len(record["graph"]["entities"]),9)
        self.assertEqual(len(record["graph"]["relations"]),10)

    def test_unknown_endpoint_rejected(self):
        graph=copy.deepcopy(demo.fixture()["graph"])
        graph["relations"][0]["target"]="unknown"
        with self.assertRaises(ValueError): validate_graph(graph,demo.TEXT)

    def test_invented_quote_rejected(self):
        graph=copy.deepcopy(demo.fixture()["graph"])
        graph["relations"][0]["quote"]="Invented evidence"
        with self.assertRaises(ValueError): validate_graph(graph,demo.TEXT)

    def test_invalid_type_pair_rejected(self):
        graph=copy.deepcopy(demo.fixture()["graph"])
        graph["relations"][0]["type"]="ABOUT"
        with self.assertRaises(ValueError): validate_graph(graph,demo.TEXT)

    def test_resolution_accents_and_case(self):
        self.assertEqual(entity_id("Author","Alicé Martin"),entity_id("Author","ALICE MARTIN"))
        self.assertNotEqual(entity_id("Author","Atlas"),entity_id("Institution","Atlas"))

    def test_resolution_merges_aliases(self):
        graph={"entities":[{"id":"a","name":"Alice Martin","type":"Author"},
                           {"id":"b","name":"ALICE MARTIN","type":"Author"}],"relations":[]}
        self.assertEqual(len(resolve(graph)["entities"]),1)
        self.assertEqual(len(resolve(graph,False)["entities"]),2)

    def test_chunk_coverage(self):
        text="abcdefghijklmnopqrstuvwxyz"
        parts=list(chunks(text,10,2))
        rebuilt=parts[0]+"".join(p[2:] for p in parts[1:])
        self.assertEqual(rebuilt,text)

    def test_all_reference_queries(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                actual={r["answer"] for r in local_demo.analytics(case["mode"],case["term"])}
                self.assertEqual(actual,set(case["expected"]))

    def test_metrics_penalize_extra_answer(self):
        self.assertEqual(score(["a"],["a","b"])["precision"],.5)

    def test_auth_and_validation(self):
        client=TestClient(app)
        with patch.dict(os.environ,{"API_TOKEN":"test-only-token"}):
            self.assertEqual(client.post("/analytics",json={"mode":"papers","term":"Bob"}).status_code,401)
            self.assertEqual(client.post("/analytics",headers={"x-api-token":"test-only-token"},
                json={"mode":"arbitrary","term":"Bob"}).status_code,422)
            self.assertEqual(client.post("/ingest",headers={"x-api-token":"test-only-token"},
                json={"filename":"../../.env"}).status_code,400)

    def test_demo_public_but_not_secret(self):
        client=TestClient(app)
        self.assertEqual(client.get("/demo").json()["mode"],"manual_fixture")
        self.assertEqual(client.get("/").status_code,200)

    def test_rag_unknown_source_rejected(self):
        with patch("app.store.retrieve",return_value=demo.facts()),patch("app.llm.generate",
            return_value=('{"answer":"x","items":["Alice"],"source_ids":["invented"]}',{})):
            with self.assertRaises(ValueError): rag.ask("Qui ?","Graph")

    def test_rag_no_results_no_llm(self):
        with patch("app.store.retrieve",return_value=[]),patch("app.llm.generate") as generate:
            self.assertEqual(rag.ask("Qui ?","inconnu")["items"],[])
            generate.assert_not_called()

    def test_html_reader(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir="data/raw") as folder:
            path=Path(folder)/"sample.html"
            path.write_text("<h1>Article</h1><p>Texte</p>",encoding="utf-8")
            self.assertEqual(pipeline.read_file(path),"Article Texte")

    def test_rag_valid_sources(self):
        import json
        doc=demo.fixture()["document"]["id"]
        with patch("app.store.retrieve",return_value=demo.facts()),patch("app.llm.generate",
            return_value=(json.dumps({"answer":"Alice","items":["Alice Martin"],"source_ids":[doc]}),{})):
            self.assertEqual(len(rag.ask("Qui ?","Graph")["sources"]),10)

if __name__=="__main__":
    unittest.main(verbosity=2)
