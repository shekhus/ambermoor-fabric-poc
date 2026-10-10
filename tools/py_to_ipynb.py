"""Convert fabric/notebooks/*.py ("# %%" cells) into .ipynb files you can import into a Fabric workspace.

Fabric: Workspace -> Import -> Notebook -> From this computer. The "# %% parameters" cell gets the "parameters"
tag, so pipelines (lab L2) can pass values. Override a parameter line with --param, e.g.
    python tools/py_to_ipynb.py --out build/notebooks --param 'upn_overrides = {"P03": "qa.p03@contoso.com"}'
"""
import argparse
import json
import re
from pathlib import Path

NOTEBOOKS = {
    "NB_01_load_bronze": "fabric/notebooks/nb_01_load_bronze.py",
    "NB_03_gold_fasttrack": "fabric/notebooks/nb_03_gold_fasttrack.py",
}


def to_cells(src: str, params: dict[str, str]) -> list[dict]:
    cells, header, current, tag = [], [], None, None
    for line in src.splitlines():
        m = re.match(r"^# %%\s*(.*)$", line)
        if m:
            if current is not None:
                cells.append((tag, current))
            current, tag = [], m.group(1).strip()
            continue
        if current is None:
            header.append(line)
            continue
        name = line.split("=", 1)[0].strip()
        if tag == "parameters" and name in params:
            line = params[name]
        current.append(line)
    if current is not None:
        cells.append((tag, current))

    out = [{"cell_type": "markdown", "metadata": {},
            "source": "\n".join(l.lstrip("# ").rstrip() for l in header).strip()}]
    for tag, lines in cells:
        while lines and not lines[-1].strip():
            lines.pop()
        out.append({"cell_type": "code", "execution_count": None, "outputs": [],
                    "metadata": {"tags": ["parameters"]} if tag == "parameters" else {},
                    "source": "\n".join(lines)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/notebooks")
    ap.add_argument("--param", action="append", default=[],
                    help='replace a parameter-cell line, e.g. \'upn_overrides = {"P03": "qa.p03@x.com"}\'')
    args = ap.parse_args()
    params = {p.split("=", 1)[0].strip(): p for p in args.param}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, path in NOTEBOOKS.items():
        nb = {
            "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark"},
                         "language_info": {"name": "python"}},
            "cells": to_cells(Path(path).read_text(encoding="utf-8"), params),
        }
        (out / f"{name}.ipynb").write_text(json.dumps(nb, indent=1), encoding="utf-8")
        print(f"wrote {out / f'{name}.ipynb'}")


if __name__ == "__main__":
    main()
