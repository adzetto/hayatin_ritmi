"""
DCA-CNN Değerlendirme — Çoklu kanal konfigürasyonu ile cross-dataset test
=========================================================================
Eğitilmiş DCA-CNN modelini 1-lead, 3-lead, 12-lead konfigürasyonlarında
ve 6 veri seti üzerinde test eder.

Çalıştır:
    python ai/evaluation/evaluate_dca_cnn.py

Çıktılar:
    ai/models/results/dca_cnn_eval_results.json
    ai/models/results/dca_cnn_eval_detail.csv
"""

from __future__ import annotations

import os, sys, json, csv, time, glob
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ── Project paths ───────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR       = os.path.join(PROJECT_ROOT, "ai")
sys.path.insert(0, os.path.join(AI_DIR, "training"))

from train_dca_cnn import (
    DcaCNN, C_MAX, N_SAMPLES, NUM_CLASSES, SNOMED_MAP, CONDITION_NAMES,
    DEVICE, preprocess, parse_dx, load_snomed_map, LEAD_CONFIGS,
    CACHE_DIR, MODEL_DIR, RESULTS_DIR, SPH_PATH, EXTERNAL_DATASETS,
)

CHECKPOINT = os.path.join(MODEL_DIR, "ecg_dca_cnn_best.pt")


# ═══════════════════════════════════════════════════════════
#  Veri yükleme
# ═══════════════════════════════════════════════════════════
class NpDataset(Dataset):
    def __init__(self, X: np.ndarray, Y: np.ndarray):
        self.X = torch.from_numpy(X)
        self.Y = torch.from_numpy(Y)
    def __len__(self): return len(self.X)
    def __getitem__(self, i): return self.X[i], self.Y[i]


def load_dataset(name: str, path: str):
    """Cache varsa cache'den, yoksa raw'dan yükle."""
    cache = os.path.join(CACHE_DIR, f"cache_{name}.npz")
    if os.path.exists(cache):
        data = np.load(cache, allow_pickle=True)
        return data["X"], data["Y"]

    # Fallback: load from raw
    from train_dca_cnn import load_dataset_records
    X, Y = load_dataset_records(path)
    if len(X) > 0:
        np.savez_compressed(cache, X=X, Y=Y)
    return X, Y


