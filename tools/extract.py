"""Run tikz2qasm over every downloaded paper source that contains circuit diagrams.

Usage: python -I extract.py SCRIPTS_DIR DATA_DIR
Writes DATA_DIR/cands/<id>__<k>.qasm and DATA_DIR/cands.jsonl (one line per diagram,
including rejected ones with the reason). Sources are read as text only.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
from tikz2qasm import Abstract, collect_macros, diagram_to_circuit, finalize, find_envs, read_paper_tex, strip_comments  # noqa: E402

from qiskit import qasm2, transpile  # noqa: E402

DATA = sys.argv[2]
os.makedirs(os.path.join(DATA, "cands"), exist_ok=True)
out_path = os.path.join(DATA, "cands.jsonl")
done = set()
if os.path.exists(out_path):
    done = {json.loads(l)["id"] for l in open(out_path)}
idx = [json.loads(l) for l in open(os.path.join(DATA, "src_index.jsonl"))]
with open(out_path, "a") as fo:
    for rec in idx:
        if not rec.get("marks") or rec["id"] in done:
            continue
        done.add(rec["id"])
        d = os.path.join(DATA, "src", rec["id"].replace("/", "_"))
        tex = read_paper_tex(d)
        macros = collect_macros(tex)
        k = 0
        wrote = False
        for kind, body, off in find_envs(tex):
            k += 1
            r = {"id": rec["id"], "k": k, "kind": kind, "offset": off,
                 "body_sha": hashlib.sha256(body.strip().encode()).hexdigest()[:16]}
            cap = re.search(r"\\caption\{", tex[off: off + 6000])
            r["caption"] = re.sub(r"\s+", " ", tex[off + cap.end(): off + cap.end() + 400]) if cap else ""
            try:
                qc, flags = diagram_to_circuit(kind, body, macros)
                norm, st = finalize(qc)
                r.update(ok=True, n_ops_raw=len(qc.data), flags=flags, ops_raw=dict(qc.count_ops()), **st)
                path = os.path.join(DATA, "cands", f"{rec['id'].replace('/', '_')}__{k}.qasm")
                open(path, "w").write(qasm2.dumps(norm))
                r["qasm"] = path
                open(path[:-5] + ".txt", "w").write(str(qc.draw("text", fold=160, idle_wires=False)))
                open(path[:-5] + ".tex", "w").write(body)
            except Abstract as e:
                r.update(ok=False, reason=f"abstract: {e}"[:200])
            except Exception as e:  # parse failures
                r.update(ok=False, reason=f"{type(e).__name__}: {e}"[:200])
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            wrote = True
        # OpenQASM 2.0 listings embedded in the text (exact source; parsed, never executed)
        for m in re.finditer(r"OPENQASM\s+2\.0\s*;", tex):
            end = re.search(r"\\end\{(lstlisting|verbatim|minted|Verbatim)\}", tex[m.start():])
            src = tex[m.start(): m.start() + (end.start() if end else 20000)]
            k += 1
            r = {"id": rec["id"], "k": k, "kind": "openqasm", "offset": m.start(), "caption": "",
                 "body_sha": hashlib.sha256(src.strip().encode()).hexdigest()[:16]}
            try:
                from qiskit import QuantumCircuit
                qc = QuantumCircuit.from_qasm_str(src)
                qc.remove_final_measurements(inplace=True)
                q2 = QuantumCircuit(qc.num_qubits)
                dropped = set()
                for ins in qc.data:
                    nm = ins.operation.name
                    if nm in ("measure", "reset", "barrier", "if_else"):
                        if nm != "barrier":
                            dropped.add(nm)
                        continue
                    q2.append(ins.operation, [qc.find_bit(q).index for q in ins.qubits])
                qc = q2
                flags = sorted(f"{d}_dropped" for d in dropped)
                norm, st = finalize(qc)
                r.update(ok=True, n_ops_raw=len(qc.data), flags=flags, ops_raw=dict(qc.count_ops()), **st)
                path = os.path.join(DATA, "cands", f"{rec['id'].replace('/', '_')}__{k}.qasm")
                open(path, "w").write(qasm2.dumps(norm))
                r["qasm"] = path
                open(path[:-5] + ".txt", "w").write(str(qc.draw("text", fold=160, idle_wires=False)))
                open(path[:-5] + ".tex", "w").write(src)
            except Exception as e:
                r.update(ok=False, reason=f"openqasm: {type(e).__name__}: {e}"[:200])
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            wrote = True
        if not wrote:
            fo.write(json.dumps({"id": rec["id"], "k": 0, "ok": False, "reason": "no env found"}) + "\n")
print("ok")
