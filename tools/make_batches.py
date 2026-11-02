"""Reconcile reviews with current candidates (by body_sha) and split unreviewed good candidates into batches.
Usage: python -I make_batches.py DATA FIRST_BATCH_NO N_BATCHES"""
import glob, json, sys
D, first, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
C = [json.loads(l) for l in open(f"{D}/cands.jsonl")]
R = [r for f in sorted(glob.glob(f"{D}/reviews/b*.json")) for r in json.load(open(f))]
# rejections caused by converter bugs that have since been fixed are reviewed again
REREVIEW = {("2610.00579v1", 1)}  # \wire[u]{q} control link (fixed)
R = [r for r in R if (r["id"], r["k"]) not in REREVIEW or r["decision"] == "accept"]
rev = {(r["id"], r.get("body_sha")) for r in R}
gs = {(c["id"], c.get("body_sha")): c for c in C}
for r in R:
    if r["decision"] == "accept":
        c = gs.get((r["id"], r.get("body_sha")))
        if not c or not c.get("ok"):
            print("ACCEPTED NOW MISSING/FAILED", r["id"], r["k"], c and c.get("reason"))
        elif c["k"] != r["k"]:
            print("k changed", r["id"], r["k"], "->", c["k"])
good = [c for c in C if c.get("ok") and c["n"] >= 3 and c["n_cx"] >= 6]
new = [c for c in good if (c["id"], c["body_sha"]) not in rev]
print("good", len(good), "new", len(new), "papers", len({c["id"] for c in new}))
by = {}
for c in new:
    by.setdefault(c["id"], []).append(c["k"])
prior = {}
for r in R:
    if r["decision"] == "accept":
        prior.setdefault(r["id"], []).append(f'k={r["k"]} {r["name"]}')
ids = sorted(by, reverse=True)
for j in range(n):
    ch = sorted(ids[j::n], reverse=True)
    if not ch:
        continue
    name = f"b{first + j:02d}"
    json.dump({i: by[i] for i in ch}, open(f"{D}/batches/{name}.json", "w"))
    print(name, len(ch), sum(len(by[i]) for i in ch), "prior:", {i: prior[i] for i in ch if i in prior})
