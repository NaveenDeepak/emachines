"""Run every notebook under a folder in place, so the docs show the outputs of code cells (plots, tables).

Used by the Deploy Docs workflow only; the outputs are never committed. Cells marked
``#| eval: false`` are skipped, as nbdev-test skips them.

Usage:  python .github/scripts/execute_notebooks.py nbs [--timeout 600] [--workers 4]
"""
import argparse
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nbformat
from nbclient import NotebookClient

SKIP = re.compile(r"^#\|\s*eval:\s*false\s*$", re.MULTILINE)
TAG = "skip-execution"


def run(path: str, timeout: int) -> str:
    p = Path(path)
    nb = nbformat.read(p, as_version=4)
    tagged = []
    for c in nb.cells:
        if c.cell_type == "code" and SKIP.search(c.source):
            c.metadata.setdefault("tags", []).append(TAG)
            tagged.append(c)
    try:
        NotebookClient(nb, timeout=timeout, kernel_name="python3", skip_cells_with_tag=TAG,
                       resources={"metadata": {"path": str(p.parent)}}).execute()
    except Exception as e:                                      # report, keep going
        return f"FAILED {p}: {type(e).__name__}: {str(e).splitlines()[-1] if str(e) else ''}"
    for c in tagged:
        c.metadata["tags"].remove(TAG)
        if not c.metadata["tags"]:
            del c.metadata["tags"]
    nbformat.write(nb, p)
    return f"ok     {p}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    paths = sorted(str(p) for p in Path(a.folder).rglob("*.ipynb")
                   if ".ipynb_checkpoints" not in p.parts and not p.name.startswith("_"))
    with ProcessPoolExecutor(a.workers) as ex:
        results = list(ex.map(run, paths, [a.timeout] * len(paths)))
    print("\n".join(results))
    failed = [r for r in results if r.startswith("FAILED")]
    print(f"{len(paths) - len(failed)} of {len(paths)} notebooks executed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
