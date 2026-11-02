import os, sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from tikz2qasm import *
from qiskit.quantum_info import Operator, SparsePauliOp
from scipy.linalg import expm
tex = r"""\begin{quantikz}
& \gate[3]{H^{\otimes 3}} & \gate{R_Z} & \gate[2]{\mathtt{Z}\mathtt{Z}(\theta)} & \gate[3]{\mathrm{MultiRZ}(\pi/3)} & \gate{\hat{R}_Y(x_1)} & \gate{R_x\!\big(\tfrac{\pi}{2}\big)}\\
& & \gate{R_Z} & & & & \\
& & & \gate{\ensuremath{R_z}(\pi)} & & &
\end{quantikz}"""
SIG_MORE = [3, 1, 1, 1, 2, 3, 1, 1]  # H^{(x)3} box, 3 rotations, ZZ, MultiRZ, R_Y, R_x
for kind, body, off in find_envs(tex):
    qc, fl = diagram_to_circuit(kind, body, {}); print(qc.draw(fold=200)); print(fl)
# multirz check
g = build("multirz", [0.7, 3]); Z=SparsePauliOp("ZZZ").to_matrix()
ok = np.allclose(Operator(g).data, expm(-1j*0.35*Z)); print("multirz exact", ok)
assert ok
assert [i.operation.num_qubits for i in qc.data] == SIG_MORE, [i.operation.num_qubits for i in qc.data]
