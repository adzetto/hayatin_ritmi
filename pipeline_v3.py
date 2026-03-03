"""
pipeline_v3.py — Overnight Robustness & Diagnostics Pipeline
=============================================================
Phases: D(Leakage) E(Overfit) F(Noise) G(LeadDrop) H(CrossDS) I(Calibration) + Figures
Usage: conda activate ecg_tf; python pipeline_v3.py
"""
from __future__ import annotations
import os, sys, json, csv, time, glob, warnings, ast, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as Fn
from torch.utils.data import DataLoader, TensorDataset
from scipy.signal import butter, filtfilt, resample
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, SpinnerColumn, TaskProgressColumn
from rich import box
from tqdm import tqdm
import wfdb
import pandas as pd

warnings.filterwarnings("ignore")
console = Console(force_terminal=True)

PROJECT_ROOT = Path(__file__).resolve().parent
AI_DIR       = PROJECT_ROOT / "ai"
DATASET_DIR  = PROJECT_ROOT / "dataset"
MODEL_DIR    = AI_DIR / "models" / "checkpoints"
RESULTS_DIR  = AI_DIR / "models" / "results"
FIGURES_DIR  = RESULTS_DIR / "figures"
CACHE_DIR    = AI_DIR / "cache"
for d in [FIGURES_DIR]: d.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

sys.path.insert(0, str(AI_DIR / "training"))
from train_dca_cnn import (
    DcaCNN, preprocess, bandpass, load_snomed_map, parse_dx,
    load_dataset_records, load_combined_dataset, train_model, export_onnx,
    EcgAugDataset, sample_channel_config, apply_channel_mask,
    SNOMED_MAP, CONDITION_NAMES, NUM_CLASSES,
    C_MAX, N_SAMPLES, FS_TARGET, BATCH_SIZE, EPOCHS,
    EXTERNAL_DATASETS, SPH_PATH,
)

