"""Download arXiv e-print sources, keep only text members (.tex/.qasm/.txt/.py), flattened. Never executes anything.

Usage: python -I fetch_src.py DATA_DIR [PAPERS_JSON]   (PAPERS_JSON relative to DATA_DIR, default kw.json)
PAPERS_JSON is a list of records in the fetch_meta.py format (only "id" is used).
Writes DATA_DIR/src/<id>/<sanitized name> and appends a JSON line per paper to DATA_DIR/src_index.jsonl.
Rate limit: one request per ~3 s, as asked by arXiv."""
import gzip, io, json, os, re, sys, tarfile, time, urllib.request
base = sys.argv[1]
recs = json.load(open(os.path.join(base, sys.argv[2] if len(sys.argv) > 2 else "kw.json")))
idx_path = os.path.join(base, "src_index.jsonl")
done = set()
if os.path.exists(idx_path):
    done = {json.loads(l)["id"] for l in open(idx_path)}
MARK = re.compile(r"\\begin\{quantikz\}|\\Qcircuit|\\qw\b|OPENQASM|\\begin\{yquant\}|qcircuit", re.I)
KEEP = re.compile(r"\.(tex|qasm|txt|py)$", re.I)
for r in recs:
    pid = r["id"]
    if pid in done: continue
    t0 = time.time()
    url = f"https://export.arxiv.org/e-print/{pid}"
    info = {"id": pid, "ok": False}
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "arxiv-circuits-dataset/1.0"}), timeout=120).read()
        files = {}
        try:
            raw = gzip.decompress(data)
        except Exception:
            raw = data
        try:
            with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
                for m in tf.getmembers():
                    if m.isfile() and KEEP.search(m.name) and m.size < 5_000_000:
                        files[m.name] = tf.extractfile(m).read()
        except tarfile.ReadError:
            if raw[:4] != b"%PDF":
                files["main.tex"] = raw
        d = os.path.join(base, "src", pid.replace("/", "_"))
        os.makedirs(d, exist_ok=True)
        marks = {}
        for name, b in files.items():
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[-120:]
            open(os.path.join(d, safe), "wb").write(b)
            t = b.decode("utf-8", "replace")
            n = len(MARK.findall(t))
            if n: marks[safe] = n
        info.update(ok=True, nfiles=len(files), marks=marks,
                    nquantikz=sum(b.decode("utf-8","replace").count("begin{quantikz}") for b in files.values()),
                    nqcircuit=sum(b.decode("utf-8","replace").count("Qcircuit") for b in files.values()),
                    qasm_files=[n for n in files if n.lower().endswith(".qasm")])
    except Exception as e:
        info["err"] = f"{type(e).__name__}: {e}"[:200]
    with open(idx_path, "a") as f: f.write(json.dumps(info) + "\n")
    time.sleep(max(0.0, 3.1 - (time.time() - t0)))
print("done")
