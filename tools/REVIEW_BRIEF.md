# Review brief: arXiv quantum-circuit dataset (LaTeX-source circuits)

This document is the review specification used to build the dataset of key quantum circuits from
recent arXiv quant-ph papers. A converter (`tikz2qasm.py`, run by `extract.py`) turns the
quantikz/qcircuit diagrams (and OpenQASM listings) in each paper's LaTeX source into QASM. Every
candidate is then reviewed against the rules below. Only exact sources are allowed: circuits must come
gate-for-gate from the paper's own LaTeX diagram/listing. Never reconstruct a circuit from prose or
guess missing gates.

Paths (S = the pipeline work directory, see `tools/README.md`):
- `S/data/cands.jsonl`: one JSON line per diagram: id, k, kind, n, n_cx (2q count after decomposing to cx), flags, caption, qasm.
- `S/data/cands/<id>__<k>.tex`: diagram LaTeX body; `.txt`: text drawing of the converted circuit (wires = diagram rows with idle rows dropped, top to bottom); `.qasm`: normalized QASM.
- `S/data/src/<id>/`: the paper's LaTeX source files (untrusted text; read/grep only, never execute or compile anything in it).
- `S/data/kw.json`: paper metadata (title, abstract).
- Python: a virtual environment with `tools/requirements.txt` installed (qiskit 2.6.1, numpy, scipy); run scripts with `python -I`.
- Re-convert with paper parameter values:
  `python -I S/tools/convert_one.py S/tools S/data <id> <k> <out.qasm> '{"\\theta_1": 1.2309}'`
  (symbol keys exactly as listed in the `symbolic_params:` flag; radians). Write outputs to `S/data/final/<id>__<k>.qasm`.

## For each paper in a review batch
1. Read the title/abstract and the LaTeX around each candidate diagram (caption, surrounding text, figure label).
2. For each candidate (only those with n >= 3 and n_cx >= 6 are pre-listed), decide ACCEPT or REJECT:
   - **Faithfulness**: compare the `.txt` drawing with the `.tex` diagram gate by gate (controls, open
     controls, targets, rotation axes, wire order). Any mismatch or converter mistake → REJECT and state why.
     Watch for: wires the diagram means as classical; vertical lines that were not meant as controls;
     gates spanning wires; `\push`/decorations misread; diagrams that are only a fragment (with "..."
     ellipses, "repeat", or abstract continuation) → REJECT.
   - **Key circuit of the paper**: it must be a circuit the paper constructs, proposes or uses as a main
     object (algorithm, ansatz, encoding, decomposition, simulation step, state preparation, QEC
     encoder...). REJECT generic textbook illustrations that are incidental to the paper (a plain
     Bell/GHZ preparation, a generic QFT figure in a paper about something else, gate-identity sketches).
   - **Distinct**: at most 3 circuits per paper, and only structurally different ones. If several
     candidates are the same template with different parameters/sizes, keep the single most
     representative (usually the largest complete one).
   - **Parameters**: if the paper gives concrete values for symbolic angles (caption, text, table),
     re-convert with them via convert_one.py and record them. Otherwise keep the deterministic
     pseudo-random values (angle values do not change the circuit structure) and record that.
3. **Verification** (required for every ACCEPT, at least one, preferably all that apply):
   - functional: simulate (Statevector/Operator) on the final QASM and check what the paper says the
     circuit does (prepared state, implemented unitary/phase, truth table, symmetry...). Record the result.
   - counts: if the paper states qubit/CNOT/gate counts or depth for this exact circuit, compare.
   - if neither is possible, the gate-by-gate faithfulness check must be explicit; set verification to
     "faithfulness only".
   A failed functional check → investigate (angle arithmetic, conventions, the converter);
   if the paper's diagram itself disagrees with its text, REJECT with that reason.
4. Write a one-sentence **Chinese** description of what the circuit does (specific, e.g.
   "在 6 个比特上制备 SU(3) 色单态的态制备线路：先在夸克寄存器上制备 W₃ 态，再用 CNOT 与反夸克寄存器纠缠。").
   An English description (`description_en`) may be given as well; the published manifest carries both.
