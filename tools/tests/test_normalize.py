"""normalize_qasm is the identity on the published circuits (they are already normalized), and it
translates gates outside INPUT_GATES while dropping final measurements and barriers.
Usage: python -I test_normalize.py [SCRIPTS_DIR]"""
import glob
import os
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tikz2qasm import INPUT_GATES, normalize_qasm  # noqa: E402

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = sorted(glob.glob(os.path.join(root, "circuits", "*.qasm")))
for f in files:
    src = open(f).read()
    assert normalize_qasm(src) == src, f
print(f"normalize_qasm is the identity on {len(files)} published circuits")

src = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\nch q[0],q[1];\nrxx(0.3) q[1],q[2];\nbarrier q;\nmeasure q -> c;\n'
out = normalize_qasm(src)
qc = QuantumCircuit.from_qasm_str(out)
assert set(qc.count_ops()) <= set(INPUT_GATES) and qc.num_clbits == 0, out
ref = QuantumCircuit.from_qasm_str(src)
ref.remove_final_measurements(inplace=True)
ref.data = [i for i in ref.data if i.operation.name != "barrier"]
assert Operator(qc).equiv(Operator(ref))
try:
    normalize_qasm('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\nmeasure q[0] -> c[0];\nx q[0];\n')
    raise SystemExit("FAIL: mid-circuit measurement accepted")
except ValueError:
    pass
print("translation, measurement/barrier removal ok")
