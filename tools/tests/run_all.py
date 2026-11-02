"""Run every tests/test_*.py script; exit status 1 if any fails.

Usage: python -I tools/tests/run_all.py
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
failed = []
for t in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
    p = subprocess.run([sys.executable, "-I", t, TOOLS], capture_output=True, text=True)
    print(f"{'PASS' if p.returncode == 0 else 'FAIL'}  {os.path.basename(t)}")
    if p.returncode:
        failed.append(t)
        print(p.stdout[-2000:], p.stderr[-2000:])
print(f"{len(failed)} failed" if failed else "all tests passed")
sys.exit(1 if failed else 0)
