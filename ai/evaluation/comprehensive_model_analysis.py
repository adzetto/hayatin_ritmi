"""
DCA-CNN Comprehensive Model Analysis
=====================================
- Per-lead ablation study (each single lead 0-11)
- All meaningful lead combinations (I+II, II+III, limb, precordial, etc.)
- Per-dataset per-class AUC with 12/3/1-lead
- Graceful degradation curve
- Gate value analysis (which channels does the model consider important?)
- Model response when leads are missing/corrupted
- Comparison table: DCA-CNN vs DS-1D-CNN across all configs

Usage: python ai/evaluation/comprehensive_model_analysis.py
"""
import os, sys, json, time
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ai" / "training"))

import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

CACHE_DIR = PROJECT_ROOT / "ai" / "cache"
CKPT_DIR = PROJECT_ROOT / "ai" / "models" / "checkpoints"
RESULTS_DIR = PROJECT_ROOT / "ai" / "models" / "results"
SNOMED_CSV = PROJECT_ROOT / "dataset" / "ecg-arrhythmia" / "ConditionNames_SNOMED-CT.csv"

LEAD_NAMES = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

LEAD_COMBOS = {
    "Lead II only":         [1],
    "Lead I only":          [0],
    "Lead III only":        [2],
    "Lead V1 only":         [6],
    "Lead V2 only":         [7],
    "Lead V5 only":         [10],
    "I + II":               [0, 1],
    "II + III":             [1, 2],
    "II + V1":              [1, 6],
    "II + V5":              [1, 10],
    "Einthoven (I,II,III)": [0, 1, 2],
    "Limb (I,II,III,aVR,aVL,aVF)": [0, 1, 2, 3, 4, 5],
    "Precordial (V1-V6)":  [6, 7, 8, 9, 10, 11],
    "II + V1-V6":           [1, 6, 7, 8, 9, 10, 11],
    "Clinical 12-lead":    list(range(12)),
}

def load_class_names():
    import csv
    names = []
    with open(SNOMED_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            names.append(row["Acronym Name"])
    return names


def load_datasets():
    """Load all cached datasets. Returns dict of name -> (X, Y)."""
    datasets = {}
    cache_files = {
        "sph": CACHE_DIR / "dataset_cache.npz",
        "cpsc2018": CACHE_DIR / "cache_cpsc2018.npz",
        "cpsc2018-extra": CACHE_DIR / "cache_cpsc2018-extra.npz",
        "georgia": CACHE_DIR / "cache_georgia.npz",
        "chapman-shaoxing": CACHE_DIR / "cache_chapman-shaoxing.npz",
        "ningbo": CACHE_DIR / "cache_ningbo.npz",
    }
    for name, path in cache_files.items():
        if not path.exists():
            continue
        data = np.load(path, allow_pickle=True)
        X, Y = data["X"], data["Y"]
        valid = np.isfinite(X).reshape(X.shape[0], -1).all(axis=1)
        X, Y = X[valid], Y[valid]
        rng = np.random.RandomState(42)
        n = min(2000, len(X))
        idx = rng.choice(len(X), n, replace=False)
        datasets[name] = (X[idx], Y[idx])
        console.print(f"  [green]{name}[/]: {n:,} samples")
    return datasets


def load_models():
    from train_dca_cnn import DcaCNN
    from train_pytorch import EcgDSCNN

    models = {}

    dca_path = CKPT_DIR / "ecg_dca_cnn_best.pt"
    if dca_path.exists():
        m = DcaCNN()
        m.load_state_dict(torch.load(dca_path, map_location="cpu", weights_only=True))
        m.eval()
        models["DCA-CNN"] = m

    ds_path = CKPT_DIR / "ecg_best_combined.pt"
    if not ds_path.exists():
        ds_path = CKPT_DIR / "ecg_best.pt"
    if ds_path.exists():
        m = EcgDSCNN()
        m.load_state_dict(torch.load(ds_path, map_location="cpu", weights_only=True))
        m.eval()
        models["DS-1D-CNN"] = m

    return models


def evaluate_with_leads(model, X, Y, active_leads, model_name="DCA-CNN"):
    """Run inference with specific leads active, others zeroed."""
    X_masked = X.copy()
    for ch in range(12):
        if ch not in active_leads:
            X_masked[:, ch, :] = 0.0

    X_t = torch.from_numpy(X_masked).float()
    c_active = len(active_leads)

    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X_t), 64):
            batch = X_t[i:i+64]
            if model_name == "DCA-CNN":
                logits = model(batch, c_active=c_active)
            else:
                logits = model(batch)
            probs = torch.sigmoid(logits).numpy()
            all_preds.append(np.nan_to_num(probs, 0.0))

    preds = np.concatenate(all_preds, axis=0)

    valid_cols = [c for c in range(Y.shape[1])
                  if 0 < Y[:, c].sum() < len(Y)]

    if len(valid_cols) < 2:
        return {"macro_auc": 0.0, "n_classes": 0}

    macro_auc = roc_auc_score(Y[:, valid_cols], preds[:, valid_cols], average="macro")
    micro_auc = roc_auc_score(Y[:, valid_cols], preds[:, valid_cols], average="micro")

    per_class = {}
    class_names = load_class_names()
    for c in valid_cols:
        auc = roc_auc_score(Y[:, c], preds[:, c])
        name = class_names[c] if c < len(class_names) else f"cls_{c}"
        per_class[name] = round(auc, 4)

    return {
        "macro_auc": round(macro_auc, 4),
        "micro_auc": round(micro_auc, 4),
        "n_classes": len(valid_cols),
        "per_class": per_class,
    }


