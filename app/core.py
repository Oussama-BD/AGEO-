import hashlib
import re
import unicodedata

TYPES = {"Author", "Institution", "Paper", "Topic"}
PAIRS = {"AUTHORED": ("Author", "Paper"), "AFFILIATED_WITH": ("Author", "Institution"),
         "ABOUT": ("Paper", "Topic"), "CITES": ("Paper", "Paper"),
         "COLLABORATES_WITH": ("Author", "Author")}

def normalized(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^\w]+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()

def entity_id(kind, name):
    return hashlib.sha256(f"{kind}:{normalized(name)}".encode()).hexdigest()[:24]

def document_id(text):
    return hashlib.sha256(text.encode()).hexdigest()

def evidence_text(text, dehyphenate=True):
    """Canonical text plus an offset map back to the exact original source."""
    skip = set()
    for match in re.finditer(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)", text):
        skip.update(range(match.start() if dehyphenate else match.start()+1, match.end()))
    chars, offsets = [], []
    for i, char in enumerate(text):
        if i in skip or char == "\u00ad":
            continue
        for value in unicodedata.normalize("NFKC", char):
            if value.isspace():
                if chars and chars[-1] != " ":
                    chars.append(" ")
                    offsets.append(i)
            else:
                chars.append(value)
                offsets.append(i)
    if chars and chars[-1] == " ":
        chars.pop()
        offsets.pop()
    return "".join(chars), offsets

def locate_quote(quote, text):
    if not isinstance(quote, str) or not quote.strip():
        return None
    for dehyphenate in (True,False):
        canonical, mapping = evidence_text(text,dehyphenate)
        wanted, _ = evidence_text(quote,dehyphenate)
        if not wanted:
            continue
        start = canonical.find(wanted)
        if start >= 0:
            return mapping[start], mapping[start+len(wanted)-1]+1
    return None

def sanitize_graph(graph, text, strict=False):
    if not isinstance(graph, dict) or set(graph) != {"entities", "relations"}:
        raise ValueError("Expected entities and relations")
    if not isinstance(graph["entities"], list) or not isinstance(graph["relations"], list):
        raise ValueError("Expected entity and relation arrays")
    entities = {}
    for e in graph["entities"]:
        if e.get("type") not in TYPES or not isinstance(e.get("name"), str) or not e["name"].strip():
            raise ValueError("Invalid entity")
        if not isinstance(e.get("id"), str) or e["id"] in entities:
            raise ValueError("Duplicate/missing extraction ID")
        entities[e["id"]] = dict(e)
    accepted, rejected = [], []
    for i, r in enumerate(graph["relations"]):
        reason = None
        if r.get("type") not in PAIRS or r.get("source") not in entities or r.get("target") not in entities:
            reason = "invalid_endpoint_or_type"
        elif (entities[r["source"]]["type"], entities[r["target"]]["type"]) != PAIRS[r["type"]]:
            reason = "incompatible_entity_types"
        span = locate_quote(r.get("quote"), text)
        if not reason and span is None:
            reason = "unsupported_quote"
        if reason:
            if strict:
                raise ValueError(reason)
            rejected.append({"relation_index": i, "reason": reason})
        else:
            start, end = span
            accepted.append(dict(r, quote=text[start:end], evidence_start=start, evidence_end=end))
    return {"entities": list(entities.values()), "relations": accepted}, {
        "accepted_relations": len(accepted), "rejected_relations": rejected,
        "normalization": "NFKC whitespace soft-hyphen and line-end hyphenation; no paraphrase matching"}

def validate_graph(graph, text):
    return sanitize_graph(graph, text, strict=True)[0]

def resolve(graph, enabled=True):
    mapping, entities = {}, {}
    for e in graph["entities"]:
        key = entity_id(e["type"], e["name"]) if enabled else e["id"]
        mapping[e["id"]] = key
        entities[key] = {"id": key, "name": e["name"].strip(), "type": e["type"]}
    relations = []
    for r in graph["relations"]:
        row = dict(r, source=mapping[r["source"]], target=mapping[r["target"]])
        if row not in relations:
            relations.append(row)
    return {"entities": list(entities.values()), "relations": relations}

def chunks(text, size=10000, overlap=600):
    if size <= overlap or overlap < 0:
        raise ValueError("Invalid chunk size")
    for start in range(0, len(text), size-overlap):
        yield text[start:start+size]

def score(expected, actual):
    expected, actual = set(expected), set(actual)
    if not expected and not actual:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "empty_case": True}
    tp = len(expected & actual)
    precision = tp / len(actual) if actual else 0
    recall = tp / len(expected) if expected else 0
    return {"precision": precision, "recall": recall,
            "f1": 2*precision*recall/(precision+recall) if precision+recall else 0,
            "empty_case": not expected}
