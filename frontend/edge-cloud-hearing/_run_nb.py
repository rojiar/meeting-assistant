import time, pathlib
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

ROOT = pathlib.Path(__file__).resolve().parent
NB = ROOT / "edge_cloud_audio_processing.ipynb"

nb = nbformat.read(NB, as_version=4)
client = NotebookClient(
    nb,
    timeout=1800,
    kernel_name="python3",
    resources={"metadata": {"path": str(ROOT)}},
)
client.create_kernel_manager()
client.start_new_kernel()
client.start_new_kernel_client()
print("kernel started", flush=True)

t0 = time.time()
code_idx = 0
try:
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        code_idx += 1
        head = (cell.source.strip().splitlines() or ["(empty)"])[0][:70]
        print(f"[cell {i:02d} | code #{code_idx}] >>> {head}", flush=True)
        ts = time.time()
        try:
            client.execute_cell(cell, i)
        except CellExecutionError as e:
            print(
                f"  !! ERROR in cell {i}: {str(e).splitlines()[-1][:200]}", flush=True
            )
            nbformat.write(nb, NB)
            raise
        for o in cell.get("outputs", []):
            if o.get("output_type") == "error":
                print(
                    f"  !! error output: {o.get('ename')}: {o.get('evalue')}",
                    flush=True,
                )
            if o.get("output_type") == "stream" and o.get("name") == "stdout":
                for ln in o.get("text", "").splitlines():
                    if any(
                        k in ln
                        for k in (
                            "accuracy",
                            "Accuracy",
                            "Improvement",
                            "phone",
                            "Cloud",
                            "Scenes",
                        )
                    ):
                        print("     | " + ln, flush=True)
        print(
            f"     done in {time.time() - ts:5.1f}s  (total {time.time() - t0:5.1f}s)",
            flush=True,
        )
finally:
    nbformat.write(nb, NB)
    try:
        client._cleanup_kernel()
    except Exception:
        pass
print(f"\nALL CELLS EXECUTED in {time.time() - t0:.1f}s", flush=True)