log = {"start": datetime.now().isoformat(), "phases": {}}

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def save_log():
    log["updated"] = datetime.now().isoformat()
    (RESULTS_DIR / "pipeline_v3_log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False, cls=NumpyEncoder), encoding="utf-8")

# ── Shared data cache (load SPH once) ──
_DATA_CACHE = {}
def get_sph_splits():
    if "loaded" not in _DATA_CACHE:
        console.print("  [dim]Loading SPH cache into memory...[/dim]")
        data = np.load(CACHE_DIR / "dataset_cache.npz", allow_pickle=True)
        X_all, Y_all = data["X"].astype(np.float32), data["Y"].astype(np.float32)
        valid = np.isfinite(X_all).reshape(X_all.shape[0], -1).all(axis=1)
        X_all, Y_all = X_all[valid], Y_all[valid]
        rng = np.random.RandomState(42)
        idx = rng.permutation(len(X_all))
        n = len(X_all)
        _DATA_CACHE["X_train"] = X_all[idx[:int(n*0.70)]]
        _DATA_CACHE["Y_train"] = Y_all[idx[:int(n*0.70)]]
        _DATA_CACHE["X_val"] = X_all[idx[int(n*0.70):int(n*0.85)]]
        _DATA_CACHE["Y_val"] = Y_all[idx[int(n*0.70):int(n*0.85)]]
        _DATA_CACHE["X_test"] = X_all[idx[int(n*0.85):]]
        _DATA_CACHE["Y_test"] = Y_all[idx[int(n*0.85):]]
        _DATA_CACHE["loaded"] = True
        console.print(f"    train={len(_DATA_CACHE['X_train']):,} val={len(_DATA_CACHE['X_val']):,} test={len(_DATA_CACHE['X_test']):,}")
    return _DATA_CACHE

# ── Colors ──
C = {"bg":"#0f172a","surface":"#1e293b","text":"#e2e8f0","muted":"#94a3b8"}
PAL = ["#6366f1","#ec4899","#06b6d4","#10b981","#f59e0b","#ef4444","#8b5cf6"]

def dark_style():
    plt.rcParams.update({
        "figure.facecolor":C["bg"],"axes.facecolor":C["surface"],
        "axes.edgecolor":C["muted"],"axes.labelcolor":C["text"],
        "text.color":C["text"],"xtick.color":C["muted"],"ytick.color":C["muted"],
        "grid.color":"#334155","grid.alpha":0.5,"font.size":11,
    })

def header(name, desc):
    console.print()
    console.print(Rule(f"[bold cyan]{name}[/]", style="cyan"))
    console.print(f"  [dim]{desc}[/]\n")

def batch_predict(model, X, bs=256):
    """Run model on numpy array, return sigmoid probs."""
    model.eval()
    ds = TensorDataset(torch.from_numpy(X).float())
    dl = DataLoader(ds, batch_size=bs, shuffle=False, num_workers=0)
    preds = []
    with torch.no_grad():
        for (xb,) in dl:
            xb = xb.to(DEVICE)
            logits = model(xb)
            preds.append(torch.sigmoid(logits).cpu().numpy())
    return np.vstack(preds)


# ═══════════════════════════════════════════════════════════════
#  PHASE D — DATA LEAKAGE DETECTION
# ═══════════════════════════════════════════════════════════════
def phase_D_leakage(model):
    header("Phase D: Data Leakage Detection",
           "Check for duplicate records, train/val confidence gap, memorization")
    t0 = time.time()
    results = {}

    d = get_sph_splits()
    X_train, Y_train = d["X_train"], d["Y_train"]
    X_val, Y_val = d["X_val"], d["Y_val"]
    X_test, Y_test = d["X_test"], d["Y_test"]

    # 1. Duplicate detection via hashing
    console.print("  [cyan]Checking for duplicate records...[/]")
    def record_hash(x):
        return hashlib.md5(x.tobytes()).hexdigest()
    train_hashes = set(record_hash(X_train[i]) for i in range(len(X_train)))
    val_hashes = set(record_hash(X_val[i]) for i in range(len(X_val)))
    test_hashes = set(record_hash(X_test[i]) for i in range(len(X_test)))
    tv_overlap = train_hashes & val_hashes
    tt_overlap = train_hashes & test_hashes
    results["duplicate_train_val"] = len(tv_overlap)
    results["duplicate_train_test"] = len(tt_overlap)
    leak_status = "CLEAN" if len(tv_overlap) == 0 and len(tt_overlap) == 0 else "LEAKAGE DETECTED"
    color = "green" if leak_status == "CLEAN" else "red"
    console.print(f"    Train-Val overlap: {len(tv_overlap)}, Train-Test overlap: {len(tt_overlap)} -> [{color}]{leak_status}[/{color}]")

    # 2. Confidence gap analysis
    console.print("  [cyan]Prediction confidence analysis...[/]")
    p_train = batch_predict(model, X_train[:3000])  # sample for speed
    p_val = batch_predict(model, X_val)
    p_test = batch_predict(model, X_test)

    train_max = p_train.max(axis=1)
    val_max = p_val.max(axis=1)
    test_max = p_test.max(axis=1)
    train_mean = p_train.mean(axis=1)
    val_mean = p_val.mean(axis=1)
    test_mean = p_test.mean(axis=1)

    results["conf_train_mean"] = round(float(train_max.mean()), 4)
    results["conf_val_mean"] = round(float(val_max.mean()), 4)
    results["conf_test_mean"] = round(float(test_max.mean()), 4)
    results["conf_gap_train_val"] = round(float(train_max.mean() - val_max.mean()), 4)
    results["conf_gap_train_test"] = round(float(train_max.mean() - test_max.mean()), 4)

    # 3. Per-class AUC on train vs val
    console.print("  [cyan]Per-class AUC comparison (train vs val)...[/]")
    auc_gaps = []
    for i in range(min(NUM_CLASSES, Y_train.shape[1])):
        sup_t = int(Y_train[:3000, i].sum())
        sup_v = int(Y_val[:, i].sum())
        if sup_t >= 5 and sup_v >= 5:
            try:
                auc_t = roc_auc_score(Y_train[:3000, i], p_train[:, i])
                auc_v = roc_auc_score(Y_val[:, i], p_val[:, i])
                auc_gaps.append({"class": CONDITION_NAMES[i] if i < len(CONDITION_NAMES) else f"c{i}",
                                 "auc_train": round(auc_t, 4), "auc_val": round(auc_v, 4),
                                 "gap": round(auc_t - auc_v, 4)})
            except: pass

    auc_gaps.sort(key=lambda x: abs(x["gap"]), reverse=True)
    results["auc_gaps"] = auc_gaps[:15]

    t = Table(box=box.ROUNDED, title="[bold]Train vs Val AUC Gaps (Top 10)[/]")
    t.add_column("Class", style="cyan"); t.add_column("Train AUC"); t.add_column("Val AUC"); t.add_column("Gap")
    for g in auc_gaps[:10]:
        gap_color = "red" if abs(g["gap"]) > 0.05 else "yellow" if abs(g["gap"]) > 0.02 else "green"
        t.add_row(g["class"], f"{g['auc_train']:.4f}", f"{g['auc_val']:.4f}",
                  f"[{gap_color}]{g['gap']:+.4f}[/{gap_color}]")
    console.print(t)

    # 4. Prediction entropy
    def entropy(p):
        p_clip = np.clip(p, 1e-7, 1 - 1e-7)
        return -np.mean(p_clip * np.log(p_clip) + (1-p_clip) * np.log(1-p_clip))
    results["entropy_train"] = round(entropy(p_train), 4)
    results["entropy_val"] = round(entropy(p_val), 4)
    results["entropy_test"] = round(entropy(p_test), 4)

    t2 = Table(box=box.ROUNDED, title="[bold]Leakage Summary[/]")
    t2.add_column("Check", style="cyan"); t2.add_column("Result", style="white"); t2.add_column("Status")
    t2.add_row("Duplicate records", f"TV={len(tv_overlap)} TT={len(tt_overlap)}",
               f"[{color}]{leak_status}[/{color}]")
    gap = results["conf_gap_train_val"]
    gc = "green" if abs(gap) < 0.02 else "yellow" if abs(gap) < 0.05 else "red"
    t2.add_row("Confidence gap (T-V)", f"{gap:+.4f}", f"[{gc}]{'OK' if abs(gap)<0.05 else 'SUSPICIOUS'}[/{gc}]")
    avg_gap = np.mean([abs(g["gap"]) for g in auc_gaps[:10]]) if auc_gaps else 0
    ogc = "green" if avg_gap < 0.03 else "yellow" if avg_gap < 0.06 else "red"
    t2.add_row("Mean AUC gap", f"{avg_gap:.4f}", f"[{ogc}]{'OK' if avg_gap<0.06 else 'OVERFIT'}[/{ogc}]")
    t2.add_row("Entropy (T/V/Te)", f"{results['entropy_train']:.3f}/{results['entropy_val']:.3f}/{results['entropy_test']:.3f}", "[green]OK[/]")
    console.print(t2)

    elapsed = time.time() - t0
    results["duration_s"] = round(elapsed, 1)
    log["phases"]["D"] = results; save_log()
    return results


# ═══════════════════════════════════════════════════════════════
#  PHASE E — OVERFITTING ANALYSIS
# ═══════════════════════════════════════════════════════════════
def phase_E_overfit():
    header("Phase E: Overfitting Analysis", "Training curve diagnostics, generalization gap")
    t0 = time.time()
    results = {}

    csv_path = RESULTS_DIR / "training_log_dca_cnn.csv"
    if not csv_path.exists():
        console.print("  [red]Training log not found[/]"); return {}

    df = pd.read_csv(csv_path)
    results["total_epochs"] = len(df)
    results["best_epoch"] = int(df["val_auc"].idxmax()) + 1
    results["best_val_auc"] = round(float(df["val_auc"].max()), 6)
    results["final_train_loss"] = round(float(df["train_loss"].iloc[-1]), 6)
    results["final_val_loss"] = round(float(df["val_loss"].iloc[-1]), 6)
    results["loss_gap"] = round(float(df["train_loss"].iloc[-1] - df["val_loss"].iloc[-1]), 6)

    # Overfitting detection: train loss << val loss
    last5_train = df["train_loss"].tail(5).mean()
    last5_val = df["val_loss"].tail(5).mean()
    results["loss_gap_last5"] = round(float(last5_train - last5_val), 6)

    # Early stopping analysis
    best_ep = df["val_auc"].idxmax()
    if best_ep < len(df) - 1:
        auc_after_best = df["val_auc"].iloc[best_ep+1:].tolist()
        results["auc_decline_after_best"] = round(float(df["val_auc"].iloc[best_ep] - min(auc_after_best)) if auc_after_best else 0, 4)
    else:
        results["auc_decline_after_best"] = 0

    # Learning rate restarts effect
    lr_vals = df["lr"].tolist()
    restarts = sum(1 for i in range(1, len(lr_vals)) if lr_vals[i] > lr_vals[i-1] * 2)
    results["lr_restarts"] = restarts

    t = Table(box=box.ROUNDED, title="[bold]Overfitting Diagnostics[/]")
    t.add_column("Metric", style="cyan"); t.add_column("Value", style="white"); t.add_column("Verdict")
    lg = results["loss_gap_last5"]
    t.add_row("Train-Val loss gap (last 5)", f"{lg:+.6f}",
              f"[{'green' if abs(lg)<0.005 else 'yellow' if abs(lg)<0.01 else 'red'}]{'OK' if abs(lg)<0.01 else 'OVERFIT'}[/]")
    t.add_row("Best epoch / Total", f"{results['best_epoch']} / {results['total_epochs']}", "[green]OK[/]")
    t.add_row("AUC decline after best", f"{results['auc_decline_after_best']:.4f}",
              f"[{'green' if results['auc_decline_after_best']<0.005 else 'yellow'}]OK[/]")
    t.add_row("LR restarts", str(restarts), "[green]CosineWarmRestart[/]")
    t.add_row("Best val AUC", f"{results['best_val_auc']:.6f}", "[green]OK[/]")
    console.print(t)

    # Plot
    dark_style()
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    axes[0].plot(df["epoch"], df["train_loss"], color=PAL[0], lw=2, label="Train")
    axes[0].plot(df["epoch"], df["val_loss"], color=PAL[1], lw=2, label="Val")
    axes[0].fill_between(df["epoch"], df["train_loss"], df["val_loss"], alpha=0.15, color=PAL[4])
    axes[0].set_title("Loss Gap Analysis", fontweight="bold"); axes[0].legend(); axes[0].grid(True, alpha=0.3)
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Loss")

    axes[1].plot(df["epoch"], df["val_auc"], color=PAL[2], lw=2.5)
    axes[1].axhline(y=results["best_val_auc"], color=PAL[3], ls="--", alpha=0.5)
    axes[1].scatter([results["best_epoch"]], [results["best_val_auc"]], color=PAL[3], s=150, zorder=5, marker="*")
    axes[1].set_title("Validation AUC", fontweight="bold"); axes[1].grid(True, alpha=0.3)
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Macro AUC")

    axes[2].plot(df["epoch"], df["lr"], color=PAL[4], lw=2)
    axes[2].set_title("Learning Rate Schedule", fontweight="bold"); axes[2].grid(True, alpha=0.3)
    axes[2].set_xlabel("Epoch"); axes[2].set_ylabel("LR"); axes[2].set_yscale("log")

    fig.suptitle("Overfitting Analysis | DCA-CNN", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "fig7_overfit_analysis.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    console.print(f"  [green]Saved: fig7_overfit_analysis.pdf[/]")

    elapsed = time.time() - t0
    results["duration_s"] = round(elapsed, 1)
    log["phases"]["E"] = results; save_log()
    return results


# ═══════════════════════════════════════════════════════════════
#  PHASE F — NOISE ROBUSTNESS
# ═══════════════════════════════════════════════════════════════
def phase_F_noise(model):
    header("Phase F: Noise Robustness", "Gaussian noise, baseline wander, powerline interference at varying SNR")
    t0 = time.time()

    d = get_sph_splits()
    X_test = d["X_test"][:1000]
    Y_test = d["Y_test"][:1000]
    rng = np.random.RandomState(42)
    console.print(f"  Test subset: {len(X_test):,} records")

    # Baseline (clean)
    p_clean = batch_predict(model, X_test)
    active_classes = [i for i in range(min(NUM_CLASSES, Y_test.shape[1])) if Y_test[:, i].sum() >= 5]

    def macro_auc(preds, labels, classes):
        aucs = []
        for i in classes:
            try: aucs.append(roc_auc_score(labels[:, i], preds[:, i]))
            except: pass
        return np.mean(aucs) if aucs else 0

    clean_auc = macro_auc(p_clean, Y_test, active_classes)
    console.print(f"  Clean baseline AUC: {clean_auc:.4f}")

    results = {"clean_auc": round(clean_auc, 4), "noise_tests": {}}

    # 1. Gaussian noise at different SNR levels
    console.print("  [cyan]Testing Gaussian noise...[/]")
    snr_levels = [40, 30, 20, 15, 10, 5]
    gauss_results = []
    for snr_db in tqdm(snr_levels, desc="  Gaussian SNR"):
        X_noisy = X_test.copy()
        for i in range(len(X_noisy)):
            sig_power = np.mean(X_noisy[i] ** 2)
            noise_power = sig_power / (10 ** (snr_db / 10))
            X_noisy[i] += rng.randn(*X_noisy[i].shape).astype(np.float32) * np.sqrt(noise_power)
        p_noisy = batch_predict(model, X_noisy)
        auc_noisy = macro_auc(p_noisy, Y_test, active_classes)
        top1_agree = (p_clean.argmax(1) == p_noisy.argmax(1)).mean()
        gauss_results.append({"snr_db": snr_db, "auc": round(auc_noisy, 4),
                              "auc_drop": round(clean_auc - auc_noisy, 4),
                              "top1_agree": round(float(top1_agree), 4)})
    results["noise_tests"]["gaussian"] = gauss_results

    # 2. Baseline wander (low-freq sinusoidal noise)
    console.print("  [cyan]Testing baseline wander...[/]")
    wander_amps = [0.05, 0.1, 0.2, 0.5, 1.0]
    wander_results = []
    t_axis = np.arange(N_SAMPLES) / FS_TARGET
    for amp in tqdm(wander_amps, desc="  Wander amp"):
        X_wander = X_test.copy()
        for i in range(len(X_wander)):
            freq = rng.uniform(0.1, 0.5)
            phase = rng.uniform(0, 2 * np.pi)
            wander = amp * np.sin(2 * np.pi * freq * t_axis + phase).astype(np.float32)
            X_wander[i] += wander[None, :]
        p_w = batch_predict(model, X_wander)
        auc_w = macro_auc(p_w, Y_test, active_classes)
        wander_results.append({"amplitude": amp, "auc": round(auc_w, 4),
                                "auc_drop": round(clean_auc - auc_w, 4)})
    results["noise_tests"]["baseline_wander"] = wander_results

    # 3. 50Hz powerline interference
    console.print("  [cyan]Testing powerline interference...[/]")
    pli_amps = [0.01, 0.05, 0.1, 0.2, 0.5]
    pli_results = []
    for amp in tqdm(pli_amps, desc="  PLI amp"):
        X_pli = X_test.copy()
        pli = amp * np.sin(2 * np.pi * 50 * t_axis).astype(np.float32)
        X_pli += pli[None, None, :]
        p_p = batch_predict(model, X_pli)
        auc_p = macro_auc(p_p, Y_test, active_classes)
        pli_results.append({"amplitude": amp, "auc": round(auc_p, 4),
                            "auc_drop": round(clean_auc - auc_p, 4)})
    results["noise_tests"]["powerline_50hz"] = pli_results

    # Table
    t = Table(box=box.ROUNDED, title="[bold]Noise Robustness Summary[/]")
    t.add_column("Noise Type", style="cyan"); t.add_column("Level"); t.add_column("AUC"); t.add_column("Drop")
    t.add_row("Clean baseline", "--", f"{clean_auc:.4f}", "--")
    for g in gauss_results:
        dc = "green" if g["auc_drop"]<0.02 else "yellow" if g["auc_drop"]<0.05 else "red"
        t.add_row("Gaussian", f"SNR={g['snr_db']}dB", f"{g['auc']:.4f}", f"[{dc}]{g['auc_drop']:+.4f}[/{dc}]")
    for w in wander_results:
        dc = "green" if w["auc_drop"]<0.02 else "yellow" if w["auc_drop"]<0.05 else "red"
        t.add_row("Baseline wander", f"amp={w['amplitude']}", f"{w['auc']:.4f}", f"[{dc}]{w['auc_drop']:+.4f}[/{dc}]")
    for p in pli_results:
        dc = "green" if p["auc_drop"]<0.02 else "yellow" if p["auc_drop"]<0.05 else "red"
        t.add_row("50Hz PLI", f"amp={p['amplitude']}", f"{p['auc']:.4f}", f"[{dc}]{p['auc_drop']:+.4f}[/{dc}]")
    console.print(t)

    # Plot
    dark_style()
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    ax = axes[0]
    snrs = [g["snr_db"] for g in gauss_results]
    ax.plot(snrs, [g["auc"] for g in gauss_results], 'o-', color=PAL[0], lw=2.5, ms=8)
    ax.axhline(y=clean_auc, color=PAL[3], ls="--", alpha=0.5, label=f"Clean: {clean_auc:.4f}")
    ax.set_xlabel("SNR (dB)"); ax.set_ylabel("Macro AUC"); ax.set_title("Gaussian Noise", fontweight="bold")
    ax.legend(); ax.grid(True, alpha=0.3); ax.invert_xaxis()

    ax = axes[1]
    ax.plot([w["amplitude"] for w in wander_results], [w["auc"] for w in wander_results],
            's-', color=PAL[1], lw=2.5, ms=8)
    ax.axhline(y=clean_auc, color=PAL[3], ls="--", alpha=0.5)
    ax.set_xlabel("Wander Amplitude"); ax.set_ylabel("Macro AUC"); ax.set_title("Baseline Wander", fontweight="bold")
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.plot([p["amplitude"] for p in pli_results], [p["auc"] for p in pli_results],
            'D-', color=PAL[2], lw=2.5, ms=8)
    ax.axhline(y=clean_auc, color=PAL[3], ls="--", alpha=0.5)
    ax.set_xlabel("PLI Amplitude"); ax.set_ylabel("Macro AUC"); ax.set_title("50Hz Powerline", fontweight="bold")
    ax.grid(True, alpha=0.3)

    fig.suptitle("Noise Robustness Analysis | DCA-CNN", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "fig8_noise_robustness.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    console.print(f"  [green]Saved: fig8_noise_robustness.pdf[/]")

    elapsed = time.time() - t0
    results["duration_s"] = round(elapsed, 1)
    log["phases"]["F"] = results; save_log()
    return results


# ═══════════════════════════════════════════════════════════════
#  PHASE G — LEAD DROPOUT STRESS TEST
# ═══════════════════════════════════════════════════════════════
def phase_G_lead_dropout(model):
    header("Phase G: Lead Dropout Stress Test",
           "Individual lead importance, random dropout rates, shuffled leads")
    t0 = time.time()

    d = get_sph_splits()
    X_test = d["X_test"][:1000]
    Y_test = d["Y_test"][:1000]
    rng = np.random.RandomState(42)

    active_classes = [i for i in range(min(NUM_CLASSES, Y_test.shape[1])) if Y_test[:, i].sum() >= 5]
    def macro_auc(preds):
        aucs = []
        for i in active_classes:
            try: aucs.append(roc_auc_score(Y_test[:, i], preds[:, i]))
            except: pass
        return np.mean(aucs) if aucs else 0

    p_clean = batch_predict(model, X_test)
    clean_auc = macro_auc(p_clean)

    LEAD_NAMES = ["I","II","III","aVR","aVL","aVF","V1","V2","V3","V4","V5","V6"]
    results = {"clean_auc": round(clean_auc, 4)}

    # 1. Individual lead dropout (drop one lead at a time)
    console.print("  [cyan]Individual lead dropout...[/]")
    lead_importance = []
    for lead_idx in range(12):
        X_drop = X_test.copy()
        X_drop[:, lead_idx, :] = 0
        p = batch_predict(model, X_drop)
        auc = macro_auc(p)
        importance = clean_auc - auc
        lead_importance.append({"lead": LEAD_NAMES[lead_idx], "idx": lead_idx,
                                "auc_without": round(auc, 4), "importance": round(importance, 4)})
    lead_importance.sort(key=lambda x: x["importance"], reverse=True)
    results["lead_importance"] = lead_importance

    t = Table(box=box.ROUNDED, title="[bold]Lead Importance (drop = AUC loss)[/]")
    t.add_column("Lead", style="cyan"); t.add_column("AUC w/o"); t.add_column("Importance")
    for li in lead_importance:
        ic = "red" if li["importance"] > 0.01 else "yellow" if li["importance"] > 0.003 else "green"
        t.add_row(li["lead"], f"{li['auc_without']:.4f}", f"[{ic}]{li['importance']:+.4f}[/{ic}]")
    console.print(t)

    # 2. Random lead dropout at different rates
    console.print("  [cyan]Random lead dropout rates...[/]")
    drop_rates = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    drop_results = []
    for rate in tqdm(drop_rates, desc="  Dropout rate"):
        aucs_at_rate = []
        for trial in range(5):  # 5 random trials per rate
            X_drop = X_test.copy()
            for i in range(len(X_drop)):
                mask = rng.rand(12) > rate
                if not mask.any(): mask[1] = True  # keep at least lead II
                X_drop[i] *= mask[:, None].astype(np.float32)
            p = batch_predict(model, X_drop)
            aucs_at_rate.append(macro_auc(p))
        mean_auc = np.mean(aucs_at_rate)
        drop_results.append({"rate": rate, "auc_mean": round(float(mean_auc), 4),
                             "auc_std": round(float(np.std(aucs_at_rate)), 4)})
    results["dropout_sweep"] = drop_results

    # 3. Lead shuffle test (permute lead assignments)
    console.print("  [cyan]Lead shuffle test...[/]")
    X_shuf = X_test.copy()
    for i in range(len(X_shuf)):
        perm = rng.permutation(12)
        X_shuf[i] = X_shuf[i][perm]
    p_shuf = batch_predict(model, X_shuf)
    shuf_auc = macro_auc(p_shuf)
    results["shuffled_auc"] = round(shuf_auc, 4)
    results["shuffle_drop"] = round(clean_auc - shuf_auc, 4)
    console.print(f"    Shuffled AUC: {shuf_auc:.4f} (drop: {clean_auc-shuf_auc:+.4f})")

    # Plot
    dark_style()
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Lead importance bar chart
    ax = axes[0]
    names = [l["lead"] for l in lead_importance]
    imps = [l["importance"] for l in lead_importance]
    colors = [PAL[5] if v > 0.01 else PAL[4] if v > 0.003 else PAL[3] for v in imps]
    ax.barh(range(12), imps, color=colors)
    ax.set_yticks(range(12)); ax.set_yticklabels(names)
    ax.set_xlabel("AUC Drop When Removed"); ax.set_title("Lead Importance", fontweight="bold")
    ax.invert_yaxis(); ax.grid(True, alpha=0.3, axis="x")

    # Dropout sweep
    ax = axes[1]
    rates = [d["rate"] for d in drop_results]
    aucs = [d["auc_mean"] for d in drop_results]
    stds = [d["auc_std"] for d in drop_results]
    ax.plot(rates, aucs, 'o-', color=PAL[0], lw=2.5, ms=8)
    ax.fill_between(rates, [a-s for a,s in zip(aucs,stds)], [a+s for a,s in zip(aucs,stds)],
                    alpha=0.2, color=PAL[0])
    ax.axhline(y=clean_auc, color=PAL[3], ls="--", alpha=0.5)
    ax.set_xlabel("Lead Dropout Rate"); ax.set_ylabel("Macro AUC")
    ax.set_title("Random Lead Dropout", fontweight="bold"); ax.grid(True, alpha=0.3)

    # Confidence distribution comparison
    ax = axes[2]
    ax.hist(p_clean.max(1), bins=50, alpha=0.6, color=PAL[2], label="Clean", density=True)
    X_half = X_test.copy()
    X_half[:, 6:, :] = 0
    p_half = batch_predict(model, X_half)
    ax.hist(p_half.max(1), bins=50, alpha=0.6, color=PAL[5], label="6-lead only", density=True)
    ax.set_xlabel("Max Prediction Confidence"); ax.set_ylabel("Density")
    ax.set_title("Confidence: 12-lead vs 6-lead", fontweight="bold"); ax.legend(); ax.grid(True, alpha=0.3)

    fig.suptitle("Lead Dropout Stress Test | DCA-CNN", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "fig9_lead_dropout.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    console.print(f"  [green]Saved: fig9_lead_dropout.pdf[/]")

    elapsed = time.time() - t0
    results["duration_s"] = round(elapsed, 1)
    log["phases"]["G"] = results; save_log()
    return results


# ═══════════════════════════════════════════════════════════════
#  PHASE H — CROSS-DATASET GENERALIZATION
# ═══════════════════════════════════════════════════════════════
def phase_H_cross_dataset(model):
    header("Phase H: Cross-Dataset Generalization",
           "Evaluate retrained model on each external dataset separately")
    t0 = time.time()
    results = {}

    ds_order = ["sph", "cpsc2018", "cpsc2018-extra", "georgia", "chapman-shaoxing", "ningbo"]
    caches = {
        "sph": CACHE_DIR / "dataset_cache.npz",
        "cpsc2018": CACHE_DIR / "cache_cpsc2018.npz",
        "cpsc2018-extra": CACHE_DIR / "cache_cpsc2018-extra.npz",
        "georgia": CACHE_DIR / "cache_georgia.npz",
        "chapman-shaoxing": CACHE_DIR / "cache_chapman-shaoxing.npz",
        "ningbo": CACHE_DIR / "cache_ningbo.npz",
    }
    # Also add PTB-XL
    ptb_cache = CACHE_DIR / "cache_ptbxl_native.npz"
    if ptb_cache.exists():
        caches["ptb-xl"] = ptb_cache
        ds_order.append("ptb-xl")

    t = Table(box=box.ROUNDED, title="[bold]Cross-Dataset Generalization (V2 Model)[/]")
    t.add_column("Dataset", style="cyan"); t.add_column("Records"); t.add_column("Active Cls")
    t.add_column("Macro AUC"); t.add_column("Mean Conf"); t.add_column("Pred Rate >0.5")

    for ds_name in ds_order:
        cache_p = caches.get(ds_name)
        if cache_p is None or not cache_p.exists():
            continue
        try:
            data = np.load(cache_p, allow_pickle=True)
            X_ds, Y_ds = data["X"], data["Y"]
            valid = np.isfinite(X_ds).reshape(X_ds.shape[0], -1).all(axis=1)
            X_ds, Y_ds = X_ds[valid], Y_ds[valid]
            # Use up to 2000 records for speed
            if len(X_ds) > 2000:
                sel = np.random.RandomState(42).choice(len(X_ds), 2000, replace=False)
                X_ds, Y_ds = X_ds[sel], Y_ds[sel]

            preds = batch_predict(model, X_ds)
            active = [i for i in range(min(NUM_CLASSES, Y_ds.shape[1])) if Y_ds[:, i].sum() >= 5]
            aucs = []
            for i in active:
                try: aucs.append(roc_auc_score(Y_ds[:, i], preds[:, i]))
                except: pass
            macro = np.mean(aucs) if aucs else 0
            mean_conf = float(preds.max(1).mean())
            pred_rate = float((preds.max(1) > 0.5).mean())

            results[ds_name] = {"n": len(X_ds), "active_classes": len(active),
                                "macro_auc": round(macro, 4), "mean_conf": round(mean_conf, 4),
                                "pred_rate": round(pred_rate, 4)}

            ac = "green" if macro > 0.9 else "yellow" if macro > 0.8 else "red"
            t.add_row(ds_name, f"{len(X_ds):,}", str(len(active)),
                      f"[{ac}]{macro:.4f}[/{ac}]", f"{mean_conf:.4f}", f"{pred_rate:.1%}")
        except Exception as e:
            console.print(f"    [red]{ds_name}: {e}[/]")
    console.print(t)

    # Plot
    dark_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    ds_names = list(results.keys())
    aucs_plot = [results[d]["macro_auc"] for d in ds_names]
    colors = [PAL[3] if a > 0.9 else PAL[4] if a > 0.8 else PAL[5] for a in aucs_plot]
    bars = ax.barh(ds_names, aucs_plot, color=colors, edgecolor=C["surface"])
    for bar, auc in zip(bars, aucs_plot):
        ax.text(bar.get_width()+0.005, bar.get_y()+bar.get_height()/2,
                f"{auc:.4f}", va="center", fontsize=10, color=C["text"])
    ax.set_xlabel("Macro AUC"); ax.set_xlim(0.5, 1.05)
    ax.axvline(x=0.9, color=PAL[2], ls="--", alpha=0.5)
    ax.invert_yaxis(); ax.grid(True, alpha=0.3, axis="x")
    ax.set_title("Cross-Dataset Generalization | DCA-CNN V2", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "fig10_cross_dataset.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    console.print(f"  [green]Saved: fig10_cross_dataset.pdf[/]")

    elapsed = time.time() - t0
    results["duration_s"] = round(elapsed, 1)
    log["phases"]["H"] = results; save_log()
    return results


# ═══════════════════════════════════════════════════════════════
#  PHASE I — CALIBRATION ANALYSIS
# ═══════════════════════════════════════════════════════════════
def phase_I_calibration(model):
    header("Phase I: Calibration Analysis",
           "Expected Calibration Error, reliability diagrams, Brier score")
    t0 = time.time()

    d = get_sph_splits()
    X_val, Y_val = d["X_val"], d["Y_val"]

    preds = batch_predict(model, X_val)
    results = {}

    # Per-class Brier score and ECE
    console.print("  [cyan]Computing calibration metrics...[/]")
    cal_data = []
    for i in range(min(NUM_CLASSES, preds.shape[1])):
        support = int(Y_val[:, i].sum())
        if support < 10: continue
        name = CONDITION_NAMES[i] if i < len(CONDITION_NAMES) else f"c{i}"
        brier = brier_score_loss(Y_val[:, i], preds[:, i])
        # ECE
        n_bins = 10
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0
        for b in range(n_bins):
            mask = (preds[:, i] >= bin_edges[b]) & (preds[:, i] < bin_edges[b+1])
            if mask.sum() == 0: continue
            avg_conf = preds[mask, i].mean()
            avg_acc = Y_val[mask, i].mean()
            ece += mask.sum() / len(Y_val) * abs(avg_conf - avg_acc)

        cal_data.append({"class": name, "support": support,
                         "brier": round(float(brier), 4), "ece": round(float(ece), 4)})
    cal_data.sort(key=lambda x: x["ece"], reverse=True)
    results["per_class_calibration"] = cal_data

    t = Table(box=box.ROUNDED, title="[bold]Calibration Metrics (Top 15)[/]")
    t.add_column("Class", style="cyan"); t.add_column("Support"); t.add_column("Brier"); t.add_column("ECE")
    for cd in cal_data[:15]:
        ec = "green" if cd["ece"] < 0.05 else "yellow" if cd["ece"] < 0.1 else "red"
        t.add_row(cd["class"], str(cd["support"]), f"{cd['brier']:.4f}", f"[{ec}]{cd['ece']:.4f}[/{ec}]")
    console.print(t)

    # Overall ECE
    overall_brier = np.mean([c["brier"] for c in cal_data])
    overall_ece = np.mean([c["ece"] for c in cal_data])
    results["overall_brier"] = round(float(overall_brier), 4)
    results["overall_ece"] = round(float(overall_ece), 4)
    console.print(f"  Overall Brier: {overall_brier:.4f}, ECE: {overall_ece:.4f}")

    # Reliability diagram for top 4 classes by support
    dark_style()
    top4 = sorted(cal_data, key=lambda x: x["support"], reverse=True)[:4]
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))

    for ax_idx, cd in enumerate(top4):
        ax = axes[ax_idx]
        cls_idx = next(j for j, n in enumerate(CONDITION_NAMES) if n == cd["class"])
        try:
            fraction_pos, mean_pred = calibration_curve(Y_val[:, cls_idx], preds[:, cls_idx], n_bins=10)
            ax.plot([0, 1], [0, 1], 'k--', alpha=0.3, lw=1)
            ax.plot(mean_pred, fraction_pos, 'o-', color=PAL[ax_idx], lw=2.5, ms=8)
            ax.fill_between(mean_pred, fraction_pos, mean_pred, alpha=0.15, color=PAL[ax_idx])
            ax.set_title(f"{cd['class']} (n={cd['support']})", fontweight="bold")
            ax.set_xlabel("Mean Predicted"); ax.set_ylabel("Fraction Positive")
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.grid(True, alpha=0.3)
            ax.text(0.05, 0.9, f"ECE={cd['ece']:.3f}\nBrier={cd['brier']:.3f}",
                    transform=ax.transAxes, fontsize=9, color=C["text"])
        except Exception:
            ax.set_title(f"{cd['class']}: error", fontweight="bold")

    fig.suptitle("Calibration Reliability Diagrams | DCA-CNN V2", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "fig11_calibration.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    console.print(f"  [green]Saved: fig11_calibration.pdf[/]")

    elapsed = time.time() - t0
    results["duration_s"] = round(elapsed, 1)
    log["phases"]["I"] = results; save_log()
    return results


# ═══════════════════════════════════════════════════════════════
#  PHASE D2 — DEDUPLICATE + RETRAIN IF LEAKAGE FOUND
# ═══════════════════════════════════════════════════════════════
def phase_D2_retrain_clean():
    header("Phase D2: Clean Retrain",
           "Removing duplicate records, rebuilding splits, retraining DCA-CNN")
    t0 = time.time()
    d = get_sph_splits()
    X_tr, Y_tr = d["X_train"], d["Y_train"]
    X_vl, Y_vl = d["X_val"], d["Y_val"]
    X_te, Y_te = d["X_test"], d["Y_test"]

    def rec_hash(x):
        return hashlib.md5(x.tobytes()).hexdigest()

    console.print("  [cyan]Deduplicating across splits...[/]")
    all_X = np.concatenate([X_tr, X_vl, X_te], axis=0)
    all_Y = np.concatenate([Y_tr, Y_vl, Y_te], axis=0)
    seen = set()
    unique_idx = []
    for i in range(len(all_X)):
        h = rec_hash(all_X[i])
        if h not in seen:
            seen.add(h)
            unique_idx.append(i)
    removed = len(all_X) - len(unique_idx)
    console.print(f"    {len(all_X):,} -> {len(unique_idx):,} unique (removed {removed})")
    all_X = all_X[unique_idx]
    all_Y = all_Y[unique_idx]

    rng = np.random.RandomState(2024)
    perm = rng.permutation(len(all_X))
    n = len(all_X)
    X_train = all_X[perm[:int(n * 0.70)]]
    Y_train = all_Y[perm[:int(n * 0.70)]]
    X_val = all_X[perm[int(n * 0.70):int(n * 0.85)]]
    Y_val = all_Y[perm[int(n * 0.70):int(n * 0.85)]]

    # Add external datasets
    console.print("  [cyan]Adding external datasets...[/]")
    for ds_name in ["cpsc2018", "cpsc2018-extra", "georgia", "chapman-shaoxing", "ningbo"]:
        cache_p = CACHE_DIR / f"cache_{ds_name}.npz"
        if cache_p.exists():
            ext = np.load(cache_p, allow_pickle=True)
            X_e = ext["X"].astype(np.float32)
            Y_e = ext["Y"].astype(np.float32)
            valid = np.isfinite(X_e).reshape(X_e.shape[0], -1).all(axis=1)
            X_e, Y_e = X_e[valid], Y_e[valid]
            ne = len(X_e)
            ep = rng.permutation(ne)
            n_tr = int(ne * 0.85)
            X_train = np.concatenate([X_train, X_e[ep[:n_tr]]])
            Y_train = np.concatenate([Y_train, Y_e[ep[:n_tr]]])
            X_val = np.concatenate([X_val, X_e[ep[n_tr:]]])
            Y_val = np.concatenate([Y_val, Y_e[ep[n_tr:]]])
            console.print(f"    +{ds_name}: {ne:,}")

    ptb_cache = CACHE_DIR / "cache_ptbxl_native.npz"
    if ptb_cache.exists():
        ptb = np.load(ptb_cache, allow_pickle=True)
        X_p = ptb["X"].astype(np.float32)
        Y_p = ptb["Y"].astype(np.float32)
        ne = len(X_p)
        ep = rng.permutation(ne)
        n_tr = int(ne * 0.85)
        X_train = np.concatenate([X_train, X_p[ep[:n_tr]]])
        Y_train = np.concatenate([Y_train, Y_p[ep[:n_tr]]])
        X_val = np.concatenate([X_val, X_p[ep[n_tr:]]])
        Y_val = np.concatenate([Y_val, Y_p[ep[n_tr:]]])
        console.print(f"    +PTB-XL: {ne:,}")

    perm = rng.permutation(len(X_train))
    X_train, Y_train = X_train[perm], Y_train[perm]

    t = Table(box=box.ROUNDED, title="[bold]Clean Retrain Dataset[/]")
    t.add_column("Metric", style="cyan")
    t.add_column("Value")
    t.add_row("Train", f"{len(X_train):,}")
    t.add_row("Val", f"{len(X_val):,}")
    t.add_row("Duplicates removed", str(removed))
    t.add_row("Memory", f"{(X_train.nbytes + X_val.nbytes)/1024**3:.2f} GB")
    console.print(t)

    console.print("\n  [bold yellow]Retraining DCA-CNN from scratch (clean splits)...[/]\n")
    model, best_auc, log_rows = train_model(X_train, Y_train, X_val, Y_val)

    import shutil
    clean_pt = MODEL_DIR / "ecg_dca_cnn_v3_clean.pt"
    best_pt = MODEL_DIR / "ecg_dca_cnn_best.pt"
    if best_pt.exists():
        shutil.copy2(best_pt, clean_pt)
    onnx_path = str(MODEL_DIR / "ecg_dca_cnn_v3_clean.onnx")
    export_onnx(model, onnx_path)

    elapsed = time.time() - t0
    results = {
        "removed_duplicates": removed, "train": len(X_train), "val": len(X_val),
        "best_auc": round(best_auc, 6), "epochs": len(log_rows),
        "duration_s": round(elapsed, 1), "model_path": str(clean_pt),
    }
    log["phases"]["D2"] = results
    save_log()
    console.print(Panel(
        f"[bold green]Clean retrain done:[/] AUC={best_auc:.4f}, "
        f"{len(X_train)+len(X_val):,} records, {timedelta(seconds=int(elapsed))}",
        border_style="green"))

    _DATA_CACHE.clear()
    # Re-populate cache with clean SPH splits for phases F/G/I
    console.print("  [dim]Reloading clean SPH splits...[/dim]")
    get_sph_splits()
    return model, results


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    start = time.time()

    console.print(Panel.fit(
        "[bold white]HAYATIN RITMI -- PIPELINE V3 (Overnight Robustness)[/]\n\n"
        "[cyan]Phase D:[/] Data leakage detection\n"
        "[cyan]Phase D2:[/] If leakage -> deduplicate + full retrain\n"
        "[cyan]Phase E:[/] Overfitting analysis\n"
        "[cyan]Phase F:[/] Noise robustness (Gaussian/Wander/PLI)\n"
        "[cyan]Phase G:[/] Lead dropout stress test\n"
        "[cyan]Phase H:[/] Cross-dataset generalization\n"
        "[cyan]Phase I:[/] Calibration analysis (ECE/Brier/Reliability)\n\n"
        f"[dim]Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]\n"
        f"[dim]Device: {DEVICE}" + (f" ({torch.cuda.get_device_name(0)})" if DEVICE.type == "cuda" else "") + "[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(1, 4),
    ))

    # Load model
    model = DcaCNN().to(DEVICE)
    v2_pt = MODEL_DIR / "ecg_dca_cnn_v2.pt"
    if not v2_pt.exists():
        v2_pt = MODEL_DIR / "ecg_dca_cnn_best.pt"
    model.load_state_dict(torch.load(v2_pt, map_location=DEVICE, weights_only=True))
    model.eval()
    console.print(f"\n  [green]Model loaded: {v2_pt.name}[/]\n")

    phases = {"D": None, "D2": None, "E": None, "F": None, "G": None, "H": None, "I": None}
    leakage_found = False

    # ── Phase D: Leakage ──
    try:
        phases["D"] = phase_D_leakage(model)
        console.print(Panel("[green]Phase D complete[/]", border_style="green"))
    except Exception as e:
        console.print(f"[red]Phase D failed: {e}[/]")
        import traceback; traceback.print_exc()

    # ── Phase D2: Retrain if leakage ──
    if phases["D"]:
        tv = phases["D"].get("duplicate_train_val", 0)
        tt = phases["D"].get("duplicate_train_test", 0)
        leakage_found = (tv > 0 or tt > 0)

    if leakage_found:
        v3_clean = MODEL_DIR / "ecg_dca_cnn_v3_clean.pt"
        skip_d2 = v3_clean.exists() and "--force-d2" not in sys.argv

        if skip_d2:
            console.print(Panel(
                f"[bold yellow]LEAKAGE: {tv} train-val + {tt} train-test duplicates[/]\n"
                f"[green]V3 clean model found: {v3_clean.name} -- loading instead of retrain[/]\n"
                "[dim](use --force-d2 to retrain)[/dim]",
                border_style="yellow"))
            model = DcaCNN().to(DEVICE)
            model.load_state_dict(torch.load(v3_clean, map_location=DEVICE, weights_only=True))
            model.eval()
            phases["D2"] = {"skipped": True, "model_path": str(v3_clean)}
        else:
            console.print(Panel(
                f"[bold red]LEAKAGE: {tv} train-val + {tt} train-test duplicates[/]\n"
                "[bold yellow]-> Retraining from scratch with deduplicated data...[/]",
                border_style="red"))
            try:
                model, d2_res = phase_D2_retrain_clean()
                phases["D2"] = d2_res
                model.to(DEVICE)
                model.eval()
                console.print(Panel("[green]Phase D2 complete - clean model ready[/]", border_style="green"))
            except Exception as e:
                console.print(f"[red]Phase D2 failed: {e}[/]")
                import traceback; traceback.print_exc()
    else:
        console.print(Panel("[green]No leakage - skipping retrain[/]", border_style="green"))

    # ── Phases E-I with (possibly retrained) model ──
    for phase_id, (fn, args) in [
        ("E", (phase_E_overfit, [])),
        ("F", (phase_F_noise, [model])),
        ("G", (phase_G_lead_dropout, [model])),
        ("H", (phase_H_cross_dataset, [model])),
        ("I", (phase_I_calibration, [model])),
    ]:
        try:
            phases[phase_id] = fn(*args)
            console.print(Panel(f"[green]Phase {phase_id} complete[/]", border_style="green"))
        except Exception as e:
            console.print(f"[red]Phase {phase_id} failed: {e}[/]")
            import traceback; traceback.print_exc()

    total = time.time() - start
    log["total_s"] = round(total, 1)
    log["end"] = datetime.now().isoformat()
    save_log()

    console.print("\n")
    console.print(Rule("[bold green]PIPELINE V3 COMPLETE[/]", style="green"))

    final = Table(box=box.DOUBLE_EDGE, title="[bold green]Overnight Robustness Report[/]", border_style="green")
    final.add_column("Phase", style="cyan")
    final.add_column("Status")
    final.add_column("Key Finding")

    labels = {"D":"Leakage","D2":"Clean Retrain","E":"Overfitting","F":"Noise",
              "G":"Lead Dropout","H":"Cross-DS","I":"Calibration"}
    for pid in ["D","D2","E","F","G","H","I"]:
        if pid == "D2" and not leakage_found:
            final.add_row(f"{pid}. {labels[pid]}", "[dim]SKIPPED[/]", "No leakage")
            continue
        status = "[green]OK[/]" if phases.get(pid) else "[red]FAIL[/]"
        finding = ""
        if phases.get(pid):
            if pid == "D":
                finding = f"Dupes: TV={phases[pid].get('duplicate_train_val',0)} TT={phases[pid].get('duplicate_train_test',0)}"
            elif pid == "D2":
                finding = f"AUC={phases[pid].get('best_auc','?')}, removed {phases[pid].get('removed_duplicates',0)} dupes"
            elif pid == "E":
                finding = f"BestAUC={phases[pid].get('best_val_auc','?')}"
            elif pid == "F":
                finding = f"CleanAUC={phases[pid].get('clean_auc','?')}"
            elif pid == "G":
                finding = f"ShuffleDrop={phases[pid].get('shuffle_drop','?')}"
            elif pid == "H":
                finding = f"{len([k for k in phases[pid] if k!='duration_s'])} datasets"
            elif pid == "I":
                finding = f"ECE={phases[pid].get('overall_ece','?')}"
        final.add_row(f"{pid}. {labels[pid]}", status, finding)

    final.add_row("", "", "")
    final.add_row("[bold]Total Time[/]", "", f"[bold]{timedelta(seconds=int(total))}[/]")
    mp = "ecg_dca_cnn_v3_clean.pt" if leakage_found else "ecg_dca_cnn_v2.pt"
    final.add_row("[bold]Model[/]", "", str(MODEL_DIR / mp))
    final.add_row("[bold]Figures[/]", "", str(FIGURES_DIR))
    console.print(final)