def get_all_datasets() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Return dict name→(X, Y) for all available datasets."""
    datasets = {}

    # SPH
    sph_cache = os.path.join(CACHE_DIR, "dataset_cache.npz")
    if os.path.exists(sph_cache):
        data = np.load(sph_cache, allow_pickle=True)
        X, Y = data["X"], data["Y"]
        valid = np.isfinite(X).reshape(X.shape[0], -1).all(axis=1)
        datasets["sph"] = (X[valid], Y[valid])
    else:
        from train_dca_cnn import load_dataset_records
        datasets["sph"] = load_dataset_records(SPH_PATH)

    # External
    for ds_name, ds_path in EXTERNAL_DATASETS.items():
        if not os.path.exists(ds_path):
            continue
        X, Y = load_dataset(ds_name, ds_path)
        if len(X) > 0:
            datasets[ds_name] = (X, Y)

    return datasets


# ═══════════════════════════════════════════════════════════
#  Channel masking
# ═══════════════════════════════════════════════════════════
def mask_channels(x: torch.Tensor, n_ch: int) -> tuple[torch.Tensor, int]:
    """Zero out inactive channels for given config."""
    if n_ch >= 12:
        return x, 12
    active = LEAD_CONFIGS[n_ch]
    mask = torch.zeros(12, device=x.device, dtype=x.dtype)
    for a in active:
        mask[a] = 1.0
    return x * mask.view(1, 12, 1), n_ch


# ═══════════════════════════════════════════════════════════
#  Eval loop
# ═══════════════════════════════════════════════════════════
@torch.no_grad()
def evaluate_config(model: DcaCNN, loader: DataLoader, n_channels: int):
    """Evaluate model with specific channel configuration."""
    model.eval()
    all_preds, all_labels = [], []

    for xb, yb in loader:
        xb = xb.to(DEVICE, non_blocking=True)
        xb_masked, c_active = mask_channels(xb, n_channels)
        logits = model(xb_masked, c_active=c_active)
        probs = torch.sigmoid(logits).float().cpu().numpy()
        all_preds.append(probs)
        all_labels.append(yb.numpy())

    preds = np.nan_to_num(np.vstack(all_preds), nan=0.5, posinf=1.0, neginf=0.0)
    labels = np.vstack(all_labels)

    valid_cols = labels.sum(0) > 0
    if valid_cols.sum() == 0:
        return {"macro_auc": 0.0, "micro_auc": 0.0, "n_classes": 0, "n_samples": len(labels)}

    macro_auc = roc_auc_score(labels[:, valid_cols], preds[:, valid_cols], average="macro")
    micro_auc = roc_auc_score(labels[:, valid_cols], preds[:, valid_cols], average="micro")

    # Per-class AUC
    per_class = {}
    for ci in range(labels.shape[1]):
        if labels[:, ci].sum() > 0 and labels[:, ci].sum() < len(labels):
            auc_i = roc_auc_score(labels[:, ci], preds[:, ci])
            per_class[CONDITION_NAMES[ci]] = round(auc_i, 4)

    return {
        "macro_auc": round(macro_auc, 4),
        "micro_auc": round(micro_auc, 4),
        "n_classes": int(valid_cols.sum()),
        "n_samples": len(labels),
        "per_class_auc": per_class,
    }


def benchmark_speed(model: DcaCNN, n_ch: int, n_iters: int = 100):
    """Measure inference time for a single sample."""
    model.eval()
    dummy = torch.zeros(1, 12, N_SAMPLES, device=DEVICE)
    if n_ch < 12:
        dummy, _ = mask_channels(dummy, n_ch)

    # Warmup
    for _ in range(10):
        with torch.no_grad():
            model(dummy, c_active=n_ch)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()

    t0 = time.perf_counter()
    for _ in range(n_iters):
        with torch.no_grad():
            model(dummy, c_active=n_ch)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
    elapsed = (time.perf_counter() - t0) / n_iters * 1000  # ms
    return round(elapsed, 3)


# ═══════════════════════════════════════════════════════════
#  BASELINE comparison (DS-1D-CNN if available)
# ═══════════════════════════════════════════════════════════
def load_baseline_model():
    """Try loading the DS-1D-CNN baseline for comparison."""
    baseline_pt = os.path.join(MODEL_DIR, "ecg_best_combined.pt")
    if not os.path.exists(baseline_pt):
        return None
    try:
        sys.path.insert(0, os.path.join(AI_DIR, "training"))
        from train_pytorch import EcgDSCNN
        m = EcgDSCNN()
        m.load_state_dict(torch.load(baseline_pt, map_location=DEVICE, weights_only=True))
        m.to(DEVICE).eval()
        return m
    except Exception as e:
        console.print(f"  [yellow]Baseline yüklenemedi: {e}[/]")
        return None


@torch.no_grad()
def evaluate_baseline(model, loader: DataLoader):
    """Evaluate DS-1D-CNN baseline (12-lead only)."""
    model.eval()
    all_preds, all_labels = [], []
    for xb, yb in loader:
        xb = xb.to(DEVICE, non_blocking=True)
        logits = model(xb)
        probs = torch.sigmoid(logits).float().cpu().numpy()
        all_preds.append(probs)
        all_labels.append(yb.numpy())

    preds = np.nan_to_num(np.vstack(all_preds), nan=0.5, posinf=1.0, neginf=0.0)
    labels = np.vstack(all_labels)
    valid_cols = labels.sum(0) > 0
    if valid_cols.sum() == 0:
        return 0.0
    return round(roc_auc_score(labels[:, valid_cols], preds[:, valid_cols], average="macro"), 4)


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold white]DCA-CNN DEĞERLENDİRME[/]\n"
        "[cyan]Cross-Dataset · Multi-Channel · Benchmark[/]\n"
        "[dim]TÜBİTAK 2209-A — Hayatın Ritmi[/]",
        border_style="bright_cyan", box=box.DOUBLE_EDGE, padding=(1, 4),
    ))

    # ── Load model ──
    if not os.path.exists(CHECKPOINT):
        console.print(f"[bold red]❌ Model checkpoint bulunamadı: {CHECKPOINT}[/]")
        sys.exit(1)

    model = DcaCNN().to(DEVICE)
    model.load_state_dict(torch.load(CHECKPOINT, map_location=DEVICE, weights_only=True))
    model.eval()

    total_params = sum(p.numel() for p in model.parameters())
    console.print(f"  [green]✅ Model yüklendi:[/] {total_params:,} params")

    # ── Load baseline ──
    baseline = load_baseline_model()
    if baseline:
        baseline_params = sum(p.numel() for p in baseline.parameters())
        console.print(f"  [green]✅ Baseline (DS-1D-CNN) yüklendi:[/] {baseline_params:,} params")

    # ── Load datasets ──
    console.print("\n[bold cyan]📦 Veri setleri yükleniyor...[/]")
    datasets = get_all_datasets()
    console.print(f"  [green]{len(datasets)} veri seti bulundu[/]\n")

    # ── Evaluate ──
    all_results = {}
    csv_rows = []

    for ds_name, (X, Y) in datasets.items():
        console.print(f"\n  [bold magenta]━━ {ds_name} ({len(X):,} kayıt) ━━[/]")

        # Use test split only: last 15% for SPH, last 15% for external
        n = len(X)
        if ds_name == "sph":
            rng = np.random.RandomState(42)
            idx = rng.permutation(n)
            test_idx = idx[int(n * 0.85):]
        else:
            rng = np.random.RandomState(42)
            idx = rng.permutation(n)
            test_idx = idx[int(n * 0.85):]

        X_test, Y_test = X[test_idx], Y[test_idx]
        if len(X_test) == 0:
            continue

        loader = DataLoader(NpDataset(X_test, Y_test),
                            batch_size=256, shuffle=False, num_workers=2)

        ds_results = {}

        # DCA-CNN: 12-lead, 3-lead, 1-lead
        for n_ch in [12, 3, 1]:
            label = f"{n_ch}-lead"
            console.print(f"    {label}...", end=" ")
            result = evaluate_config(model, loader, n_ch)
            ds_results[label] = result
            console.print(f"Macro AUC = [bold]{result['macro_auc']:.4f}[/], "
                          f"Micro AUC = {result['micro_auc']:.4f} "
                          f"({result['n_classes']} classes)")

            csv_rows.append({
                "dataset": ds_name, "model": "DCA-CNN", "config": label,
                "macro_auc": result["macro_auc"], "micro_auc": result["micro_auc"],
                "n_classes": result["n_classes"], "n_samples": result["n_samples"],
            })

        # Baseline comparison (12-lead only)
        if baseline:
            b_auc = evaluate_baseline(baseline, loader)
            ds_results["baseline_12lead"] = b_auc
            console.print(f"    [dim]Baseline 12-lead: Macro AUC = {b_auc:.4f}[/]")
            csv_rows.append({
                "dataset": ds_name, "model": "DS-1D-CNN", "config": "12-lead",
                "macro_auc": b_auc, "micro_auc": "", "n_classes": "", "n_samples": len(X_test),
            })

        all_results[ds_name] = ds_results

    # ── Speed benchmark ──
    console.print("\n[bold cyan]⏱️  Inference Benchmark[/]")
    speed_table = Table(box=box.ROUNDED, border_style="cyan")
    speed_table.add_column("Config", style="cyan")
    speed_table.add_column("Latency (ms)", style="bold white", justify="right")

    speed_results = {}
    for n_ch in [12, 3, 1]:
        ms = benchmark_speed(model, n_ch)
        speed_results[f"{n_ch}-lead"] = ms
        speed_table.add_row(f"{n_ch}-lead", f"{ms:.3f}")
    console.print(speed_table)

    # ── FLOPs / params comparison ──
    param_table = Table(box=box.ROUNDED, border_style="cyan", title="[bold]Model Karşılaştırması[/]")
    param_table.add_column("Model", style="cyan")
    param_table.add_column("Params", style="bold white", justify="right")
    param_table.add_row("DCA-CNN", f"{total_params:,}")
    if baseline:
        param_table.add_row("DS-1D-CNN (baseline)", f"{baseline_params:,}")
    console.print(param_table)

    # ── Results summary table ──
    console.print()
    summary_table = Table(box=box.DOUBLE_EDGE, title="[bold green]📊 Sonuç Özeti[/]",
                          border_style="green")
    summary_table.add_column("Dataset", style="cyan")
    summary_table.add_column("12-lead", style="bold white", justify="center")
    summary_table.add_column("3-lead", style="bold white", justify="center")
    summary_table.add_column("1-lead", style="bold white", justify="center")
    if baseline:
        summary_table.add_column("Baseline", style="dim", justify="center")

    for ds_name, r in all_results.items():
        row = [ds_name]
        for ch in ["12-lead", "3-lead", "1-lead"]:
            if ch in r:
                row.append(f"{r[ch]['macro_auc']:.4f}")
            else:
                row.append("-")
        if baseline and "baseline_12lead" in r:
            row.append(f"{r['baseline_12lead']:.4f}")
        elif baseline:
            row.append("-")
        summary_table.add_row(*row)

    console.print(summary_table)

    # ── Save results ──
    json_path = os.path.join(RESULTS_DIR, "dca_cnn_eval_results.json")
    save_data = {
        "model": "DCA-CNN",
        "params": total_params,
        "speed_ms": speed_results,
        "results": {},
    }
    for ds_name, r in all_results.items():
        save_data["results"][ds_name] = {}
        for k, v in r.items():
            if isinstance(v, dict) and "per_class_auc" in v:
                v_copy = dict(v)
                v_copy.pop("per_class_auc", None)
                save_data["results"][ds_name][k] = v_copy
            else:
                save_data["results"][ds_name][k] = v

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(RESULTS_DIR, "dca_cnn_eval_detail.csv")
    if csv_rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            writer.writeheader()
            writer.writerows(csv_rows)

    console.print(f"\n[bold green]✅ Sonuçlar kaydedildi:[/]")
    console.print(f"   JSON: {json_path}")
    console.print(f"   CSV:  {csv_path}")
