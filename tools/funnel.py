"""Selection-funnel statistics of a pipeline run (the table in README.md).

Usage: python -I funnel.py DATA_DIR OUT_JSON [DATE_FROM DATE_TO]
Reads DATA_DIR/{meta.json, kw.json, src_index.jsonl, cands.jsonl, reviews/b*.json}.
"""
import glob, json, sys
D = sys.argv[1]
date_from, date_to = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("2026-06-28", "2026-10-28")
idx = {}
for l in open(f"{D}/src_index.jsonl"):
    r = json.loads(l); idx[r["id"]] = r
C = [json.loads(l) for l in open(f"{D}/cands.jsonl")]
R = {}
for f in sorted(glob.glob(f"{D}/reviews/b*.json")):
    for r in json.load(open(f)):
        R[(r["id"], r.get("body_sha") or r["k"], r["k"])] = r  # same key as build_dataset.py
reviewed = {k[:2] for k in R}
acc = {k: r for k, r in R.items() if r["decision"] == "accept"}
st = {"date_from": date_from, "date_to": date_to,
      "n_meta": len(json.load(open(f"{D}/meta.json"))), "n_kw": len(json.load(open(f"{D}/kw.json"))),
      "n_downloaded": sum(1 for r in idx.values() if r.get("ok")),
      "n_with_diagrams": len({c["id"] for c in C}), "n_diagrams": len(C),
      "n_concrete": sum(1 for c in C if c.get("ok")),
      "n_candidates": sum(1 for c in C if c.get("ok") and c["n"] >= 3 and c["n_cx"] >= 6),
      "n_reviewed": sum(1 for c in C if c.get("ok") and c["n"] >= 3 and c["n_cx"] >= 6 and (c["id"], c["body_sha"]) in reviewed),
      "n_accepted": len(acc), "n_papers_accepted": len({k[0] for k in acc})}
json.dump(st, open(sys.argv[2], "w"), indent=1); print(st)
