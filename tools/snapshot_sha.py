"""Attach body_sha (hash of the reviewed diagram's LaTeX body) to each review record, from DATA_DIR/cands/<id>__<k>.tex.

Usage: python -I snapshot_sha.py DATA_DIR REVIEW_JSON   (REVIEW_JSON is rewritten in place)
"""
import hashlib, json, os, sys
data, review = sys.argv[1], sys.argv[2]
R = json.load(open(review))
for r in R:
    p = os.path.join(data, "cands", f"{r['id']}__{r['k']}.tex")
    if "body_sha" not in r and os.path.exists(p):
        r["body_sha"] = hashlib.sha256(open(p).read().strip().encode()).hexdigest()[:16]
json.dump(R, open(review, "w"), ensure_ascii=False, indent=1)
print(review, sum("body_sha" in r for r in R), "/", len(R))
