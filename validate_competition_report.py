"""Numerically execute the trusted competitive QMD, without Quarto/Jupyter."""
from pathlib import Path
import contextlib
import io
import os
import re
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parent
    report = root/"amazon-walmart-scenarios.qmd"
    source = report.read_text(encoding="utf-8")
    chunks = re.findall(r"^```\{python\}\n(.*?)^```\s*$", source, flags=re.M | re.S)
    if not chunks:
        raise RuntimeError("No Python chunks found")
    with tempfile.TemporaryDirectory(prefix="amazon-walmart-validation-") as tmp:
        work = Path(tmp)
        os.environ.setdefault("MPLCONFIGDIR", str(work/"mpl-cache"))
        os.environ.setdefault("XDG_CACHE_HOME", str(work/"cache"))
        import matplotlib
        matplotlib.use("Agg")
        import shutil
        shutil.copyfile(root/"competitive_scenarios.py", work/"competitive_scenarios.py")
        previous = Path.cwd()
        sys.path.insert(0, str(root))
        output = io.StringIO()
        namespace = {"__name__": "__main__"}
        try:
            os.chdir(work)
            with contextlib.redirect_stdout(output):
                for number, chunk in enumerate(chunks, 1):
                    exec(compile(chunk, f"{report.name}:chunk-{number}", "exec"), namespace)
        except Exception:
            print(output.getvalue(), file=sys.stderr)
            raise
        finally:
            os.chdir(previous)
            sys.path.remove(str(root))
        assert len(namespace["cases"]) == 4
        assert namespace["summary"]["grid_rows"] == 1215
        assert namespace["base"].adoption == 1
        for name in ["company_scenarios.csv", "seller_comparison.csv", "summary.json",
                     "company_outcomes.png", "walmart_breakeven.png"]:
            assert (work/"competition-outputs"/name).is_file(), name
        print(f"Executed all {len(chunks)} competitive-report Python chunks.")
        print("Verified 4 named cases, 1,215 grid rows, and generated figures/exports.")
        print(namespace["model"].validate()+".")
        print("Quarto HTML rendering is not checked by this numerical validator.")


if __name__ == "__main__":
    main()
