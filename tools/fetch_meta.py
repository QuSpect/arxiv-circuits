"""Fetch quant-ph metadata (primary or cross-list) submitted in a date range, newest first.

Usage: python -I fetch_meta.py OUT_JSON [FROM_YYYYMMDDHHMM TO_YYYYMMDDHHMM]
The dataset used two ranges: 202606280000-202608272359 and 202608280000-202610282359 (the default).
"""
import json, sys, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
out = sys.argv[1]
lo, hi = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("202608280000", "202610282359")
q = f"cat:quant-ph AND submittedDate:[{lo} TO {hi}]"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
recs, start, step = [], 0, 1000
while True:
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "sortBy": "submittedDate", "sortOrder": "descending",
         "start": start, "max_results": step})
    for attempt in range(5):
        try:
            data = urllib.request.urlopen(url, timeout=120).read(); break
        except Exception as e:
            print("retry", e, file=sys.stderr); time.sleep(10)
    root = ET.fromstring(data)
    total = int(root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults").text)
    entries = root.findall("a:entry", NS)
    for e in entries:
        links = {l.get("title") or l.get("rel"): l.get("href") for l in e.findall("a:link", NS)}
        recs.append({
            "id": e.find("a:id", NS).text.rsplit("/abs/", 1)[1],
            "title": " ".join(e.find("a:title", NS).text.split()),
            "abstract": " ".join(e.find("a:summary", NS).text.split()),
            "published": e.find("a:published", NS).text,
            "primary": e.find("arxiv:primary_category", NS).get("term"),
            "cats": [c.get("term") for c in e.findall("a:category", NS)],
            "comment": (e.find("arxiv:comment", NS).text if e.find("arxiv:comment", NS) is not None else ""),
        })
    print(f"start={start} got={len(entries)} total={total}", file=sys.stderr)
    start += step
    if not entries or start >= total: break
    time.sleep(4)
json.dump(recs, open(out, "w"), ensure_ascii=False)
print(len(recs))
