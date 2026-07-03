"""Phase B2 — post-hoc supplementary validation: PBO via CSCV + CPCV OOS-Sharpe distribution.

Runs AFTER both studies' verdicts were already decided by their pre-registered gates (see
research/PREREGISTRATION*.md, output/REPORT*.md). Nothing here revises a verdict — see
src/pbo.py's module docstring for the method and the hard rules this phase operates under.

Re-evaluates ONLY the frozen grid configs (base N=42 via data_cache/series_M1.parquet, variant
N=36 via data_cache/series_A.parquet) — no new parameters, models, signals or data.

Writes:
  * output/phase_B2_pbo.md                          (consolidated PBO/CPCV findings, both studies)
  * output/figures/pbo_logit_hist_{base,variantA}.png
  * output/figures/pbo_degradation_scatter_{base,variantA}.png
  * Appends a "## Post-hoc supplementary validation (added after verdict)" section to
    output/REPORT.md and output/REPORT_variantA.md (idempotent: replaces a prior such section
    if this script is re-run).

Run: .venv\\Scripts\\python run_B2_pbo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from src import pbo as pbo_mod
from src import performance as perf

S_PRIMARY = 16
S_SENSITIVITY = (8, 12, 16)
APPEND_MARKER = "## Post-hoc supplementary validation (added after verdict)"


def _load_matrix(name: str) -> pd.DataFrame:
    df = pd.read_parquet(config.DATA_CACHE / name)
    return df.sort_index()


def _run_study(tag: str, matrix_file: str, oos_file: str, wf_oos_sharpe: float, wf_label: str) -> dict:
    mat = _load_matrix(matrix_file)
    sens = {S: pbo_mod.cscv_pbo(mat, S=S, embargo=config.EMBARGO_BARS) for S in S_SENSITIVITY}
    primary = sens[S_PRIMARY]
    cpcv = pbo_mod.cpcv_oos_distribution(primary)
    pct = pbo_mod.percentile_of(wf_oos_sharpe, primary["oos_sharpe"])

    oos_net = pd.read_parquet(config.DATA_CACHE / oos_file)["net"].dropna()
    ext = perf.extended_metrics(oos_net)

    # figures
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(primary["logits"], bins=40, color="#06c", alpha=0.85)
    ax.axvline(0, color="k", lw=1.0)
    ax.set_xlabel("logit λ = ln(ω/(1-ω))"); ax.set_ylabel("splits")
    ax.set_title(f"{tag} — CSCV logit distribution (S={S_PRIMARY}, PBO={primary['pbo']:.3f})")
    fig.tight_layout(); fig.savefig(config.FIG_DIR / f"pbo_logit_hist_{tag}.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(primary["is_sharpe"], primary["oos_sharpe"], s=6, alpha=0.25, color="#c02")
    lim = [min(primary["is_sharpe"].min(), primary["oos_sharpe"].min()),
          max(primary["is_sharpe"].max(), primary["oos_sharpe"].max())]
    ax.plot(lim, lim, "k--", lw=0.8, label="IS = OOS")
    ax.axhline(0, color="k", lw=0.6); ax.axhline(wf_oos_sharpe, color="#093", lw=1.2,
                                                 label=f"{wf_label} ({wf_oos_sharpe:.2f})")
    ax.set_xlabel("IS Sharpe of the split-selected config")
    ax.set_ylabel("OOS Sharpe of the same config")
    ax.set_title(f"{tag} — IS-vs-OOS degradation (S={S_PRIMARY}, {primary['n_splits']} splits)")
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(config.FIG_DIR / f"pbo_degradation_scatter_{tag}.png", dpi=120); plt.close(fig)

    return {"tag": tag, "sens": sens, "primary": primary, "cpcv": cpcv, "ext": ext,
            "wf_oos_sharpe": wf_oos_sharpe, "wf_label": wf_label, "wf_percentile": pct}


def _ordinal(n: float) -> str:
    i = int(round(n))
    if 10 <= i % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(i % 10, "th")
    return f"{i}{suf}"


def _section_md(res: dict) -> str:
    L = []
    W = L.append
    tag, primary, cpcv = res["tag"], res["primary"], res["cpcv"]
    W(APPEND_MARKER)
    W("\n> Computed AFTER the verdict above was already decided by the pre-registered gates. This")
    W("> section cannot revise that verdict, strengthen it, or rehabilitate a negative result even if")
    W("> a number below looks favourable — it is the deferred \"optional, gold standard\" PBO/CPCV test,")
    W("> closing the one item the original brief left open. See `docs/DECISION_LOG.md` and `src/pbo.py`")
    W("> for the exact method (CSCV, Bailey-Borwein-LdP-Zhu 2017) and purge convention.\n")
    sens_pbos = [res["sens"][S]["pbo"] for S in S_SENSITIVITY]
    W(f"**PBO (S={S_PRIMARY}, purge={config.EMBARGO_BARS}):** "
      f"**{primary['pbo']:.3f}** (S-sensitivity range **{min(sens_pbos):.3f}–{max(sens_pbos):.3f}** "
      f"across S={{{','.join(str(s) for s in S_SENSITIVITY)}}}; table below) over "
      f"{primary['n_splits']}/{primary['n_splits_total']} valid combinatorial splits "
      f"(C({S_PRIMARY},{S_PRIMARY//2})) — i.e. in "
      f"{primary['pbo']*100:.0f}% of splits, the config picked as best in-sample ranked *below the "
      f"out-of-sample median* among all frozen configs. High PBO reinforces the verdict above.\n")
    W("S-sensitivity (so the headline isn't S-picked):\n")
    W("| S | splits used | PBO |")
    W("|---:|---:|---:|")
    for S in S_SENSITIVITY:
        r = res["sens"][S]
        W(f"| {S} | {r['n_splits']}/{r['n_splits_total']} | {r['pbo']:.3f} |")
    W(f"\n**CPCV OOS-Sharpe distribution** of the per-split IS-selected config (S={S_PRIMARY}, "
      f"n={cpcv['n']}): median **{cpcv['median']:.3f}**, IQR [{cpcv['q25']:.3f}, {cpcv['q75']:.3f}], "
      f"range [{cpcv['min']:.3f}, {cpcv['max']:.3f}].")
    W(f"- The single walk-forward path's OOS Sharpe (**{res['wf_oos_sharpe']:.3f}**, \"{res['wf_label']}\") "
      f"sits at the **{_ordinal(res['wf_percentile'])} percentile** of this distribution — one "
      f"chronological draw among many combinatorial train/test partitions, not \"the\" answer.")
    W(f"- **Caveat (read this before drawing any conclusion from the median):** both this distribution "
      f"and the walk-forward path re-select the in-sample-best config independently per split/fold — "
      f"neither is one fixed config's OOS Sharpe evaluated repeatedly (the picked config varies across "
      f"the {primary['n_splits']} splits here exactly as it varied across the walk-forward's 5 folds). "
      f"The real asymmetry is combinatorial breadth versus chronological order, not selection-vs-no-"
      f"selection: most CSCV splits let blocks that are chronologically *after* the walk-forward's test "
      f"window serve as \"training\" — an ordering no live sequential strategy could ever trade. The "
      f"CPCV median is a description of the *selection process's* spread under that broader, partly "
      f"unrealisable set of partitions, not a higher, more-representative, or more-tradeable Sharpe "
      f"estimate than the actual walk-forward. It does not revise, soften, or rehabilitate the verdict "
      f"above; the high PBO alongside it points the same direction the verdict does.")
    W("\nFigures: `figures/pbo_logit_hist_" + tag + ".png`, `figures/pbo_degradation_scatter_" + tag + ".png`\n")

    e = res["ext"]
    W("**Descriptive-stats extension** (walk-forward OOS net returns; descriptive only, no verdict "
      "weight):\n")
    W("| Sortino | Calmar | skew | excess kurtosis | daily VaR 95% | daily CVaR 95% | longest DD (days) |")
    W("|---:|---:|---:|---:|---:|---:|---:|")
    W(f"| {e['sortino']:.2f} | {e['calmar']:.2f} | {e['skew']:.2f} | {e['excess_kurtosis']:.2f} | "
      f"{e['var_95']*100:.2f}% | {e['cvar_95']*100:.2f}% | {e['longest_dd_days']} |")
    return "\n".join(L)


def _append_or_replace(report_path: Path, section_md: str) -> None:
    text = report_path.read_text(encoding="utf-8")
    marker_pos = text.find(APPEND_MARKER)
    if marker_pos != -1:
        text = text[:marker_pos].rstrip() + "\n\n"
    else:
        text = text.rstrip() + "\n\n"
    report_path.write_text(text + section_md + "\n", encoding="utf-8")


MULTIPLICITY_NOTE = (
    "## Program-level multiplicity\n\n"
    "The two studies form one research family: 2 pre-registered hypotheses, "
    "42 (base) + 36 (Variant A) = **78 grid configurations tested in total**. Neither study's "
    "within-study BH-FDR/DSR correction accounts for this program-level breadth. A family-wise "
    "correction spanning both hypotheses would only raise the significance bar further — since both "
    "verdicts are already negative (`FALSIFIED` / `INCONCLUSIVE` leaning `FALSIFIED`) under their own "
    "within-study corrections, a program-level correction cannot change either verdict; it can only "
    "strengthen the case for the negative reading. No such computation is needed to reach that "
    "conclusion. See `docs/TEST_RATIONALE.md` for the full test-selection rationale, including tests "
    "considered and deliberately not run.\n"
)


def main() -> None:
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)

    base = _run_study("base", "series_M1.parquet", "oos_M1.parquet",
                      wf_oos_sharpe=0.294, wf_label="base-study WF OOS")
    variantA = _run_study("variantA", "series_A.parquet", "oos_A.parquet",
                          wf_oos_sharpe=0.684, wf_label="Variant-A WF OOS")

    (config.OUTPUT_DIR / "phase_B2_pbo.md").write_text(
        "# Phase B2 — PBO (CSCV) + CPCV OOS-Sharpe distribution\n\n"
        "Post-hoc supplementary validation, added after both verdicts. See each study's appended "
        "section in `output/REPORT.md` / `output/REPORT_variantA.md` for the full write-up.\n\n"
        "## Base study\n" + _section_md(base) + "\n## Variant A\n" + _section_md(variantA) +
        "\n" + MULTIPLICITY_NOTE,
        encoding="utf-8")

    _append_or_replace(config.OUTPUT_DIR / "REPORT.md", _section_md(base))
    _append_or_replace(config.OUTPUT_DIR / "REPORT_variantA.md", _section_md(variantA))

    print("PHASE B2 OK")
    for res in (base, variantA):
        print(f"  {res['tag']}: PBO(S={S_PRIMARY})={res['primary']['pbo']:.3f}  "
              f"CPCV median OOS Sharpe={res['cpcv']['median']:.3f}  "
              f"WF path percentile={res['wf_percentile']:.0f}th")
        print(f"    S-sensitivity: " +
              ", ".join(f"S={S}:{res['sens'][S]['pbo']:.3f}" for S in S_SENSITIVITY))


if __name__ == "__main__":
    main()
