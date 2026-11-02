# Extraction pipeline

The scripts that built this dataset: they download arXiv metadata and LaTeX sources, convert the
quantikz / qcircuit diagrams into OpenQASM 2.0, organise the per-candidate review, and assemble the
published files (`circuits/`, `manifest.csv`, `manifest.jsonl`, `review_log.jsonl`).

The code in this directory is released under the MIT License (see [`LICENSE`](LICENSE)); the data
in the rest of the repository is under CC BY 4.0.

## Requirements

- Python 3.10 or newer (tested with 3.13)
- `pip install -r tools/requirements.txt` (qiskit 2.6.1, numpy, scipy)
- optional: `quspect` and/or `pytket`; when installed, `build_dataset.py` and `check_dataset.py` also
  check that every circuit loads with them

qiskit is pinned because the published QASM text is produced by qiskit's transpiler and QASM
exporter; another version may emit different (but equivalent) text.

All scripts are meant to be run with `python -I` (isolated mode). Scripts that import `tikz2qasm`
take the tools directory as their first argument.

## Files

| File | Purpose |
|---|---|
| `tikz2qasm.py` | Converter: parses quantikz / qcircuit diagram bodies into qiskit circuits. Rejects anything abstract (named boxes, ellipses, bundles, meter boxes, ambiguous links); drops measurements; turns `\|1⟩`/`\|+⟩`/`\|−⟩` input labels into X/H; assigns deterministic pseudo-random values to symbolic angles. `finalize` translates to the published gate set without borrowing idle wires as ancillas and asserts unitary equivalence with the parsed diagram (n ≤ 12). Also defines `INPUT_GATES` and `normalize_qasm`. |
| `fetch_meta.py` | arXiv API: metadata of quant-ph papers (primary or cross-list) in a submission-date range. |
| `fetch_src.py` | Downloads e-print sources (≈1 request / 3 s), keeps only text members, never executes anything; indexes which files contain circuit markup. |
| `extract.py` | Runs the converter over every downloaded source with circuit markup (and parses embedded OpenQASM 2.0 listings); writes candidates and the reason for every rejection. |
| `convert_one.py` | Re-converts one diagram, optionally with angle values given in the paper. |
| `make_batches.py` | Splits not-yet-reviewed candidates (≥ 3 qubits, ≥ 6 CX) into review batches; reports accepted circuits whose diagram changed. |
| `REVIEW_BRIEF.md` | The review specification applied to every candidate. |
| `snapshot_sha.py` | Attaches the hash of the reviewed diagram body (`body_sha`) to review records. |
| `funnel.py` | Selection-funnel statistics. |
| `build_dataset.py` | Re-converts every accepted diagram from the paper source, checks it against the reviewed QASM, normalizes, checks loading, and writes the dataset files. |
| `gen_readme.py` | Regenerates the circuit tables in `README.md` / `README_CN.md` from the manifest. |
| `check_dataset.py` | Consistency check of the published files (see below). |
| `tests/` | Converter regression tests; `tests/run_all.py` runs them all. |

## Checking the published dataset

```bash
python -I tools/check_dataset.py      # manifest vs. QASM statistics, gate set, links, loading
python -I tools/tests/run_all.py      # converter and normalizer tests
```

## Re-running the pipeline

The downloaded sources are not redistributed; a re-run fetches them from arXiv. The work directory
layout is `W/data/{meta.json, kw.json, src/, src_index.jsonl, cands/, cands.jsonl, batches/, reviews/, final/}`.

```bash
T=tools; W=work
mkdir -p $W/data/batches $W/data/reviews $W/data/final
python -I $T/fetch_meta.py $W/data/meta.json 202608280000 202610282359   # one call per date range
# keyword pre-filter: write the selected records of meta.json (same format) to $W/data/kw.json
python -I $T/fetch_src.py $W/data kw.json
python -I $T/extract.py $T $W/data                 # -> cands.jsonl, cands/<id>__<k>.{tex,txt,qasm}
python -I $T/make_batches.py $W/data 0 4           # -> batches/b00.json ... b03.json
# review each batch according to REVIEW_BRIEF.md -> $W/data/reviews/bNN.json, then:
python -I $T/snapshot_sha.py $W/data $W/data/reviews/bNN.json
python -I $T/funnel.py $W/data $W/funnel.json
python -I $T/build_dataset.py $T $W/data . --write # writes circuits/, manifest.*, review_log.jsonl
python -I $T/gen_readme.py .
python -I $T/check_dataset.py
```

Notes:

- The keyword pre-filter (terms such as circuit, qubit, gate, algorithm in the title or abstract) is
  a simple selection over `meta.json` and is not shipped as a script; any subset of `meta.json`
  records can be used as `kw.json`.
- `build_dataset.py` accepts review records whose `final_qasm` path starts with `S/`, resolved
  relative to the parent of the data directory (`W/`).
- `description_en` is taken from the review record if present, otherwise carried over from the
  existing `manifest.jsonl`.
- With the original work directory, `build_dataset.py` reproduces the published `circuits/`,
  `manifest.csv`, `manifest.jsonl` and `review_log.jsonl` byte for byte.
