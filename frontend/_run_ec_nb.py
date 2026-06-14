"""Execute the edge-cloud hearing notebook cell by cell."""

import json
import sys
import time
import traceback
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "edge_cloud_audio_processing.ipynb"
WORKDIR = str(ROOT)

WIDGET_MIMES = {
    "application/vnd.jupyter.widget-view+json",
    "application/vnd.jupyter.widget-state+json",
}


def sanitize_notebook(nb):
    """Strip widget metadata/outputs that break Cursor's notebook renderer."""
    nb.metadata.pop("widgets", None)
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        cleaned = []
        for out in cell.outputs:
            data = out.get("data", {})
            if any(m in data for m in WIDGET_MIMES):
                if "text/plain" in data:
                    text = data["text/plain"]
                    cleaned.append(
                        nbformat.v4.new_output(
                            "stream",
                            name="stdout",
                            text=text if isinstance(text, list) else [text],
                        )
                    )
                continue
            cleaned.append(out)
        cell.outputs = cleaned


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
            sanitize_notebook(nb)
            nbformat.write(nb, PATH)
            sys.exit(1)
        print(f"[ok ] cell {i} in {time.time() - t0:.1f}s", flush=True)
        sanitize_notebook(nb)
        nbformat.write(nb, PATH)

sanitize_notebook(nb)
nbformat.write(nb, PATH)
print("ALL_DONE", flush=True)
