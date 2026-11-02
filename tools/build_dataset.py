"""Assemble the dataset (circuits/, manifest.csv, manifest.jsonl, review_log.jsonl) from accepted review records.

Usage: python -I build_dataset.py SCRIPTS_DIR DATA_DIR OUT_DIR [--max 100] [--write]

For every accepted (id, body_sha):
  1. re-convert the diagram from the paper's LaTeX source with the recorded parameters,
  2. check the reviewed final QASM is the same unitary as the re-conversion (n <= 12),
  3. normalize with tikz2qasm.normalize_qasm and check it loads in qiskit (and in pytket and
     quspect when they are installed),
  4. (with --write) write OUT_DIR/circuits/<file>.qasm, OUT_DIR/manifest.csv / manifest.jsonl
     (newest paper first) and OUT_DIR/review_log.jsonl.

`description_en` is taken from the review record if present, otherwise carried over from an
existing OUT_DIR/manifest.jsonl (matched by file name), otherwise left empty.
"""
import csv
import glob
import hashlib
import json
import os
import sys

SCRIPTS, DATA, OUT = sys.argv[1:4]
MAX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 100
WRITE = "--write" in sys.argv
sys.path.insert(0, SCRIPTS)

from qiskit import QuantumCircuit, qasm2  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

from tikz2qasm import (INPUT_GATES, Abstract, collect_macros, diagram_to_circuit, finalize,  # noqa: E402
                       find_envs, normalize_qasm, read_paper_tex)

CIRCUITS = os.path.join(OUT, "circuits")

try:
    from pytket.qasm import circuit_from_qasm_str
except ImportError:
    circuit_from_qasm_str = None
    print("note: pytket not installed, skipping the pytket load check")
try:
    from quspect.ir import qasm2_loads
except ImportError:
    qasm2_loads = None
    print("note: quspect not installed, skipping the quspect load check")

prev_en = {}
if os.path.exists(os.path.join(OUT, "manifest.jsonl")):
    for line in open(os.path.join(OUT, "manifest.jsonl")):
        r = json.loads(line)
        prev_en[r["file"]] = r.get("description_en", "")

meta = {x["id"]: x for x in json.load(open(os.path.join(DATA, "meta.json")))}
reviews = [r for f in sorted(glob.glob(os.path.join(DATA, "reviews", "b*.json"))) for r in json.load(open(f))]
acc = {}
for r in reviews:
    if r["decision"] == "accept":
        acc[(r["id"], r["body_sha"])] = r
order = sorted(acc.values(), key=lambda r: (meta[r["id"]]["published"], r["id"], r["k"]), reverse=True)


def load(path):
    return QuantumCircuit.from_qasm_str(open(path).read())


rows, problems = [], []
for r in order:
    pid = r["id"]
    tex = read_paper_tex(os.path.join(DATA, "src", pid))
    env = [(kind, body) for kind, body, _ in find_envs(tex)
           if hashlib.sha256(body.strip().encode()).hexdigest()[:16] == r["body_sha"]]
    if not env or len(set(env)) != 1:  # the same diagram body may appear twice verbatim in a paper
        problems.append((pid, r["k"], f"diagram with body_sha not found uniquely ({len(env)})"))
        continue
    preset = {k: float(v) for k, v in (r.get("params") or {}).items()}
    try:
        qc, flags = diagram_to_circuit(env[0][0], env[0][1], collect_macros(tex), preset)
    except Abstract as e:
        problems.append((pid, r["k"], f"re-conversion now rejected: {e}"))
        continue
    regen, st = finalize(qc)
    # final_qasm paths may be written relative to the work directory as "S/..."
    fq = r["final_qasm"]
    if fq.startswith("S/"):
        fq = fq.replace("S/", os.path.dirname(DATA.rstrip("/")) + "/", 1)
    final = load(fq)
    if qc.num_qubits <= 12 and not Operator(final).equiv(Operator(regen)):
        problems.append((pid, r["k"], "reviewed final QASM differs from re-conversion"))
        continue
    norm = normalize_qasm(qasm2.dumps(regen))
    nq = QuantumCircuit.from_qasm_str(norm)
    names = {i.operation.name for i in nq.data}
    assert names <= set(INPUT_GATES), names
    if circuit_from_qasm_str is not None:
        circuit_from_qasm_str(norm)
    if qasm2_loads is not None:
        qasm2_loads(norm)
    n2q = sum(1 for i in nq.data if i.operation.num_qubits == 2)
    nccx = nq.count_ops().get("ccx", 0)
    short = pid.split("v")[0]
    fname = f"arxiv{short}_{r['name']}_{nq.num_qubits}.qasm"
    m = meta[pid]
    rows.append({
        "file": fname, "arxiv_id": pid, "url": f"https://arxiv.org/abs/{pid}",
        "title": m["title"], "submitted": m["published"][:10], "primary_category": m["primary"],
        "description_zh": r["description_zh"],
        "description_en": r.get("description_en") or prev_en.get(fname, ""),
        "category": r["category"],
        "n_qubits": nq.num_qubits, "n_2q": n2q, "n_ccx": nccx, "n_2q_ccx6": n2q + 6 * nccx,
        "depth": nq.depth(), "source": f"LaTeX {env[0][0]} diagram (diagram #{r['k']} in source)",
        "params_source": r.get("params_source", ""), "verification": r["verification"],
        "flags": ";".join(f for f in flags if not f.startswith(("symbolic_params", "paper_params"))),
        "_qasm": norm,
    })

print(f"accepted {len(acc)}  built {len(rows)}  problems {len(problems)}")
for p in problems:
    print("PROBLEM", *p)
rows = rows[:MAX]
names = [r["file"] for r in rows]
assert len(names) == len(set(names)), "duplicate file names"
for r in rows:
    print(f'{r["arxiv_id"]:14s} {r["submitted"]} n={r["n_qubits"]:2d} 2q={r["n_2q"]:4d} ccx={r["n_ccx"]:3d} {r["file"]}')

if WRITE:
    os.makedirs(CIRCUITS, exist_ok=True)
    for old in glob.glob(os.path.join(CIRCUITS, "*.qasm")):
        os.remove(old)
    cols = [k for k in rows[0] if not k.startswith("_")]
    with open(os.path.join(OUT, "manifest.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})
            open(os.path.join(CIRCUITS, r["file"]), "w").write(r["_qasm"])
    with open(os.path.join(OUT, "manifest.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in cols}, ensure_ascii=False) + "\n")
    # full review log (accepted and rejected), so every decision is traceable; a later review of the
    # same diagram replaces an earlier one, while a verbatim duplicate of a diagram at another
    # position k (same body_sha) keeps its own record
    seen = {}
    for r in reviews:
        seen[(r["id"], r.get("body_sha") or r["k"], r["k"])] = r
    with open(os.path.join(OUT, "review_log.jsonl"), "w") as f:
        for r in sorted(seen.values(), key=lambda r: (r["id"], r["k"]), reverse=True):
            f.write(json.dumps({"arxiv_id": r["id"], "title": meta[r["id"]]["title"], "diagram": r["k"],
                                "decision": r["decision"], "reason": r["reason"]}, ensure_ascii=False) + "\n")
    print("wrote", len(rows), "circuits to", CIRCUITS)
