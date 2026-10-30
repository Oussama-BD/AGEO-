"""Extraction deterministe des metadonnees arXiv; aucune annotation de reference lue."""
from html.parser import HTMLParser
from pathlib import Path
from app.core import document_id, entity_id, normalized, validate_graph

def name_key(value):
    return normalized(value).translate(str.maketrans({"ł":"l","ø":"o","đ":"d","æ":"ae","œ":"oe"}))

class MetaParser(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True)
        self.text=text
        self.lines=[0]
        self.lines.extend(i+1 for i,c in enumerate(text) if c=="\n")
        self.meta={}
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag.lower()!="meta" or not values.get("name","").startswith("citation_"):
            return
        line,column=self.getpos()
        start=self.lines[line-1]+column
        raw=self.get_starttag_text()
        self.meta.setdefault(values["name"],[]).append({"value":values.get("content",""),
            "quote":raw,"start":start,"end":start+len(raw)})

def parse_arxiv(text):
    parsed=MetaParser(text).meta
    def first(name):
        if name not in parsed:raise ValueError("Missing arXiv metadata: "+name)
        return parsed[name][0]
    title=first("citation_title")
    authors=[]
    for item in parsed.get("citation_author",[]):
        family,sep,given=item["value"].partition(",")
        authors.append(dict(item,name=(given.strip()+" "+family.strip()) if sep else family.strip()))
    if not authors:raise ValueError("No citation_author metadata")
    return {"title":title,"authors":authors,"abstract":first("citation_abstract") if "citation_abstract" in parsed else None,
            "arxiv_id":first("citation_arxiv_id")["value"] if "citation_arxiv_id" in parsed else None}

def author_graph(text, existing_entities=(), publication_id=None, paper_entity_id=None):
    meta=parse_arxiv(text)
    known={(e["type"],name_key(e["name"])):e for e in existing_entities}
    entities={}
    def node(kind,name):
        found=known.get((kind,name_key(name)))
        item=dict(found) if found else {"id":entity_id(kind,name),"name":name,"type":kind}
        entities[item["id"]]=item
        return item["id"]
    if paper_entity_id is not None:
        if publication_id != meta["arxiv_id"]:
            raise ValueError("Cannot merge paper identities from different arXiv IDs")
        matches=[e for e in existing_entities if e["id"]==paper_entity_id and e["type"]=="Paper"]
        if len(matches)!=1:raise ValueError("Ambiguous existing paper identity")
        item=dict(matches[0]);entities[item["id"]]=item;pid=item["id"]
    else:
        pid=node("Paper",meta["title"]["value"])
    relations=[]
    for author in meta["authors"]:
        aid=node("Author",author["name"])
        start=min(meta["title"]["start"],author["start"])
        end=max(meta["title"]["end"],author["end"])
        relations.append({"source":aid,"target":pid,"type":"AUTHORED","quote":text[start:end],
            "evidence_start":start,"evidence_end":end,
            "evidence_parts":[meta["title"],{k:v for k,v in author.items() if k!="name"}],
            "method":"arxiv_citation_metadata"})
    graph=validate_graph({"entities":list(entities.values()),"relations":relations},text)
    return {"document":{"id":"html-"+document_id(text),"title":meta["title"]["value"],
                        "source":"https://arxiv.org/abs/"+meta["arxiv_id"]},
            "graph":graph,"mode":"deterministic_html_metadata","arxiv_id":meta["arxiv_id"],
            "abstract":meta["abstract"]["value"] if meta["abstract"] else None,
            "llm_calls":0}