def analyze_gate_values(model):
    """Extract learned gate values g_c = σ(α_c) from DCA-CNN ACC layer."""
    console.print(Panel("[bold cyan]GATE VALUE ANALYSIS[/]", expand=False))
    alpha = model.acc.alpha.detach().numpy()
    gates = 1.0 / (1.0 + np.exp(-alpha))

    table = Table(title="Learned Channel Gate Values g_c = sigmoid(alpha_c)", box=box.SIMPLE_HEAVY)
    table.add_column("Lead", style="cyan")
    table.add_column("α_c", justify="right")
    table.add_column("g_c", justify="right")
    table.add_column("Importance", justify="left")

    for i in range(12):
        imp = "█" * int(gates[i] * 20)
        style = "green" if gates[i] > 0.8 else ("yellow" if gates[i] > 0.5 else "red")
        table.add_row(LEAD_NAMES[i], f"{alpha[i]:.3f}", f"[{style}]{gates[i]:.4f}[/]", imp)

    console.print(table)
    return {LEAD_NAMES[i]: round(float(gates[i]), 4) for i in range(12)}


def run_lead_ablation(models, datasets):
    """Test every single lead (0-11) individually across all datasets."""
    console.print(Panel("[bold cyan]SINGLE-LEAD ABLATION STUDY[/]", expand=False))

    results = {}
    dca = models.get("DCA-CNN")
    if dca is None:
        return results

    for ds_name, (X, Y) in datasets.items():
        console.print(f"\n  [bold]{ds_name}[/]:")
        ds_results = {}
        for lead_idx in range(12):
            r = evaluate_with_leads(dca, X, Y, [lead_idx], "DCA-CNN")
            ds_results[LEAD_NAMES[lead_idx]] = r["macro_auc"]
            console.print(f"    Lead {LEAD_NAMES[lead_idx]:>4s}: AUC = {r['macro_auc']:.4f}")
        results[ds_name] = ds_results

    return results


