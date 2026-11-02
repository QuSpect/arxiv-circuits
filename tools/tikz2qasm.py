"""Convert quantikz / qcircuit LaTeX circuit diagrams to qiskit circuits.

Only concrete gates are accepted; any abstract box (U, QFT, W, ...) or unknown
macro makes the whole diagram 'abstract' and it is rejected. Measurements are
dropped (unitary part kept); classically-controlled operations are dropped and
flagged. Symbolic angles get deterministic pseudo-random values (flagged).
"""
from __future__ import annotations

import hashlib
import math
import re

# ---------------------------------------------------------------- tokenizing


def read_paper_tex(d: str) -> str:
    """Concatenate a paper's .tex files (comments stripped, text after \\end{document} dropped)."""
    import os
    out = ""
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith(".tex"):
            t = strip_comments(open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
            t = re.sub(r"\\begin\{comment\}.*?\\end\{comment\}", "", t, flags=re.S)
            e = t.find("\\end{document}")
            out += "\n" + (t[:e] if e >= 0 else t)
    return out


def strip_comments(t: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", t)


def read_group(t: str, i: int, op: str, cl: str):
    """t[i] == op; return (content, index after closing)."""
    depth, j = 0, i
    while j < len(t):
        c = t[j]
        if c == "\\":
            j += 2
            continue
        if c == op:
            depth += 1
        elif c == cl:
            depth -= 1
            if depth == 0:
                return t[i + 1 : j], j + 1
        j += 1
    raise ValueError("unbalanced")


def split_top(t: str, sep: str) -> list[str]:
    """Split at sep (either '&' or '\\\\') at brace depth 0."""
    out, depth, cur, i = [], 0, [], 0
    while i < len(t):
        c = t[i]
        if sep == "\\\\" and t.startswith("\\\\", i) and depth == 0:
            out.append("".join(cur))
            cur = []
            i += 2
            # optional [spacing]
            m = re.match(r"\s*\[[^\]]*\]", t[i:])
            if m:
                i += m.end()
            continue
        if c == "\\" and i + 1 < len(t):
            cur.append(t[i : i + 2])
            i += 2
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        if c == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out


def find_envs(tex: str):
    """Yield (kind, body, start_offset)."""
    for m in re.finditer(r"\\begin\{quantikz\}", tex):
        i = m.end()
        # optional [opts]
        while i < len(tex) and tex[i] in " \n\t":
            i += 1
        opts = ""
        if i < len(tex) and tex[i] == "[":
            opts, i = read_group(tex, i, "[", "]")
        e = tex.find("\\end{quantikz}", i)
        if e > 0:
            body = tex[i:e]
            if "ampersand replacement" in opts:  # [ampersand replacement=\&]: \& separates columns
                body = body.replace("\\&", "&")
            yield "quantikz", body, m.start()
    for m in re.finditer(r"\\Qcircuit", tex):
        i = tex.find("{", m.end())
        if i < 0:
            continue
        try:
            body, _ = read_group(tex, i, "{", "}")
        except ValueError:
            continue
        yield "qcircuit", body, m.start()


def parse_cell(cell: str):
    """Return list of (cmd, opt, args) in a cell."""
    out, i = [], 0
    while i < len(cell):
        if cell[i] != "\\":
            i += 1
            continue
        m = re.match(r"\\([A-Za-z]+)\*?", cell[i:])
        if not m:
            i += 2
            continue
        cmd = m.group(1)
        i += m.end()
        opt, args = None, []
        nmax = ARITY.get(cmd, 0)
        while True:
            j = i
            while j < len(cell) and cell[j] in " \t\n":
                j += 1
            if j < len(cell) and cell[j] == "[" and not args:
                o2, i = read_group(cell, j, "[", "]")
                opt = o2 if opt is None else opt + "|" + o2  # e.g. \wire[d][2]{q}
                continue
            if j < len(cell) and cell[j] == "{" and len(args) < nmax:
                a, i = read_group(cell, j, "{", "}")
                args.append(a)
                continue
            break
        out.append((cmd, opt, args))
    return out


ARITY = {
    "gate": 1, "ctrl": 1, "octrl": 1, "ctrlo": 1, "targ": 1, "control": 1, "ocontrol": 1,
    "controlo": 1, "swap": 1, "targX": 1, "meter": 1, "meterD": 1, "measure": 1, "phase": 1,
    "lstick": 1, "rstick": 1, "slice": 1, "gategroup": 1, "push": 1, "ghost": 1, "multigate": 2,
    "sgate": 2, "midstick": 1, "setwiretype": 1, "wireoverride": 1, "qwbundle": 1, "ket": 1,
    "bra": 1, "wire": 2, "cwbend": 1, "vcw": 1, "vqw": 1, "qwx": 0, "cwx": 0, "trash": 1,
    "ground": 1, "inputD": 1, "push": 1, "measuretab": 1, "metercw": 1, "dmeter": 1,
}
IGNORE = {
    "qw", "lstick", "rstick", "slice", "gategroup", "push", "ghost", "midstick", "wireoverride",
    "ket", "bra", "wire", "nghost", "hphantom", "vphantom", "phantom", "quad", "qquad",
    "rangle", "langle", "rvert", "lvert", "ghostwire", "barrier", "pgfmatrixnextcell", "ifthenelse",
    "hspace", "vspace", "text", "textrm", "mathrm", "scriptsize", "small", "tiny",
    "footnotesize", "label", "linethrough", "trash", "ground", "inputD", "setwiretype", "rule",
    "dots", "cdots", "ldots", "vdots", "ddots", "alpha", "beta", "gamma", "psi", "phi", "theta",
    "dag", "dagger", "uparrow", "downarrow", "otimes", "mathcal", "boldsymbol", "bf", "it",
    "relax", "strut", "colorbox", "color", "textcolor", "gateoutput", "gateinput", "plus", "minus",
}
MEAS = {"meter", "meterD", "measure", "measuretab", "metercw", "dmeter", "measureD"}
CLASSICAL = {"cw", "cwbend", "vcw", "cwx", "cctrl"}

# ---------------------------------------------------------------- gate names


def _norm(s: str) -> str:
    s = s.replace("$", "")
    s = re.sub(r"\\(mathrm|text|textrm|mathsf|mathbf|mathit|textsf|textsc|operatorname|rm|bf|texttt|mathtt|ensuremath|hat|big|Big|bigl|bigr|Bigl|Bigr)(?![A-Za-z])", "", s)
    s = re.sub(r"\\[,;:! ]", "", s)
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\s+", "", s)
    s = s.replace("{", "").replace("}", "")
    return s


GREEK = ("alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|"
         "rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Phi|Psi|Omega")


def _arg(t: str, i: int):
    while i < len(t) and t[i] == " ":
        i += 1
    if i < len(t) and t[i] == "{":
        return read_group(t, i, "{", "}")
    m = re.match(r"\\[A-Za-z]+|.", t[i:])
    return m.group(0), i + m.end()


def _expand_frac(e: str) -> str:
    for _ in range(10):
        m = re.search(r"\\[dt]?frac(?![A-Za-z])", e)
        if not m:
            return e
        a, j = _arg(e, m.end())
        b, j = _arg(e, j)
        e = e[: m.start()] + "((" + _expand_frac(a) + ")/(" + _expand_frac(b) + "))" + e[j:]
    return e


def parse_angle(expr: str, symbols: dict) -> float:
    e = expr.replace("$", "").replace("\u2212", "-")
    e = re.sub(r"\\(?:text|mathrm)\{\s*([-+])\s*\}", r"\1", e)  # \text{-} used as a minus sign
    e = re.sub(r"\\(left|right|mathrm|text|boldsymbol|vec|mathbf|bm|hat|tilde|bar|mathit|big|Big|bigl|bigr|Bigl|Bigr)(?![A-Za-z])", "", e)
    e = re.sub(r"\\[,;:! ]", "", e)
    e = _expand_frac(e)
    e = re.sub(r"\{(\\[A-Za-z]+|[A-Za-z])\}", r"\1", e)
    e = e.replace("\\pi", "pi").replace("π", "pi").replace("{", "(").replace("}", ")")
    e = e.replace("\\cdot", "*").replace("\\times", "*")
    e = re.sub(r"\s+", "", e)
    e = e.replace("^", "**")
    if re.fullmatch(r"[0-9.+\-*/()pi]*", e) and e:
        e2 = re.sub(r"(\d)(pi|\()", r"\1*\2", e)
        e2 = re.sub(r"\)(\d|pi|\()", r")*\1", e2)
        e2 = re.sub(r"pi(\d|\()", r"pi*\1", e2)
        return float(eval(e2, {"__builtins__": {}}, {"pi": math.pi}))  # noqa: S307 restricted charset
    # symbolic: each symbol (greek letter / single latin letter, with optional subscript)
    # gets one deterministic value; the expression is then evaluated arithmetically
    sym = re.compile(r"(\\(?:" + GREEK + r")(?![A-Za-z])|(?<![A-Za-z\\])[A-Za-z](?![A-Za-z]))('*)(_\([^()]*\)|_[A-Za-z0-9+\-])?('*)(\^\(?[A-Za-z0-9]+\)?)?")
    e = e.replace("pi", "#")
    parts, pos = [], 0
    for m in sym.finditer(e):
        parts.append(e[pos:m.start()])
        base = (m.group(1) + m.group(2) + (m.group(3) or "") + m.group(4)).replace("(", "").replace(")", "")
        if base not in symbols:
            h = int(hashlib.sha256(base.encode()).hexdigest()[:8], 16)
            symbols[base] = round((h / 0xFFFFFFFF) * 2 * math.pi - math.pi, 6)
        val = f"({symbols[base]})"
        if m.group(5):
            val = f"({val}**{m.group(5)[1:].strip('()')})"
        parts.append(val)
        pos = m.end()
    parts.append(e[pos:])
    e3 = "".join(parts).replace("#", "pi")
    if not re.fullmatch(r"[0-9.+\-*/()pi]*", e3.replace("**", "*")) or not e3:
        raise Abstract(f"angle '{expr}'")
    e3 = re.sub(r"(\d|\))\s*(\(|pi)", r"\1*\2", e3)
    e3 = re.sub(r"pi\s*(\d|\()", r"pi*\1", e3)
    try:
        return float(eval(e3, {"__builtins__": {}}, {"pi": math.pi}))  # noqa: S307 restricted charset
    except Exception:
        raise Abstract(f"angle '{expr}'")


ROT = re.compile(r"^(R|r)_?([xyzXYZ])\((.*)\)$")
ROT2 = re.compile(r"^(R|r)_?(xx|yy|zz|XX|YY|ZZ|zx|ZX)\((.*)\)$")
PH = re.compile(r"^(P|U_?1|R_?\\phi|Phase|U_?\\phi)\((.*)\)$")
RK = re.compile(r"^R_?(\d+)$")


_ANON = [0]


def _next_anon() -> int:
    """Per-diagram counter for rotations drawn without an angle (reset in diagram_to_circuit)."""
    _ANON[0] += 1
    return _ANON[0] - 1


def map_1q(name: str, symbols: dict):
    """Return ('name', params) for a known single-qubit gate, or None."""
    raw = name
    n = _norm(name)
    m = re.fullmatch(r"(.+?)\^(\d)", n) or re.fullmatch(r"\((.+)\)\^(\d)", n)
    if m and not re.fullmatch(r"[XYZ]", m.group(1)):
        inner = re.sub(r"\^\{?\d\}?\s*$", "", raw.strip().strip("$"))
        g = map_1q(inner, symbols)
        if g is not None:
            return "pow", [g, int(m.group(2))]
    table = {
        "H": "h", "X": "x", "Y": "y", "Z": "z", "S": "s", "T": "t", "I": "id", "\\mathbb1": "id",
        "1": "id", "Id": "id", "NOT": "x", "\\sigma_x": "x", "\\sigma_z": "z", "\\sigma_y": "y",
        "SX": "sx", "\\sqrtX": "sx", "\\sqrt{X}": "sx", "X^1/2": "sx", "X^\\frac12": "sx",
        "\\sqrtX^\\dagger": "sxdg",
    }
    if n in table:
        return table[n], []
    m = re.fullmatch(r"(S|T|\\sqrtX|SX)(\^\\dagger|\^\\dag|\^†|\^\*|\^-1|\^\\ast|\\dagger|\\dag|†)", n)
    if m:
        return {"S": "sdg", "T": "tdg", "\\sqrtX": "sxdg", "SX": "sxdg"}[m.group(1)], []
    m = ROT.match(n)
    if m:
        return "r" + m.group(2).lower(), [parse_angle(_inner(raw), symbols)]
    m = re.fullmatch(r"R_?([xyzXYZ])", n)
    if m:  # rotation drawn without its angle: fresh pseudo-random angle per occurrence
        return "r" + m.group(1).lower(), [parse_angle(f"\\vartheta_{{anon{_next_anon()}}}", symbols)]
    m = re.fullmatch(r"(R|r)_?([xyzXYZ])\^?\(?(.*?)\)?", n)
    if m and m.group(3) and not ROT.match(n):
        pass
    m = PH.match(n)
    if m:
        return "p", [parse_angle(_inner(raw), symbols)]
    m = RK.match(n)
    if m:  # QFT R_k = P(2pi/2^k)
        return "p", [2 * math.pi / 2 ** int(m.group(1))]
    m = re.fullmatch(r"([XYZ])\^(.+)", n)
    if m:  # X^t = up to global phase R_x(pi t)
        try:
            t = parse_angle(m.group(2), {})
        except Exception:
            return None
        if re.search(r"[A-Za-z]", m.group(2).replace("pi", "")):
            return None
        return "pow_exact", [m.group(1).lower(), t]
    return None


def map_2q(name: str, symbols: dict):
    n = _norm(name)
    m = ROT2.match(n) or re.fullmatch(r"()(XX|YY|ZZ)\((.*)\)", n)
    if m:
        return "r" + m.group(2).lower(), [parse_angle(_inner(name), symbols)]
    m = re.fullmatch(r"R_?(xx|yy|zz|XX|YY|ZZ)", n)
    if m:
        return "r" + m.group(1).lower(), [parse_angle(f"\\vartheta_{{anon{_next_anon()}}}", symbols)]
    if n in {"SWAP", "\\mathrmSWAP", "Swap"}:
        return "swap", []
    m = re.fullmatch(r"(fSim|FSim|fsim)\((.*)\)", n)
    if m:
        a = split_top(_inner(name), ",")
        if len(a) == 2:
            return "fsim", [parse_angle(a[0], symbols), parse_angle(a[1], symbols)]
    if n in {"iSWAP"}:
        return "iswap", []
    if n in {"CZ", "CNOT", "CX"}:
        return {"CZ": "cz", "CNOT": "cx", "CX": "cx"}[n], []
    return None


def _inner(raw: str) -> str:
    i, j = raw.find("("), raw.rfind(")")
    return raw[i + 1 : j] if 0 <= i < j else raw


def build(nm, ps):
    """Exact qiskit gate for a mapped name (global phases kept, so controlled versions are right)."""
    from qiskit import QuantumCircuit
    from qiskit.circuit import library as L
    simple = {"x": L.XGate, "y": L.YGate, "z": L.ZGate, "h": L.HGate, "s": L.SGate, "sdg": L.SdgGate,
              "t": L.TGate, "tdg": L.TdgGate, "sx": L.SXGate, "sxdg": L.SXdgGate, "rx": L.RXGate,
              "ry": L.RYGate, "rz": L.RZGate, "p": L.PhaseGate, "swap": L.SwapGate,
              "rxx": L.RXXGate, "ryy": L.RYYGate, "rzz": L.RZZGate, "iswap": L.iSwapGate,
              "rzx": L.RZXGate, "cz": L.CZGate, "cx": L.CXGate}
    if nm in simple:
        return simple[nm](*ps)
    if nm == "pow":
        g, k = ps
        base = build(*g)
        qc = QuantumCircuit(base.num_qubits)
        for _ in range(k):
            qc.append(base, range(base.num_qubits))
        return qc.to_gate(label=f"{base.name}^{k}")
    if nm == "pow_exact":  # P^t = exp(i*pi*t/2) * R_P(pi*t) for P in {X,Y,Z}
        axis, t = ps
        qc = QuantumCircuit(1, global_phase=math.pi * t / 2)
        getattr(qc, "r" + axis)(math.pi * t, 0)
        return qc.to_gate(label=f"{axis.upper()}^{t:g}")
    if nm == "tensor":  # same 1q gate on every wire of the box
        g, span = ps
        qc = QuantumCircuit(span)
        for q in range(span):
            qc.append(build(*g), [q])
        return qc.to_gate(label="tensor")
    if nm == "multirz":  # exp(-i theta/2 Z...Z)
        theta, span = ps
        qc = QuantumCircuit(span)
        for q in range(span - 1):
            qc.cx(q, q + 1)
        qc.rz(theta, span - 1)
        for q in reversed(range(span - 1)):
            qc.cx(q, q + 1)
        return qc.to_gate(label="MultiRZ")
    if nm == "fsim":  # [[1,0,0,0],[0,c,-is,0],[0,-is,c,0],[0,0,0,e^{-i phi}]]
        theta, phi = ps
        qc = QuantumCircuit(2)
        qc.append(L.XXPlusYYGate(2 * theta), [0, 1])
        qc.cp(-phi, 0, 1)
        return qc.to_gate(label="fSim")
    raise Abstract(f"no builder for {nm}")


# ---------------------------------------------------------------- diagram


class Abstract(Exception):
    pass


def diagram_to_circuit(kind: str, body: str, macros: dict, preset: dict | None = None):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import (XGate, YGate, ZGate, HGate, SGate, SdgGate, TGate,
                                        TdgGate, SXGate, SXdgGate, RXGate, RYGate, RZGate,
                                        PhaseGate, SwapGate, RXXGate, RYYGate, RZZGate,
                                        iSwapGate, RZXGate)

    for k, v in macros.items():
        body = re.sub(r"\\" + k + r"(?![A-Za-z])", lambda _m, v=v: v, body)
    if re.search(r"\\(vdots|cdots|ldots|dots|ddots|hdots)(?![A-Za-z])", body):
        raise Abstract("ellipsis (generic-n template)")
    rows = [r for r in split_top(body, "\\\\")]
    grid = [[parse_cell(c) for c in split_top(r, "&")] for r in rows]
    # drop trailing empty rows
    while grid and all(not c for c in grid[-1]):
        grid.pop()
    nrows = len(grid)
    ncols = max((len(r) for r in grid), default=0)
    for r in grid:
        r.extend([[]] * (ncols - len(r)))
    flags = set()
    classical_row = [any(c[0] in CLASSICAL or (c[0] == "setwiretype" and c[2] and "c" in c[2][0])
                         for cell in row for c in cell) and not any(
                         c[0] in ("gate", "targ", "ctrl", "control", "swap", "targX") for cell in row for c in cell)
                     for row in grid]
    symbols: dict = dict(preset or {})
    _ANON[0] = 0
    G1 = {"x": XGate, "y": YGate, "z": ZGate, "h": HGate, "s": SGate, "sdg": SdgGate, "t": TGate,
          "tdg": TdgGate, "sx": SXGate, "sxdg": SXdgGate, "rx": RXGate, "ry": RYGate, "rz": RZGate,
          "p": PhaseGate}
    G2 = {"swap": SwapGate, "rxx": RXXGate, "ryy": RYYGate, "rzz": RZZGate, "iswap": iSwapGate,
          "rzx": RZXGate}
    qc = QuantumCircuit(nrows)
    # input states written as \lstick{|1>} etc. become explicit preparation gates
    for r, row in enumerate(grid):
        for cell in row[:1]:
            for cmd, opt, args in cell:
                if cmd != "lstick" or not args or (opt and re.search(r"\d", opt)):
                    continue
                st = re.findall(r"\\ket\{\s*([01+\-])\s*\}|\|\s*([01+\-])\s*\\rangle", args[0])
                st = [a or b for a, b in st]
                if len(st) != 1 or st[0] == "0":
                    continue
                {"1": lambda q: qc.x(q), "+": lambda q: qc.h(q),
                 "-": lambda q: (qc.x(q), qc.h(q))}[st[0]](r)
                flags.add("input_state_prep_added")
    for col in range(ncols):
        items = {}  # row -> (role, data)
        links = []  # (r1, r2) vertical connections
        cls_links = []
        multi = []
        for r in range(nrows):
            for cmd, opt, args in grid[r][col]:
                o = opt or ""
                if cmd == "qwx":  # qcircuit vertical quantum wire, default one row up
                    links.append((r, r + (_int(o) if o.strip() else -1)))
                    continue
                if cmd == "wire" and o.split("|")[0].strip() in ("u", "d"):  # \wire[u|d][n]{q|c}
                    parts = o.split("|")
                    d = _int(parts[1]) if len(parts) > 1 and parts[1].strip() else 1
                    d = -d if parts[0].strip() == "u" else d
                    (cls_links if args and args[0].strip() == "c" else links).append((r, r + d))
                    continue
                if cmd == "vqw":  # quantikz vertical quantum wire
                    links.append((r, r + _int(args[0] if args else o)))
                    continue
                if cmd == "qwbundle":
                    raise Abstract("qubit bundle (register drawn as one wire)")
                if cmd in IGNORE or cmd in MEAS:
                    if cmd in MEAS:
                        flags.add("measure_dropped")
                    continue
                if cmd in CLASSICAL:
                    if cmd in ("vcw", "cwx"):
                        d = _int(args[0] if args else o or "1")
                        cls_links.append((r, r + d))
                    if cmd == "cwbend":
                        cls_links.append((r, r + _int(args[0])))
                    continue
                if cmd in ("ctrl", "octrl", "ctrlo"):
                    d = _int(args[0])
                    openc = cmd != "ctrl" or "open" in o
                    if "vertical wire=c" in o.replace(" ", "") or "wire=c" in o.replace(" ", ""):
                        cls_links.append((r, r + d))
                    links.append((r, r + d))
                    items[r] = ("octrl" if openc else "ctrl", None)
                elif cmd in ("control", "ocontrol", "controlo"):
                    items[r] = ("octrl" if (cmd != "control" or "open" in o) else "ctrl", None)
                elif cmd == "targ":
                    items[r] = ("tgt", ("x", []))
                elif cmd in ("swap",):
                    d = _int(args[0])
                    links.append((r, r + d))
                    items[r] = ("swp", None)
                elif cmd in ("targX", "qswap"):
                    items[r] = ("swp", None)
                elif cmd == "phase":
                    items[r] = ("phase", parse_angle(args[0], symbols) if args and args[0].strip() else math.pi)
                elif cmd == "gate":
                    span = 1
                    mm = re.search(r"(?:wires\s*=\s*)?(\d+)", o) if o else None
                    if o and mm and (o.strip()[0].isdigit() or "wires" in o):
                        span = int(mm.group(1))
                    name = args[0] if args else ""
                    if o and "meter" in o:  # \gate[ps=meter]{Z}: a measurement box, not a gate
                        raise Abstract("meter-styled gate box")
                    if RK.match(_norm(name)):  # R_k read as QFT P(2pi/2^k); reviewer must confirm
                        flags.add("qft_rk_convention")
                    if "swap" in o and span == 2:
                        multi.append((r, 2, ("swap", [])))
                        continue
                    if span == 1:
                        g = map_1q(name, symbols)
                        if g is None:
                            raise Abstract(f"gate '{name}'")
                        if g[0] != "id":
                            items[r] = ("tgt", g)
                    else:
                        g = map_2q(name, symbols) if span == 2 else None
                        nn = _norm(name)
                        mt = re.fullmatch(r"(.+?)\^\\otimes(\d+|[a-zA-Z])?", nn)
                        mr = re.fullmatch(r"MultiRZ\((.*)\)", nn)
                        if g is None and mt and (not mt.group(2) or not mt.group(2).isdigit() or int(mt.group(2)) == span):
                            g1 = map_1q(mt.group(1), symbols)
                            if g1 is not None:
                                g = ("tensor", [g1, span])
                        if g is None and mr:
                            g = ("multirz", [parse_angle(_inner(name), symbols), span])
                        if g is None:
                            raise Abstract(f"multi-wire gate[{span}] '{name}'")
                        multi.append((r, span, g))
                elif cmd == "multigate":
                    span = _int(args[0]) + 1
                    g = map_2q(args[1], symbols) if span == 2 else None
                    if g is None:
                        raise Abstract(f"multigate '{args[1]}'")
                    multi.append((r, span, g))
                elif cmd == "sgate":
                    raise Abstract("sgate")
                else:
                    raise Abstract(f"unknown macro \\{cmd}")
        # groups: a vertical link from r to r+d joins every row in between that has content
        parent = {r: r for r in items}
        for r in list(items):
            parent.setdefault(r, r)

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        cls_rows = set()
        for a, b in cls_links:
            lo, hi = min(a, b), max(a, b)
            cls_rows.update(range(lo, hi + 1))
        # overlapping links with no shared end (e.g. 0->2 and 1->3) may be parallel gates drawn in one
        # column; if the merged group then has several dots and several targets, which dot belongs to
        # which target is ambiguous, so do not guess (a chain of dots onto one target is fine)
        # a control whose link ends on a wire with nothing in this column has no target there; if it
        # is then merged with other dots, we would invent a control (two distance-2 CNOTs read as a CCX)
        dangling = {a for a, b in links
                    if b not in items and not any(m_r <= b < m_r + m_s for m_r, m_s, _ in multi)
                    and not any(min(a2, b2) <= b <= max(a2, b2) for a2, b2 in cls_links)}
        crossing = set()
        for i_, (a, b) in enumerate(links):
            for c_, d_ in links[i_ + 1:]:
                if {a, b} & {c_, d_}:
                    continue
                if max(min(a, b), min(c_, d_)) < min(max(a, b), max(c_, d_)):
                    crossing.update((a, b, c_, d_))
        for a, b in links:
            lo, hi = min(a, b), max(a, b)
            members = [r for r in range(lo, hi + 1) if r in items]
            for m_ in members[1:]:
                parent[find(m_)] = find(members[0])
        groups = {}
        for r in items:
            groups.setdefault(find(r), []).append(r)
        ops = []
        for grp in groups.values():
            if any(r in cls_rows or classical_row[r] for r in grp):
                flags.add("classical_control_dropped")
                continue
            ctrls = [r for r in grp if items[r][0] in ("ctrl", "octrl")]
            opens = [r for r in grp if items[r][0] == "octrl"]
            tgts = [r for r in grp if items[r][0] == "tgt"]
            swps = [r for r in grp if items[r][0] == "swp"]
            phs = [r for r in grp if items[r][0] == "phase"]
            if crossing & set(grp) and len(ctrls) >= 2 and len(tgts) + len(phs) >= 2:
                raise Abstract("overlapping vertical links: dots/targets ambiguous")
            if dangling & set(ctrls) and len(ctrls) >= 2:
                raise Abstract("control link ends on an empty wire next to other controls")
            if len(grp) == 1 and not ctrls:
                r = grp[0]
                if tgts:
                    ops.append((build(*items[r][1]), [r], [], []))
                elif phs:
                    ops.append((PhaseGate(items[r][1]), [r], [], []))
                elif swps:
                    raise Abstract("lone swap end")
                continue
            if swps:
                if len(swps) != 2 or tgts or phs:
                    raise Abstract("bad swap group")
                ops.append((SwapGate(), swps, ctrls, opens))
                continue
            if tgts:
                for t in tgts:
                    ops.append((build(*items[t][1]), [t], ctrls, opens))
                if phs:
                    raise Abstract("phase+target group")
                continue
            if phs:
                # controlled phase: dots + one phase marker
                p = phs[0]
                ops.append((PhaseGate(items[p][1]), [p], ctrls + phs[1:], opens))
                continue
            # only dots: multi-controlled Z
            if len(ctrls) >= 2:
                closed = [r for r in ctrls if r not in opens]
                if not closed:
                    raise Abstract("open-dot-only group")
                t = closed[-1]
                ops.append((ZGate(), [t], [r for r in ctrls if r != t], opens))
            else:
                raise Abstract("dangling control")
        for r, span, g in multi:
            nm, ps = g
            ops.append((build(nm, ps), list(range(r, r + span)) if nm in ("tensor", "multirz") else [r, r + span - 1], [], []))
        for gate, tq, cq, oq in ops:
            for o_ in oq:
                qc.x(o_)
            if cq:
                cg = gate.control(len(cq))
                qc.append(cg, list(cq) + list(tq))
            else:
                qc.append(gate, list(tq))
            for o_ in oq:
                qc.x(o_)
    # drop idle wires
    used = sorted({qc.find_bit(q).index for inst in qc.data for q in inst.qubits})
    if not used:
        raise Abstract("empty")
    out = QuantumCircuit(len(used))
    remap = {u: i for i, u in enumerate(used)}
    for inst in qc.data:
        out.append(inst.operation, [remap[qc.find_bit(q).index] for q in inst.qubits])
    if preset:
        flags.add("paper_params:" + ";".join(f"{k}={v}" for k, v in preset.items()))
    symbols = {k: v for k, v in symbols.items() if k not in (preset or {})}
    if symbols:
        flags.add("symbolic_params:" + ";".join(f"{k}={v}" for k, v in symbols.items()))
    return out, sorted(flags)


def _int(s) -> int:
    s = str(s).strip()
    m = re.search(r"-?\d+", s)
    if not m:
        raise Abstract(f"non-numeric offset '{s}'")
    return int(m.group())


# Gate set of the published QASM files: the gates that common OpenQASM 2.0 readers
# (qiskit, pytket, quspect) all accept. ccx is kept as a native gate.
INPUT_GATES = ["id", "h", "x", "y", "z", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "p", "u3",
               "cx", "cz", "cp", "crz", "swap", "ccx"]


def normalize_qasm(source: str) -> str:
    """Normalize an OpenQASM 2.0 program to INPUT_GATES (the form of the published files).

    Final measurements and barriers are removed; if the circuit contains gates outside
    INPUT_GATES it is translated with qiskit at optimization level 0 (pure gate
    translation, no optimization). Raises ValueError on mid-circuit measurements.
    """
    from qiskit import QuantumCircuit, qasm2, transpile

    qc = QuantumCircuit.from_qasm_str(source)
    qc.remove_final_measurements(inplace=True)
    names = {inst.operation.name for inst in qc.data}
    if "measure" in names:
        raise ValueError("mid-circuit measurement")
    stripped = QuantumCircuit(qc.num_qubits)
    for inst in qc.data:
        if inst.operation.name != "barrier":
            stripped.append(inst.operation, [qc.find_bit(q).index for q in inst.qubits])
    if not {i.operation.name for i in stripped.data} <= set(INPUT_GATES):
        stripped = transpile(stripped, basis_gates=list(INPUT_GATES), optimization_level=0)
    return qasm2.dumps(stripped)


def finalize(qc):
    """Translate to INPUT_GATES without borrowing idle wires as |0> ancillas, drop exact-zero
    rotations, and assert the result is the same unitary as the parsed diagram (n <= 12).
    Returns (normalized circuit, stats dict)."""
    from qiskit import QuantumCircuit, qasm2, transpile
    from qiskit.quantum_info import Operator
    t = transpile(qc, basis_gates=INPUT_GATES, optimization_level=0, qubits_initially_zero=False)
    out = QuantumCircuit(t.num_qubits, global_phase=t.global_phase)
    for ins in t.data:
        op = ins.operation
        if op.name in ("rx", "ry", "rz", "p", "cp", "crz") and all(float(x) == 0.0 for x in op.params):
            continue
        if op.name == "id":
            continue
        out.append(op, [t.find_bit(q).index for q in ins.qubits])
    back = qasm2.loads(qasm2.dumps(out), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    equiv = None
    if qc.num_qubits <= 12:
        equiv = bool(Operator(back).equiv(Operator(qc)))
        if not equiv:
            raise RuntimeError("normalized circuit is not unitary-equivalent to the diagram")
    cx = transpile(qc, basis_gates=["cx", "u"], optimization_level=0, qubits_initially_zero=False)
    stats = {"n": qc.num_qubits, "n_cx": cx.count_ops().get("cx", 0), "depth": cx.depth(),
             "n_2q_norm": sum(1 for i in out.data if i.operation.num_qubits == 2),
             "n_ccx_norm": out.count_ops().get("ccx", 0), "unitary_equiv": equiv}
    return out, stats


def collect_macros(tex: str) -> dict:
    """Zero-argument \\newcommand / \\def macros (body only, used for substitution)."""
    out = {}
    for m in re.finditer(r"\\(?:re)?newcommand\*?\{?\\([A-Za-z]+)\}?\s*\{", tex):
        try:
            body, _ = read_group(tex, m.end() - 1, "{", "}")
        except ValueError:
            continue
        out[m.group(1)] = body
    for m in re.finditer(r"\\def\\([A-Za-z]+)\s*\{", tex):
        try:
            body, _ = read_group(tex, m.end() - 1, "{", "}")
        except ValueError:
            continue
        out.setdefault(m.group(1), body)
    # never override structural commands
    for k in list(out):
        if k in ARITY or k in IGNORE or len(out[k]) > 400:
            out.pop(k, None)
    return out
