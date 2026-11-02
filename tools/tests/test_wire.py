import os, sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tikz2qasm import *
tex = r"""\begin{quantikz}
& \gate{H} & \qw \\
& \octrl{1}\wire[u]{q} & \qw \\
& \ctrl{0} & \ctrl[open]{-2}\wire[d][1]{q} & \\
& & \targ{}
\end{quantikz}"""
# open control on wire 1 + control on wire 2 -> H on wire 0; open control on wire 2 -> X on wire 3
SIG_WIRE = [('x', [1]), ('ch', [1, 2, 0]), ('x', [1]), ('x', [2]), ('cx', [2, 3]), ('x', [2])]
for kind, body, off in find_envs(tex):
    qc, fl = diagram_to_circuit(kind, body, {}); print(qc.draw())
    assert [(i.operation.name if i.operation.num_qubits < 3 else "c" + i.operation.base_gate.name, [qc.find_bit(q).index for q in i.qubits]) for i in qc.data] == SIG_WIRE
