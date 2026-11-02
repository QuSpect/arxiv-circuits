"""Re-convert one diagram of one paper, optionally with paper-given parameter values.

Usage: python -I convert_one.py SCRIPTS_DIR DATA_DIR ARXIV_ID K OUT.qasm ['{"\\\\theta_1": 1.9106}']
Prints the text drawing, gate counts and flags. Symbol keys are as reported in the
'symbolic_params' flag of cands.jsonl (e.g. "\\theta_1"). Values are floats in radians.
"""
import json, os, sys
sys.path.insert(0, sys.argv[1])
from tikz2qasm import collect_macros, diagram_to_circuit, finalize, find_envs, read_paper_tex, strip_comments
from qiskit import QuantumCircuit, qasm2, transpile
DATA, pid, k, out = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
preset = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
d = os.path.join(DATA, "src", pid.replace("/", "_"))
tex = read_paper_tex(d)
envs = list(find_envs(tex))
if k > len(envs):  # OpenQASM listing: reuse the stored normalized file
    raise SystemExit("k refers to an OpenQASM listing; use the cands/ file directly")
kind, body, _ = envs[k - 1]
qc, flags = diagram_to_circuit(kind, body, collect_macros(tex), preset)
print(qc.draw("text", fold=160, idle_wires=False))
norm, st = finalize(qc)
open(out, "w").write(qasm2.dumps(norm))
print(json.dumps({**st, "ops_raw": dict(qc.count_ops()), "flags": flags}))
