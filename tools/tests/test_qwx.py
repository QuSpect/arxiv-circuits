import os, sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tikz2qasm import *
tex = r"""\Qcircuit @C=1em @R=.7em {
& \ctrl{1} & \qw \\
& \targ \qwx[1] & \qw \\
& \targ & \gate{H} \qw
}"""
for kind, body, off in find_envs(tex):
    qc, fl = diagram_to_circuit(kind, body, {}); print(qc.draw())
    assert dict(qc.count_ops()) == {"cx": 2, "h": 1}, qc.count_ops()