def run_lead_combinations(models, datasets):
    """Test all meaningful lead combinations."""
    console.print(Panel("[bold cyan]LEAD COMBINATION ANALYSIS[/]", expand=False))

    results = {}
    dca = models.get("DCA-CNN")
    ds_cnn = models.get("DS-1D-CNN")

    test_ds = "sph"
    if test_ds not in datasets:
        test_ds = list(datasets.keys())[0]
    X, Y = datasets[test_ds]

    table = Table(title=f"Lead Combinations — {test_ds} ({len(X)} samples)",
                  box=box.ROUNDED, border_style="bright_blue")
    table.add_column("Configuration", style="cyan", min_width=30)
    table.add_column("Leads", style="dim")
    table.add_column("DCA-CNN AUC", justify="right", style="bold")
    if ds_cnn:
        table.add_column("DS-1D-CNN AUC", justify="right")
        table.add_column("Δ", justify="right")

    for combo_name, leads in LEAD_COMBOS.items():
        r_dca = evaluate_with_leads(dca, X, Y, leads, "DCA-CNN")
        lead_str = "+".join([LEAD_NAMES[l] for l in leads])

        row = [combo_name, lead_str, f"{r_dca['macro_auc']:.4f}"]

        if ds_cnn:
            r_ds = evaluate_with_leads(ds_cnn, X, Y, leads, "DS-1D-CNN")
            delta = r_dca["macro_auc"] - r_ds["macro_auc"]
            delta_str = f"[green]+{delta:.4f}[/]" if delta >= 0 else f"[red]{delta:.4f}[/]"
            row.extend([f"{r_ds['macro_auc']:.4f}", delta_str])

        table.add_row(*row)
        results[combo_name] = {
            "leads": leads,
            "dca_cnn": r_dca["macro_auc"],
            "ds_1d_cnn": r_ds["macro_auc"] if ds_cnn else None,
        }

    console.print(table)
    return results


def run_cross_dataset_per_class(models, datasets):
    """Per-class AUC across datasets with 12/3/1-lead for DCA-CNN."""
    console.print(Panel("[bold cyan]CROSS-DATASET PER-CLASS (TOP/BOTTOM 5)[/]", expand=False))

    dca = models.get("DCA-CNN")
    if dca is None:
        return {}

    configs = {
        "12-lead": list(range(12)),
        "3-lead":  [0, 1, 2],
        "1-lead":  [1],
    }

    results = {}
    for ds_name, (X, Y) in datasets.items():
        ds_res = {}
        for cfg_name, leads in configs.items():
            r = evaluate_with_leads(dca, X, Y, leads, "DCA-CNN")
            ds_res[cfg_name] = r

            if cfg_name == "12-lead":
                pc = r.get("per_class", {})
                if pc:
                    sorted_classes = sorted(pc.items(), key=lambda x: x[1])
                    bottom5 = sorted_classes[:5]
                    top5 = sorted_classes[-5:]
                    console.print(f"\n  [bold]{ds_name}[/] — 12-lead (AUC={r['macro_auc']:.4f}):")
                    console.print(f"    Bottom 5: {', '.join([f'{n}={v:.3f}' for n,v in bottom5])}")
                    console.print(f"    Top 5:    {', '.join([f'{n}={v:.3f}' for n,v in top5])}")

        results[ds_name] = ds_res
    return results


def run_corruption_test(models, datasets):
    """Test model response when leads have corrupted/noisy data."""
    console.print(Panel("[bold cyan]LEAD CORRUPTION ROBUSTNESS[/]", expand=False))

    dca = models.get("DCA-CNN")
    if dca is None:
        return {}

    ds_name = "sph" if "sph" in datasets else list(datasets.keys())[0]
    X, Y = datasets[ds_name]

    scenarios = {
        "Clean (baseline)": lambda x: x.copy(),
        "Lead II random noise": lambda x: _corrupt_lead(x, 1, "noise"),
        "Lead V1 random noise": lambda x: _corrupt_lead(x, 6, "noise"),
        "Lead I+III flat (electrode off)": lambda x: _corrupt_leads_flat(x, [0, 2]),
        "V1-V3 flat (precordial partial)": lambda x: _corrupt_leads_flat(x, [6, 7, 8]),
        "All limb leads noisy": lambda x: _corrupt_leads_noise(x, [0, 1, 2, 3, 4, 5]),
        "Random 4 leads dropped": lambda x: _drop_random_leads(x, 4),
    }

    results = {}
    table = Table(title=f"Corruption Robustness — {ds_name}", box=box.ROUNDED)
    table.add_column("Scenario", style="cyan", min_width=35)
    table.add_column("Macro AUC", justify="right", style="bold")
    table.add_column("Δ from clean", justify="right")

    baseline_auc = None
    for scenario_name, corrupt_fn in scenarios.items():
        X_c = corrupt_fn(X)
        r = evaluate_with_leads(dca, X_c, Y, list(range(12)), "DCA-CNN")
        auc = r["macro_auc"]

        if baseline_auc is None:
            baseline_auc = auc
            delta_str = "—"
        else:
            delta = auc - baseline_auc
            delta_str = f"[red]{delta:+.4f}[/]" if delta < -0.01 else f"[yellow]{delta:+.4f}[/]"

        table.add_row(scenario_name, f"{auc:.4f}", delta_str)
        results[scenario_name] = round(auc, 4)

    console.print(table)
    return results


