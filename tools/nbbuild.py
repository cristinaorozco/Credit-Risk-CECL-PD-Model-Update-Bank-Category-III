"""Tiny notebook builder/executor (no nbformat needed): runs cells in one namespace and stores outputs in .ipynb v4."""
import ast, base64, io, json, sys, contextlib, traceback
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _src(t): return t.strip("\n").splitlines(keepends=True)

def run_notebook(cells, out_path, cwd):
    import os; os.chdir(cwd)
    ns = {"__name__": "__main__"}; outputs_acc = []
    def display(obj=None, **kw):
        import pandas as pd
        if isinstance(obj, (pd.DataFrame, pd.Series)):
            df = obj.to_frame() if isinstance(obj, pd.Series) else obj
            outputs_acc.append({"output_type": "display_data", "metadata": {},
                                "data": {"text/html": _src(df.to_html(max_rows=40, float_format=lambda x: f"{x:,.4f}")), "text/plain": _src(df.to_string(max_rows=40))}})
        elif isinstance(obj, (bytes, bytearray)):
            outputs_acc.append({"output_type": "display_data", "metadata": {}, "data": {"image/png": base64.b64encode(obj).decode(), "text/plain": ["<Figure>"]}})
        elif obj is not None:
            outputs_acc.append({"output_type": "display_data", "metadata": {}, "data": {"text/plain": _src(repr(obj))}})
    def show_image(path):
        display(Path(path).read_bytes())
    ns["display"], ns["show_image"] = display, show_image
    plt.show = lambda *a, **k: None
    nb_cells, count = [], 0
    for kind, text in cells:
        if kind == "md":
            nb_cells.append({"cell_type": "markdown", "metadata": {}, "source": _src(text)}); continue
        count += 1; outputs_acc.clear(); buf = io.StringIO()
        tree = ast.parse(text); last = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last = ast.Expression(tree.body.pop().value)
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(tree, "<cell>", "exec"), ns)
                if last is not None:
                    val = eval(compile(last, "<cell>", "eval"), ns)
                    if val is not None: display(val)
        except Exception:
            traceback.print_exc(); raise
        figs = []
        for n in plt.get_fignums():
            b = io.BytesIO(); plt.figure(n).savefig(b, format="png", dpi=110, bbox_inches="tight"); figs.append(b.getvalue()); plt.close(n)
        outs = []
        if buf.getvalue(): outs.append({"output_type": "stream", "name": "stdout", "text": _src(buf.getvalue())})
        outs += list(outputs_acc)
        for f in figs: outs.append({"output_type": "display_data", "metadata": {}, "data": {"image/png": base64.b64encode(f).decode(), "text/plain": ["<Figure>"]}})
        nb_cells.append({"cell_type": "code", "metadata": {}, "execution_count": count, "source": _src(text), "outputs": outs})
    nb = {"cells": nb_cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
          "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    Path(out_path).write_text(json.dumps(nb, indent=1))