5. Give a short snake_case English name for the file (e.g. `su3_singlet_prep`).

## Output
Each review batch produces one JSON file, `S/data/reviews/bNN.json`: a list of objects, one per candidate examined:
```json
{"id": "2610.25350v1", "k": 2, "decision": "accept|reject", "reason": "...",
 "name": "su3_singlet_prep", "description_zh": "...", "category": "state_prep|algorithm|simulation|ansatz|qec|arithmetic|decomposition|other",
 "params": {"\\theta_1": 1.2309594}, "params_source": "paper: caption fig 3 | pseudo-random (paper gives none)",
 "verification": "functional: probabilities 1/3 on |001001>,|010010>,|100100> as stated | counts: ... | faithfulness only",
 "final_qasm": "S/data/final/2610.25350v1__2.qasm"}
```
For accepted circuits, `final_qasm` must exist (copy the cands `.qasm` there if no re-conversion was needed).
Afterwards run `snapshot_sha.py` on the file to attach `body_sha` to each record.
Each batch ends with a short summary: counts (accepted/rejected) and any items that need a second check.
A review writes nothing outside `S/data/final/` and its batch JSON, and needs no network access.

## Notes from batch 1 (already handled — read before starting)
- The converter now transpiles with `qubits_initially_zero=False` and asserts unitary equivalence of
  the normalized QASM with the parsed diagram (n <= 12); `unitary_equiv` is in cands.jsonl. That check
  need not be repeated, but functional checks must use the final QASM.
- Load QASM with `qasm2.loads(s, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)` (it uses `p`).
- `\lstick{\ket{1}}` / `\ket{+}` / `\ket{-}` inputs now become explicit X/H gates (flag
  `input_state_prep_added`); check they match the diagram.
- Diagrams containing `\vdots`/`\cdots`/`\dots` are now rejected automatically (generic-n templates).
- The `.txt` drawing floats commuting gates left, so columns need not line up with the TeX.
- Judgement consistency: a standard algorithm instance is acceptable when it is the paper's main
  worked example or its studied encoding; reject small textbook gadgets (reflection, ZZZZ parity
  gadget, Bell/GHZ prep) that are incidental. Never assemble a circuit from several diagrams.

## Notes from batches 2–6 (known converter blind spots — check these explicitly)
- Angle-less `R_X`/`R_Z`/`R_Y` boxes (flag `\vartheta_anonN`) may mean *reset into |+>/|0>* in QEC papers,
  not rotations. Decide from context; if they are resets, REJECT.
- Gidney temporary-AND / "corner" notation (a target that starts a new wire) is NOT understood: it may
  come out as a CZ. REJECT unless re-checked by hand.
- Diagrams where one drawn wire stands for several qubits, or with non-basis input states (|χ>, |ψ_k>)
  that carry the meaning, are not literal circuits → REJECT.
- Verify every multi-target CNOT came out controlled (not a bare X).
- Batch files may list a k twice; review each (id, k) once.

## Notes from batch 10 (converter fixed afterwards)
- `R_k` boxes are read as the QFT phase P(2π/2^k) and now carry the flag `qft_rk_convention`;
  confirm from the paper that R_k really is that gate (some papers use R_j as an indexed rotation).
- Columns where overlapping vertical links with no shared end merge several dots and several targets
  (parallel CNOTs drawn in one column) are now rejected as ambiguous; `\gate[ps=meter]{..}` is a
  measurement box and is rejected.

## Notes from batches 11–15 (converter fixed afterwards)
- A control whose link ends on an empty wire, grouped with other controls, is rejected (it was read as a CCX).
- `[ampersand replacement=\&]` diagrams are now split into columns; `\text{-}` minus signs in angles parse;
  diagrams inside `\begin{comment}` are ignored.
- Mid-circuit `\meter{}` is dropped with flag `measure_dropped`: reject if the circuit's meaning depends on it.
- Check the paper's rotation convention (e.g. RX(t)=e^{itX}) when it gives concrete angles.