def _corrupt_lead(X, lead_idx, mode="noise"):
    X_c = X.copy()
    rng = np.random.RandomState(99)
    noise = rng.randn(X_c.shape[0], X_c.shape[2]).astype(np.float32) * 5.0
    X_c[:, lead_idx, :] = noise
    return X_c

def _corrupt_leads_flat(X, lead_indices):
    X_c = X.copy()
    for l in lead_indices:
        X_c[:, l, :] = 0.0
    return X_c

def _corrupt_leads_noise(X, lead_indices):
    X_c = X.copy()
    rng = np.random.RandomState(99)
    for l in lead_indices:
        noise = rng.randn(X_c.shape[0], X_c.shape[2]).astype(np.float32) * 3.0
        X_c[:, l, :] += noise
    return X_c

def _drop_random_leads(X, n_drop):
    X_c = X.copy()
    rng = np.random.RandomState(99)
    for i in range(len(X_c)):
        drop_leads = rng.choice(12, n_drop, replace=False)
        for l in drop_leads:
            X_c[i, l, :] = 0.0
    return X_c


def run_graceful_degradation(models, datasets):
    """Plot AUC vs number of active leads (1→12) to show graceful degradation."""
    console.print(Panel("[bold cyan]GRACEFUL DEGRADATION CURVE[/]", expand=False))

    dca = models.get("DCA-CNN")
    if dca is None:
        return {}

    ds_name = "sph" if "sph" in datasets else list(datasets.keys())[0]
    X, Y = datasets[ds_name]

    lead_priority = [1, 0, 2, 5, 10, 6, 7, 11, 8, 9, 3, 4]

    results = {}
    table = Table(title="Graceful Degradation: AUC vs Active Leads", box=box.ROUNDED)
    table.add_column("# Leads", justify="right", style="cyan")
    table.add_column("Active Leads", style="dim")
    table.add_column("Macro AUC", justify="right", style="bold")
    table.add_column("Bar", min_width=30)

    for n in range(1, 13):
        active = lead_priority[:n]
        r = evaluate_with_leads(dca, X, Y, active, "DCA-CNN")
        auc = r["macro_auc"]
        lead_str = ", ".join([LEAD_NAMES[l] for l in active])
        bar = "█" * int(auc * 30)
        table.add_row(str(n), lead_str, f"{auc:.4f}", f"[green]{bar}[/]")
        results[n] = {"leads": active, "auc": auc}

    console.print(table)
    return results


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    console.print(Panel(
        "[bold white]DCA-CNN COMPREHENSIVE MODEL ANALYSIS\n"
        "[dim]Per-lead ablation · Lead combinations · Cross-dataset\n"
        "Corruption robustness · Graceful degradation · Gate analysis[/]",
        border_style="bright_cyan", expand=False
    ))

    console.print("\n[bold]Loading datasets...[/]")
    datasets = load_datasets()

    console.print("\n[bold]Loading models...[/]")
    models = load_models()
    for name, m in models.items():
        p = sum(x.numel() for x in m.parameters())
        console.print(f"  [green]{name}[/]: {p:,} params")

    all_results = {}

    # 1. Gate analysis
    if "DCA-CNN" in models:
        all_results["gate_values"] = analyze_gate_values(models["DCA-CNN"])

    # 2. Single-lead ablation
    all_results["single_lead_ablation"] = run_lead_ablation(models, datasets)

    # 3. Lead combinations
    all_results["lead_combinations"] = run_lead_combinations(models, datasets)

    # 4. Cross-dataset per-class
    all_results["cross_dataset_per_class"] = run_cross_dataset_per_class(models, datasets)

    # 5. Corruption robustness
    all_results["corruption_robustness"] = run_corruption_test(models, datasets)

    # 6. Graceful degradation
    all_results["graceful_degradation"] = run_graceful_degradation(models, datasets)

    # Save
    out_path = RESULTS_DIR / "comprehensive_model_analysis.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    console.print(f"\n[bold green]Results saved:[/] {out_path}")
