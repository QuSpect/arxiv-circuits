"""Consistency check of the published dataset.

Usage: python -I tools/check_dataset.py [DATASET_DIR]   (default: the parent of tools/)

Checks that
  * manifest.csv and manifest.jsonl hold the same rows, and every listed file exists in circuits/
    (and every file in circuits/ is listed);
  * every circuit parses with qiskit, uses only INPUT_GATES, has a single register and no
    classical bits;
  * n_qubits, n_2q, n_ccx, n_2q_ccx6 and depth recomputed from the QASM match the manifest;
  * url is https://arxiv.org/abs/<arxiv_id>;
  * the circuit also parses with quspect and pytket when they are installed.
Exits with status 1 on any failure.
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tikz2qasm import INPUT_GATES  # noqa: E402

from qiskit import QuantumCircuit  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
loaders = {}
try:
    from quspect.ir import qasm2_loads
    loaders["quspect"] = qasm2_loads
except ImportError:
    pass
try:
    from pytket.qasm import circuit_from_qasm_str
    loaders["pytket"] = circuit_from_qasm_str
except ImportError:
    pass

errors = []
rows = [json.loads(line) for line in open(os.path.join(D, "manifest.jsonl"), encoding="utf-8")]
with open(os.path.join(D, "manifest.csv"), newline="", encoding="utf-8") as f:
    crow = list(csv.DictReader(f))
if len(crow) != len(rows):
    errors.append(f"manifest.csv has {len(crow)} rows, manifest.jsonl {len(rows)}")
for a, b in zip(crow, rows):
    if list(a) != list(b) or any(a[k] != str(b[k]) for k in b):
        errors.append(f"csv/jsonl mismatch for {b['file']}")

listed = {r["file"] for r in rows}
present = {f for f in os.listdir(os.path.join(D, "circuits")) if f.endswith(".qasm")}
for f in sorted(present ^ listed):
    errors.append(f"{f}: {'not listed in manifest' if f in present else 'listed but missing'}")

ARXIV = re.compile(r"^\d{4}\.\d{4,5}v\d+$")
for r in rows:
    path = os.path.join(D, "circuits", r["file"])
    if not os.path.exists(path):
        continue
    src = open(path, encoding="utf-8").read()
    qc = QuantumCircuit.from_qasm_str(src)
    got = {
        "n_qubits": qc.num_qubits,
        "n_2q": sum(1 for i in qc.data if i.operation.num_qubits == 2),
        "n_ccx": qc.count_ops().get("ccx", 0),
        "depth": qc.depth(),
    }
    got["n_2q_ccx6"] = got["n_2q"] + 6 * got["n_ccx"]
    for k, v in got.items():
        if r[k] != v:
            errors.append(f"{r['file']}: {k} manifest={r[k]} recomputed={v}")
    extra = set(qc.count_ops()) - set(INPUT_GATES)
    if extra:
        errors.append(f"{r['file']}: gates outside INPUT_GATES {sorted(extra)}")
    if len(qc.qregs) != 1 or qc.num_clbits:
        errors.append(f"{r['file']}: expected one quantum register and no classical bits")
    if not r["file"].endswith(f"_{qc.num_qubits}.qasm"):
        errors.append(f"{r['file']}: file name does not end with the qubit count")
    if not ARXIV.match(r["arxiv_id"]) or r["url"] != f"https://arxiv.org/abs/{r['arxiv_id']}":
        errors.append(f"{r['file']}: bad arxiv_id/url {r['arxiv_id']} {r['url']}")
    for name, load in loaders.items():
        try:
            load(src)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{r['file']}: {name} failed to load: {e}")

print(f"{len(rows)} circuits, {len({r['arxiv_id'] for r in rows})} papers; "
      f"loaders checked: qiskit{''.join(', ' + n for n in loaders)}")
for e in errors:
    print("FAIL", e)
print("OK" if not errors else f"{len(errors)} problem(s)")
sys.exit(1 if errors else 0)
