"""Execute the audio foundation models notebook cell by cell."""

import sys, time, traceback
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent / "audio-foundation-models"
PATH = ROOT / "acoustic_scene_classification.ipynb"
WORKDIR = str(ROOT)

nb = nbformat.read(PATH, as_version=4)
client = NotebookClient(
    nb,
    timeout=3600,
    kernel_name="python3",
    resources={"metadata": {"path": WORKDIR}},
)

n = len(nb.cells)
with client.setup_kernel():
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        t0 = time.time()
        print(f"[run] cell {i}/{n} ...", flush=True)
        try:
            client.execute_cell(cell, i)
        except Exception:
            print(f"[ERR] cell {i} failed:", flush=True)
            traceback.print_exc()
            nbformat.write(nb, PATH)
            sys.exit(1)
        print(f"[ok ] cell {i} in {time.time() - t0:.1f}s", flush=True)
        nbformat.write(nb, PATH)

nbformat.write(nb, PATH)
print("ALL_DONE", flush=True)
