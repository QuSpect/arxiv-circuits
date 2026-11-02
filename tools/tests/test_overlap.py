"""Regression: interleaved parallel CNOTs in one column are rejected; chained dots onto one target are not.
Usage: python -I test_overlap.py [SCRIPTS_DIR]"""
import os, sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tikz2qasm import Abstract, diagram_to_circuit  # noqa: E402

par = r"\ctrl{2} & \qw \\ \ctrl{2} & \qw \\ \targ{} & \qw \\ \targ{} & \qw"
try:
    diagram_to_circuit("quantikz", par, {})
    raise SystemExit("FAIL: interleaved CNOTs converted")
except Abstract as e:
    print("interleaved rejected:", e)
chain = r"\octrl{2} \\ \octrl{2} \\ \octrl{2} \\ \octrl{1} \\ \targ{} \\ \qw"
qc, _ = diagram_to_circuit("quantikz", chain, {})
assert qc.num_qubits == 5 and sum(1 for i in qc.data if i.operation.num_qubits == 5) == 1, qc
print("chained 4-control NOT ok")
try:
    diagram_to_circuit("quantikz", r"\ctrl{1} & \gate[ps=meter]{Z} \\ \targ{} & \qw", {})
    raise SystemExit("FAIL: meter box converted")
except Abstract as e:
    print("meter box rejected:", e)
try:  # y1 -> y3 and y2 -> (nothing on y4): two distance-2 CNOTs with one target missing
    diagram_to_circuit("quantikz", r"\ctrl{2} \\ \ctrl{2} \\ \targ{} \\ \qw", {})
    raise SystemExit("FAIL: link onto empty wire converted")
except Abstract as e:
    print("link onto empty wire rejected:", e)
from tikz2qasm import find_envs, parse_angle  # noqa: E402
assert abs(parse_angle(r"\text{-}\tfrac{\pi}{4}", {}) + 0.7853981633974483) < 1e-12
envs = list(find_envs(r"\begin{quantikz}[ampersand replacement=\&] \gate{H} \& \ctrl{1} \\ \gate{H} \& \targ{} \end{quantikz}"))
qc, _ = diagram_to_circuit(*envs[0][:2], {})
assert dict(qc.count_ops()) == {"h": 2, "cx": 1}, qc.count_ops()
print("text-minus angle and ampersand replacement ok")
