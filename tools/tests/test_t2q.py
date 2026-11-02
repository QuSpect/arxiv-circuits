import os, sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tikz2qasm import *
tex = r"""
\begin{quantikz}
\lstick{$\ket{0}$} & \gate{H} & \ctrl{2} & \qw & \ctrl{1} & \gate{R_z(\pi/4)} & \meter{} \\
\lstick{$\ket{0}$} & \qw & \targ{} & \ctrl{1} & \control{} & \gate[2]{R_{zz}(\theta)} & \qw\\
\lstick{$\ket{0}$} & \qw & \targ{} & \targ{} & \octrl{-1} & & \swap{1}\\
& \gate{T^\dagger} & \qw & \qw & \gate{X} & \qw & \targX{}
\end{quantikz}
\Qcircuit @C=1em @R=.7em {
& \gate{H} & \ctrl{1} & \qw & \multigate{1}{U} \\
& \qw & \targ & \qw & \ghost{U}
}
"""
res = []
for kind, body, off in find_envs(tex):
    try:
        qc, fl = diagram_to_circuit(kind, body, {})
        print(kind, fl); print(qc.draw(fold=200))
        res.append((kind, qc.num_qubits, fl))
    except Abstract as e:
        print(kind, "ABSTRACT", e)
        res.append((kind, "abstract"))
assert res[0][:2] == ("quantikz", 4) and "measure_dropped" in res[0][2], res
assert res[1] == ("qcircuit", "abstract"), res
