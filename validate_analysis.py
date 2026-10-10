"""Execute our QMD chunks and compare them with our original simulation.

This runner executes the source code in the adjacent report. It is intended for
this repository's trusted analysis, not arbitrary downloaded Quarto documents.
No Quarto or Jupyter installation is required for numerical verification.
"""
from pathlib import Path
import contextlib
import csv
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parent
    report = root / "amazon-advertising-agents.qmd"
    chunks = re.findall(r"^```\{python\}\n(.*?)^```\s*$",
                        report.read_text(encoding="utf-8"), flags=re.M | re.S)
    if len(chunks) != 12:
        raise RuntimeError(f"Expected 12 Python chunks, found {len(chunks)}")

    with tempfile.TemporaryDirectory(prefix="amazon-analysis-validation-") as tmp:
        workspace = Path(tmp)
        os.environ.setdefault("MPLCONFIGDIR", str(workspace / "mpl-cache"))
        os.environ.setdefault("XDG_CACHE_HOME", str(workspace / "cache"))
        import matplotlib
        matplotlib.use("Agg")
        import numpy as np

        old_cwd = Path.cwd()
        output = io.StringIO()
        try:
            os.chdir(workspace)
            namespace = {"__name__": "__main__"}
            with contextlib.redirect_stdout(output):
                for number, chunk in enumerate(chunks, 1):
                    exec(compile(chunk, f"{report.name}:chunk-{number}", "exec"),
                         namespace)
        except Exception:
            print(output.getvalue(), file=sys.stderr)
            raise
        finally:
            os.chdir(old_cwd)

        original_dir = workspace / "original"
        original_dir.mkdir()
        original_script = original_dir / "simulate.py"
        shutil.copyfile(root / "simulate.py", original_script)
        result = subprocess.run([sys.executable, str(original_script)],
                                cwd=original_dir, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)

        with (original_dir / "scenarios.csv").open(newline="") as f:
            original = list(csv.DictReader(f))
        with (workspace / "quarto-outputs" / "scenarios.csv").open(newline="") as f:
            reproduced = list(csv.DictReader(f))
        if len(original) != len(reproduced) or len(original) != 35:
            raise AssertionError("Central scenario counts do not match")
        for before, after in zip(original, reproduced):
            for field in ["ad_rate", "fee_rate", "price_change", "price_from_100"]:
                if not np.isclose(float(before[field]), float(after[field]),
                                  rtol=1e-12, atol=1e-12):
                    raise AssertionError(f"Original and Quarto results differ: {field}")

        print(f"Executed all {len(chunks)} Quarto Python chunks.")
        print("All 35 central results match the original simulation.")
        print(f"Generated {len(namespace['grid_rows']):,} sensitivity scenarios.")
        print("All embedded accounting and boundary checks passed.")
        print("This validates numerical execution, not Quarto HTML rendering.")


if __name__ == "__main__":
    main()
