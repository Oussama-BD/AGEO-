import copy
import json
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import demo, rag
from app.api import app
from app.core import sanitize_graph, locate_quote, score

class ReviewFixTests(unittest.TestCase):
    def test_whitespace_keeps_original_source_span(self):
        source="Alice\n  is affiliated with\tAtlas."
        span=locate_quote("Alice is affiliated with Atlas.",source)
        self.assertEqual(source[span[0]:span[1]],source)

    def test_ligature_nfkc(self):
        self.assertIsNotNone(locate_quote("fine tuning","ﬁne\ntuning"))

    def test_line_end_hyphenation(self):
        self.assertIsNotNone(locate_quote("information retrieval","infor-\nmation retrieval"))

    def test_paraphrase_not_accepted(self):
        self.assertIsNone(locate_quote("Alice works at Atlas","Alice is affiliated with Atlas"))

    def test_reject_one_relation_preserve_segment(self):
        graph=copy.deepcopy(demo.fixture()["graph"])
        graph["relations"][0]["quote"]="Invented fact"
        cleaned,report=sanitize_graph(graph,demo.TEXT)
        self.assertEqual(len(cleaned["relations"]),9)
        self.assertEqual(report["rejected_relations"],[{"relation_index":0,"reason":"unsupported_quote"}])

    def test_empty_answer_metric_convention_explicit(self):
        result=score([],[])
        self.assertEqual(result["f1"],1)
        self.assertTrue(result["empty_case"])

    def test_question_only_plan_uses_question_without_oracle(self):
        with patch("app.llm.generate",return_value=(json.dumps({"mode":"institutions","terms":["Patrick Lewis"]}),{})) as generate:
            plan=rag.plan_question("Quelles affiliations pour Patrick Lewis ?")
            self.assertEqual(plan["terms"],["Patrick Lewis"])
            prompt=generate.call_args.args[0]
            self.assertNotIn("Facebook",prompt)

    def test_question_only_retrieval(self):
        with patch("app.rag.plan_question",return_value={"terms":["Patrick Lewis"],"mode":"institutions","usage":{}}),patch("app.store.retrieve",return_value=[]) as retrieve:
            result=rag.ask("Quelles affiliations pour Patrick Lewis ?")
            retrieve.assert_called_once_with("Patrick Lewis",document_ids=None)
            self.assertEqual(result["retrieval_mode"],"question_only")

    def test_api_accepts_question_without_term(self):
        with patch.dict(os.environ,{"API_TOKEN":"unit-test","GEMINI_API_KEY":"unit-test-no-network"}),patch("app.rag.ask",return_value={"answer":"ok"}) as ask:
            response=TestClient(app).post("/ask",headers={"x-api-token":"unit-test"},
                json={"question":"Quelles affiliations pour Patrick Lewis ?"})
            self.assertEqual(response.status_code,200)
            self.assertIsNone(ask.call_args.args[1])


    def test_preserve_real_hyphen_across_linebreak(self):
        self.assertIsNotNone(locate_quote("fine-tuning","fine-\ntuning"))

    def test_daily_quota_is_not_retried(self):
        from app import llm
        from google.genai import errors
        error=errors.ClientError(429,{"error":{"code":429,"message":"requests per day limit exceeded"}})
        with patch("app.llm.client") as client,patch("app.llm.time.sleep"),patch("app.llm._LAST_REQUEST",0):
            model=client.return_value.__enter__.return_value.models.generate_content
            model.side_effect=error
            with self.assertRaises(errors.ClientError):llm.generate("unit test")
            self.assertEqual(model.call_count,1)
