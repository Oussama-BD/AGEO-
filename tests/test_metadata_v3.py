import unittest
from app.arxiv_metadata import author_graph,parse_arxiv,name_key
from app.core import validate_graph
HTML='''<html><head>
<meta name="citation_title" content="Paper &amp; evidence">
<meta name="citation_author" content="Kaiser, Lukasz">
<meta name="citation_author" content="Vaswani, Ashish">
<meta name="citation_arxiv_id" content="1706.03762">
<meta name="citation_abstract" content="A study of attention.">
</head></html>'''

class MetadataTests(unittest.TestCase):
    def test_name_order(self):
        self.assertEqual(parse_arxiv(HTML)["authors"][0]["name"],"Lukasz Kaiser")
    def test_all_authors_with_exact_source(self):
        record=author_graph(HTML)
        self.assertEqual(len(record["graph"]["relations"]),2)
        validate_graph(record["graph"],HTML)
        for relation in record["graph"]["relations"]:
            self.assertEqual(HTML[relation["evidence_start"]:relation["evidence_end"]],relation["quote"])
            self.assertEqual(len(relation["evidence_parts"]),2)
    def test_diacritic_alias(self):
        self.assertEqual(name_key("Łukasz Kaiser"),name_key("Lukasz Kaiser"))
    def test_same_id_resolves_title_variant(self):
        entities=[{"id":"old-paper","name":"Paper and Evidence","type":"Paper"}]
        result=author_graph(HTML,entities,"1706.03762","old-paper")
        self.assertTrue(all(r["target"]=="old-paper" for r in result["graph"]["relations"]))
    def test_different_arxiv_ids_not_merged(self):
        with self.assertRaises(ValueError):
            author_graph(HTML,[{"id":"p","name":"x","type":"Paper"}],"9999.99999","p")
    def test_missing_authors_rejected(self):
        with self.assertRaises(ValueError):parse_arxiv('<meta name="citation_title" content="x">')


    def test_timing_fields_without_network_or_real_ledger(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from app import llm
        response=SimpleNamespace(text="ok",usage_metadata=SimpleNamespace(
            prompt_token_count=1,candidates_token_count=1,thoughts_token_count=0))
        with tempfile.TemporaryDirectory(dir="reports") as folder:
            fake_file=Path(folder).resolve()/"app"/"llm.py"
            with patch("app.llm.Path",return_value=fake_file),patch("app.llm.client") as client,patch("app.llm.time.sleep"),patch("app.llm._LAST_REQUEST",0):
                client.return_value.__enter__.return_value.models.generate_content.return_value=response
                text,usage=llm.generate("unit test")
                self.assertEqual(text,"ok")
                self.assertEqual(usage["timing_version"],3)
                self.assertTrue(all(usage[k]>=0 for k in ["rate_wait_s","retry_wait_s","request_wall_s"]))
                self.assertGreaterEqual(usage["latency_s"],usage["request_wall_s"])
                self.assertTrue((Path(folder)/"reports"/"gemini-usage.jsonl").exists())
