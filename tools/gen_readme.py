"""Regenerate the circuit tables in README.md (English descriptions) and README_CN.md (Chinese
descriptions) from manifest.jsonl. Only the text between the table markers is replaced.

Usage: python -I gen_readme.py DATASET_DIR
"""
import json
import re
import sys
from pathlib import Path

d = Path(sys.argv[1])
rows = [json.loads(line) for line in open(d / "manifest.jsonl", encoding="utf-8")]
START, END = "<!-- circuits-table:start -->", "<!-- circuits-table:end -->"


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def table(header: str, desc_key: str) -> str:
    lines = [header, "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| `{r['file']}` | [{r['arxiv_id']}]({r['url']}) | {esc(r['title'])} | {esc(r[desc_key])} "
            f"| {r['n_qubits']} | {r['n_2q']} | {r['n_ccx']} | {r['depth']} |")
    return "\n".join(lines)


targets = {
    "README.md": table("| File | arXiv | Paper title | Description | Qubits | 2q | ccx | Depth |", "description_en"),
    "README_CN.md": table("| 文件 | arXiv | 论文题目 | 描述 | 比特 | 2q | ccx | 深度 |", "description_zh"),
}
for name, tab in targets.items():
    p = d / name
    text = p.read_text(encoding="utf-8")
    new, n = re.subn(re.escape(START) + r".*?" + re.escape(END), lambda _m: f"{START}\n{tab}\n{END}", text, flags=re.S)
    if n != 1:
        raise SystemExit(f"{p}: table markers not found exactly once")
    p.write_text(new, encoding="utf-8")
    print("wrote", p, len(rows), "rows")
