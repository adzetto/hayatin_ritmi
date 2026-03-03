"""
DCA-CNN Lead Robustness Evaluation — Multi-Rate, Multi-Lead Unlabeled Datasets
===============================================================================
Tests the DCA-CNN model on real-world datasets with varied lead counts and
sampling rates (ltstdb, twadb, mghdb, mhd-effect-ecg-mri) that lack SNOMED
labels. Evaluates signal handling robustness without requiring ground truth.

Metrics (no labels needed):
  1. Signal loading success rate
  2. Prediction confidence distribution
  3. Cross-rate stability
  4. Real vs simulated lead reduction
  5. Predicted class distribution
  6. Per-dataset summary

Usage: python ai/evaluation/evaluate_lead_robustness.py

Outputs: ai/models/results/lead_robustness_results.json
"""

from __future__ import annotations

import os, sys, json, time, glob
from pathlib import Path
from collections import Counter

import numpy as np
from scipy.signal import butter, filtfilt, resample

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ai" / "training"))

DATASET_DIR  = PROJECT_ROOT / "dataset"
CACHE_DIR    = PROJECT_ROOT / "ai" / "cache"
RESULTS_DIR  = PROJECT_ROOT / "ai" / "models" / "results"
CKPT_DIR     = PROJECT_ROOT / "ai" / "models" / "checkpoints"
SNOMED_CSV   = PROJECT_ROOT / "dataset" / "ecg-arrhythmia" / "ConditionNames_SNOMED-CT.csv"

LEAD_NAMES_12 = ["I", "II", "III", "aVR", "aVL", "aVF",
                 "V1", "V2", "V3", "V4", "V5", "V6"]

# ============================================================================
#  DATASET DEFINITIONS
# ============================================================================
# Each dataset specifies:
#   path:        directory under dataset/
#   native_fs:   native sampling frequency
#   lead_map:    dict mapping WFDB sig_name patterns to 12-lead indices
#   min_leads:   minimum leads required (skip records with fewer)
#   skip_records: record names to skip (e.g. mixed-rate records)
#   c_active:    how many active channels to pass to DCA-CNN

DATASETS = {
    "mhd-effect-ecg-mri": {
        "path": DATASET_DIR / "mhd-effect-ecg-mri",
        "native_fs": 1024,
        "lead_map": {
            "I": 0, "II": 1, "III": 2, "aVR": 3, "aVL": 4, "aVF": 5,
            "V1": 6, "V2": 7, "V3": 8, "V4": 9, "V5": 10, "V6": 11,
        },
        "min_leads": 12,
        "skip_records": set(),
        "c_active": 12,
        "description": "MRI MHD Effect ECG (12-lead, 1024Hz)",
    },
    "twadb": {
        "path": DATASET_DIR / "twadb",
        "native_fs": 500,
        "lead_map": {
            "I": 0, "II": 1, "III": 2, "aVR": 3, "aVL": 4, "aVF": 5,
            "V1": 6, "V2": 7, "V3": 8, "V4": 9, "V5": 10, "V6": 11,
        },
        "min_leads": 12,
        "skip_records": {"twa00"},  # mixed 500/250 Hz dual-rate
        "c_active": 12,
        "description": "T-Wave Alternans DB (12-lead, 500Hz)",
    },
    "mghdb": {
        "path": DATASET_DIR / "mghdb",
        "native_fs": 360,
        "lead_map": {
            # MGH records have 3 ECG leads + hemodynamic signals
            # Lead names vary: I, II, III, V, V1-V6
            "I": 0, "II": 1, "III": 2, "V": 6, "V1": 6, "V2": 7,
            "V3": 8, "V4": 9, "V5": 10, "V6": 11,
            # Modified leads
            "ECG": 1, "ECG1": 0, "ECG2": 1, "ECG3": 2,
        },
        "min_leads": 2,
        "skip_records": set(),
        "c_active": 3,
        "description": "MGH/MF ICU DB (3 ECG leads, 360Hz)",
    },
    "ltstdb": {
        "path": DATASET_DIR / "ltstdb",
        "native_fs": 250,
        "lead_map": {
            # Modified limb leads commonly used in Holter
            "ML2": 1, "MLII": 1, "ML II": 1, "MV2": 7, "MLIII": 2,
            "ML3": 2, "ML III": 2, "MV1": 6, "MV5": 10,
            "ECG": 1, "ECG1": 0, "ECG2": 1,
            # Standard lead names if present
            "I": 0, "II": 1, "III": 2,
            "V1": 6, "V2": 7, "V3": 8, "V4": 9, "V5": 10, "V6": 11,
        },
        "min_leads": 2,
        "skip_records": set(),
        "c_active": 1,  # effectively 1-2 useful leads
        "description": "Long-Term ST DB (2-ch Holter, 250Hz)",
    },
}


# ============================================================================
#  SIGNAL PROCESSING
# ============================================================================
def bandpass(sig, fs=500, lo=0.5, hi=40.0, order=2):
    nyq = fs / 2.0
    if hi >= nyq:
        hi = nyq * 0.95
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, sig, axis=-1)


def preprocess_signal(sig_CxN, original_fs, lead_indices):
    """Preprocess arbitrary-lead signal into (12, 2500) tensor.

    sig_CxN:      (C, N) raw signal with C available channels
    original_fs:  native sampling frequency
    lead_indices: list of length C, each is target 12-lead index (0-11)

    Returns (12, 2500) float32 or None on failure.
    """
    n_ch, n_samples = sig_CxN.shape

    # Resample to 500 Hz if needed
    if original_fs != 500:
        target_samples = int(n_samples * 500 / original_fs)
        if target_samples < 100:
            return None
        sig_CxN = resample(sig_CxN, target_samples, axis=1)
        n_samples = target_samples

    # Pad or truncate to 5000 samples (10s at 500Hz)
    if n_samples < 5000:
        sig_CxN = np.pad(sig_CxN, ((0, 0), (0, 5000 - n_samples)), mode="constant")
    elif n_samples > 5000:
        # Take middle 10 seconds for longer recordings
        start = (n_samples - 5000) // 2
        sig_CxN = sig_CxN[:, start:start + 5000]

    # Bandpass filter per channel
    sig_CxN = bandpass(sig_CxN, fs=500)
    sig_CxN = np.nan_to_num(sig_CxN, nan=0.0, posinf=0.0, neginf=0.0)

    # Downsample 500 -> 250 Hz
    sig_CxN = sig_CxN[:, ::2]  # (C, 2500)

    # Map to 12-lead tensor (zero-padded)
    out = np.zeros((12, 2500), dtype=np.float32)
    for ch_idx, lead_idx in enumerate(lead_indices):
        if ch_idx < sig_CxN.shape[0] and 0 <= lead_idx < 12:
            out[lead_idx] = sig_CxN[ch_idx]

    # Z-normalize per lead (only active leads)
    for i in range(12):
        std = out[i].std()
        if std > 1e-6:
            out[i] = (out[i] - out[i].mean()) / std

    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    if not np.isfinite(out).all():
        return None
    return out


# ============================================================================
#  DATASET LOADING
# ============================================================================
def load_class_names():
    import csv
    names = []
    with open(SNOMED_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            names.append(row["Acronym Name"])
    return names


def map_record_leads(sig_names, lead_map):
    """Map WFDB signal names to 12-lead indices using the dataset's lead_map.

    Returns list of (channel_index, 12lead_index) for ECG channels only.
    """
    mappings = []
    used_targets = set()

    for ch_idx, name in enumerate(sig_names):
        name_clean = name.strip()
        target = lead_map.get(name_clean)
        if target is not None and target not in used_targets:
            mappings.append((ch_idx, target))
            used_targets.add(target)

    return mappings


def load_dataset(ds_name, ds_cfg):
    """Load a dataset, returning list of preprocessed (12, 2500) arrays and metadata."""
    import wfdb

    ds_path = ds_cfg["path"]
    if not ds_path.exists():
        console.print(f"  [yellow]{ds_name}: Directory not found, skipping.[/]")
        return [], {}

    hea_files = sorted(glob.glob(str(ds_path / "*.hea")))
    if not hea_files:
        hea_files = sorted(glob.glob(str(ds_path / "**" / "*.hea"), recursive=True))

    X_list = []
    meta = {
        "total_hea": len(hea_files),
        "loaded": 0,
        "skipped_few_leads": 0,
        "skipped_blacklist": 0,
        "skipped_error": 0,
        "native_fs": ds_cfg["native_fs"],
        "lead_counts": Counter(),
        "mapped_leads": Counter(),
    }

    for hea in hea_files:
        rec_name = Path(hea).stem
        if rec_name in ds_cfg["skip_records"]:
            meta["skipped_blacklist"] += 1
            continue

        try:
            rec_path = hea[:-4]
            record = wfdb.rdrecord(rec_path)
            sig = record.p_signal
            if sig is None:
                meta["skipped_error"] += 1
                continue

            sig_names = record.sig_name if record.sig_name else []
            fs = record.fs if record.fs else ds_cfg["native_fs"]

            # Map leads
            mappings = map_record_leads(sig_names, ds_cfg["lead_map"])
            n_ecg = len(mappings)
            meta["lead_counts"][n_ecg] += 1

            if n_ecg < ds_cfg["min_leads"]:
                meta["skipped_few_leads"] += 1
                continue

            # Extract ECG channels
            ch_indices = [m[0] for m in mappings]
            lead_indices = [m[1] for m in mappings]

            sig_ecg = sig[:, ch_indices].T  # (n_ecg, N)

            for li in lead_indices:
                meta["mapped_leads"][LEAD_NAMES_12[li]] += 1

            x = preprocess_signal(sig_ecg, fs, lead_indices)
            if x is None:
                meta["skipped_error"] += 1
                continue

            X_list.append(x)
            meta["loaded"] += 1

        except Exception:
            meta["skipped_error"] += 1

    return X_list, meta


# ============================================================================
#  MODEL INFERENCE
# ============================================================================
def run_inference(model, X_array, c_active=12, batch_size=64):
    """Run DCA-CNN inference, return sigmoid probabilities."""
    import torch

    X_t = torch.from_numpy(X_array).float()
    all_preds = []

    with torch.no_grad():
        for i in range(0, len(X_t), batch_size):
            batch = X_t[i:i + batch_size]
            logits = model(batch, c_active=c_active)
            probs = torch.sigmoid(logits).numpy()
            all_preds.append(np.nan_to_num(probs, nan=0.0, posinf=1.0, neginf=0.0))

    return np.concatenate(all_preds, axis=0) if all_preds else np.zeros((0, 55))


# ============================================================================
#  ANALYSIS FUNCTIONS
# ============================================================================
def analyze_confidence(preds, class_names, top_k=5):
    """Analyze prediction confidence distribution."""
    n_records = len(preds)
    if n_records == 0:
        return {}

    # Per-record: max sigmoid, mean sigmoid, top-k classes
    max_probs = preds.max(axis=1)
    mean_probs = preds.mean(axis=1)

    # Top-k most frequently predicted classes (threshold=0.5)
    binary = (preds > 0.5).astype(int)
    class_counts = binary.sum(axis=0)
    top_classes = np.argsort(class_counts)[::-1][:top_k]

    # Top-k by mean confidence (no threshold)
    mean_per_class = preds.mean(axis=0)
    top_confident = np.argsort(mean_per_class)[::-1][:top_k]

    return {
        "n_records": n_records,
        "max_sigmoid": {
            "mean": round(float(max_probs.mean()), 4),
            "std": round(float(max_probs.std()), 4),
            "min": round(float(max_probs.min()), 4),
            "max": round(float(max_probs.max()), 4),
            "p25": round(float(np.percentile(max_probs, 25)), 4),
            "p50": round(float(np.percentile(max_probs, 50)), 4),
            "p75": round(float(np.percentile(max_probs, 75)), 4),
        },
        "mean_sigmoid": {
            "mean": round(float(mean_probs.mean()), 4),
            "std": round(float(mean_probs.std()), 4),
        },
        "top_predicted_classes": [
            {"class": class_names[i] if i < len(class_names) else f"cls_{i}",
             "count": int(class_counts[i]),
             "pct": round(100 * class_counts[i] / n_records, 1)}
            for i in top_classes if class_counts[i] > 0
        ],
        "top_confident_classes": [
            {"class": class_names[i] if i < len(class_names) else f"cls_{i}",
             "mean_prob": round(float(mean_per_class[i]), 4)}
            for i in top_confident
        ],
        "records_with_any_prediction": int((binary.sum(axis=1) > 0).sum()),
        "avg_predictions_per_record": round(float(binary.sum(axis=1).mean()), 2),
    }


def analyze_lead_reduction(model, X_12lead, class_names):
    """For 12-lead data: compare real 3-lead subset vs full 12-lead inference."""
    if len(X_12lead) == 0:
        return {}

    # Full 12-lead
    preds_12 = run_inference(model, X_12lead, c_active=12)
    # 3-lead (I, II, III — mask others)
    X_3lead = X_12lead.copy()
    X_3lead[:, 3:, :] = 0.0  # zero aVR-V6
    preds_3 = run_inference(model, X_3lead, c_active=3)
    # 1-lead (II only)
    X_1lead = X_12lead.copy()
    for ch in range(12):
        if ch != 1:
            X_1lead[:, ch, :] = 0.0
    preds_1 = run_inference(model, X_1lead, c_active=1)

    # Agreement: how often do top-1 predictions match?
    top1_12 = preds_12.argmax(axis=1)
    top1_3 = preds_3.argmax(axis=1)
    top1_1 = preds_1.argmax(axis=1)

    agree_12_3 = (top1_12 == top1_3).mean()
    agree_12_1 = (top1_12 == top1_1).mean()
    agree_3_1 = (top1_3 == top1_1).mean()

    # Cosine similarity of probability vectors
    def cos_sim(a, b):
        dot = (a * b).sum(axis=1)
        norm_a = np.linalg.norm(a, axis=1)
        norm_b = np.linalg.norm(b, axis=1)
        denom = norm_a * norm_b
        denom = np.where(denom < 1e-8, 1.0, denom)
        return dot / denom

    cos_12_3 = cos_sim(preds_12, preds_3).mean()
    cos_12_1 = cos_sim(preds_12, preds_1).mean()

    # Confidence preservation
    conf_12 = preds_12.max(axis=1).mean()
    conf_3 = preds_3.max(axis=1).mean()
    conf_1 = preds_1.max(axis=1).mean()

    return {
        "top1_agreement_12v3": round(float(agree_12_3), 4),
        "top1_agreement_12v1": round(float(agree_12_1), 4),
        "top1_agreement_3v1": round(float(agree_3_1), 4),
        "cosine_sim_12v3": round(float(cos_12_3), 4),
        "cosine_sim_12v1": round(float(cos_12_1), 4),
        "mean_confidence_12lead": round(float(conf_12), 4),
        "mean_confidence_3lead": round(float(conf_3), 4),
        "mean_confidence_1lead": round(float(conf_1), 4),
    }


def compute_signal_quality(X_array):
    """Compute basic signal quality metrics."""
    if len(X_array) == 0:
        return {}

    # Per-record SNR estimate (signal power / noise power in high-freq band)
    snr_estimates = []
    flatline_counts = []

    for x in X_array:
        active_leads = [i for i in range(12) if np.abs(x[i]).max() > 1e-6]
        n_active = len(active_leads)
        flatline_counts.append(12 - n_active)

        if n_active > 0:
            # Simple SNR: ratio of signal variance to high-freq noise variance
            for li in active_leads:
                sig = x[li]
                # Estimate noise as diff of consecutive samples
                noise = np.diff(sig)
                sig_power = np.var(sig)
                noise_power = np.var(noise) / 2  # Correct for differencing
                if noise_power > 1e-10:
                    snr_db = 10 * np.log10(sig_power / noise_power)
                    snr_estimates.append(snr_db)

    return {
        "n_records": len(X_array),
        "avg_flatline_leads": round(float(np.mean(flatline_counts)), 1),
        "snr_db_mean": round(float(np.mean(snr_estimates)), 1) if snr_estimates else None,
        "snr_db_std": round(float(np.std(snr_estimates)), 1) if snr_estimates else None,
        "snr_db_min": round(float(np.min(snr_estimates)), 1) if snr_estimates else None,
        "snr_db_p25": round(float(np.percentile(snr_estimates, 25)), 1) if snr_estimates else None,
        "snr_db_p50": round(float(np.percentile(snr_estimates, 50)), 1) if snr_estimates else None,
    }


# ============================================================================
#  RICH DISPLAY
# ============================================================================
def display_loading_summary(ds_name, ds_cfg, meta):
    """Display dataset loading results."""
    info_tbl = Table(box=box.ROUNDED, border_style="cyan", expand=False,
                     title=f"{ds_name}")
    info_tbl.add_column("Metric", style="cyan")
    info_tbl.add_column("Value", justify="right", style="bold")

    info_tbl.add_row("Description", ds_cfg["description"])
    info_tbl.add_row("Native Fs", f"{meta['native_fs']} Hz")
    info_tbl.add_row("Total .hea files", str(meta["total_hea"]))
    info_tbl.add_row("Loaded", f"[green]{meta['loaded']}[/]")
    info_tbl.add_row("Skipped (few leads)", str(meta["skipped_few_leads"]))
    info_tbl.add_row("Skipped (blacklist)", str(meta["skipped_blacklist"]))
    info_tbl.add_row("Skipped (error)", str(meta["skipped_error"]))
    info_tbl.add_row("c_active", str(ds_cfg["c_active"]))

    # Lead distribution
    if meta["mapped_leads"]:
        lead_str = ", ".join(f"{k}:{v}" for k, v in
                             sorted(meta["mapped_leads"].items(),
                                    key=lambda x: -x[1]))
        info_tbl.add_row("Mapped leads", lead_str)

    console.print(info_tbl)


def display_confidence(ds_name, conf):
    """Display confidence analysis."""
    if not conf:
        return

    tbl = Table(title=f"Prediction Confidence — {ds_name}",
                box=box.ROUNDED, border_style="green", expand=False)
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value", justify="right", style="bold")

    ms = conf["max_sigmoid"]
    tbl.add_row("Records", str(conf["n_records"]))
    tbl.add_row("Max sigmoid (mean)", f"{ms['mean']:.4f}")
    tbl.add_row("Max sigmoid (std)", f"{ms['std']:.4f}")
    tbl.add_row("Max sigmoid [p25/p50/p75]",
                f"{ms['p25']:.3f} / {ms['p50']:.3f} / {ms['p75']:.3f}")
    tbl.add_row("Avg predictions/record", str(conf["avg_predictions_per_record"]))
    tbl.add_row("Records with any pred",
                f"{conf['records_with_any_prediction']}/{conf['n_records']}")
    console.print(tbl)

    # Top predicted classes
    if conf["top_predicted_classes"]:
        cls_tbl = Table(title="Top Predicted Classes (>0.5)",
                        box=box.SIMPLE, expand=False, border_style="dim")
        cls_tbl.add_column("Class", style="yellow")
        cls_tbl.add_column("Count", justify="right")
        cls_tbl.add_column("%", justify="right")
        for c in conf["top_predicted_classes"]:
            cls_tbl.add_row(c["class"], str(c["count"]), f"{c['pct']:.1f}%")
        console.print(cls_tbl)

    # Top confident classes
    if conf["top_confident_classes"]:
        conf_tbl = Table(title="Top Confident Classes (by mean prob)",
                         box=box.SIMPLE, expand=False, border_style="dim")
        conf_tbl.add_column("Class", style="green")
        conf_tbl.add_column("Mean Prob", justify="right", style="bold")
        for c in conf["top_confident_classes"]:
            conf_tbl.add_row(c["class"], f"{c['mean_prob']:.4f}")
        console.print(conf_tbl)


def display_lead_reduction(ds_name, lr_results):
    """Display lead reduction comparison."""
    if not lr_results:
        return

    tbl = Table(title=f"Real vs Simulated Lead Reduction — {ds_name}",
                box=box.ROUNDED, border_style="magenta", expand=False)
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value", justify="right", style="bold")

    tbl.add_row("Top-1 agreement (12 vs 3)", f"{lr_results['top1_agreement_12v3']:.1%}")
    tbl.add_row("Top-1 agreement (12 vs 1)", f"{lr_results['top1_agreement_12v1']:.1%}")
    tbl.add_row("Top-1 agreement (3 vs 1)", f"{lr_results['top1_agreement_3v1']:.1%}")
    tbl.add_row("Cosine similarity (12 vs 3)", f"{lr_results['cosine_sim_12v3']:.4f}")
    tbl.add_row("Cosine similarity (12 vs 1)", f"{lr_results['cosine_sim_12v1']:.4f}")
    tbl.add_row("Mean confidence 12-lead", f"{lr_results['mean_confidence_12lead']:.4f}")
    tbl.add_row("Mean confidence 3-lead", f"{lr_results['mean_confidence_3lead']:.4f}")
    tbl.add_row("Mean confidence 1-lead", f"{lr_results['mean_confidence_1lead']:.4f}")

    console.print(tbl)


def display_signal_quality(ds_name, sq):
    """Display signal quality metrics."""
    if not sq:
        return

    tbl = Table(title=f"Signal Quality — {ds_name}",
                box=box.SIMPLE, border_style="dim", expand=False)
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value", justify="right")

    tbl.add_row("Avg flatline leads", str(sq["avg_flatline_leads"]))
    if sq["snr_db_mean"] is not None:
        tbl.add_row("SNR (dB) mean", f"{sq['snr_db_mean']:.1f}")
        tbl.add_row("SNR (dB) std", f"{sq['snr_db_std']:.1f}")
        tbl.add_row("SNR (dB) p25/p50",
                     f"{sq['snr_db_p25']:.1f} / {sq['snr_db_p50']:.1f}")
    console.print(tbl)


# ============================================================================
#  MAIN
# ============================================================================
def main():
    import torch
    from train_dca_cnn import DcaCNN

    console.print(Panel(
        "[bold white]DCA-CNN LEAD ROBUSTNESS EVALUATION[/]\n"
        "[cyan]Multi-Rate  |  Multi-Lead  |  Unlabeled Datasets[/]\n"
        "[dim]ltstdb  |  twadb  |  mghdb  |  mhd-effect-ecg-mri[/]",
        border_style="bright_cyan", box=box.DOUBLE_EDGE, padding=(1, 4),
    ))

    # Load model
    ckpt = CKPT_DIR / "ecg_dca_cnn_best.pt"
    if not ckpt.exists():
        console.print(f"[bold red]Checkpoint not found:[/] {ckpt}")
        sys.exit(1)

    model = DcaCNN()
    model.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=True))
    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    console.print(f"  Model loaded: [green]{n_params:,}[/] params\n")

    class_names = load_class_names()
    all_results = {}

    # Summary table built incrementally
    summary_tbl = Table(title="Dataset Summary",
                        box=box.DOUBLE_EDGE, border_style="bright_green")
    summary_tbl.add_column("Dataset", style="cyan")
    summary_tbl.add_column("Records", justify="right")
    summary_tbl.add_column("Leads", justify="right")
    summary_tbl.add_column("c_active", justify="right")
    summary_tbl.add_column("Fs", justify="right")
    summary_tbl.add_column("Max Conf", justify="right", style="bold")
    summary_tbl.add_column("Avg Pred/Rec", justify="right")
    summary_tbl.add_column("SNR (dB)", justify="right")

    for ds_name, ds_cfg in DATASETS.items():
        console.print(Panel(f"[bold]{ds_name}[/]  —  {ds_cfg['description']}",
                            border_style="bright_blue", expand=False))

        # Load dataset
        X_list, meta = load_dataset(ds_name, ds_cfg)
        display_loading_summary(ds_name, ds_cfg, meta)

        if not X_list:
            console.print(f"  [yellow]No records loaded, skipping analysis.[/]\n")
            all_results[ds_name] = {"meta": meta, "loaded": 0}
            continue

        X_array = np.array(X_list, dtype=np.float32)

        # Signal quality
        sq = compute_signal_quality(X_array)
        display_signal_quality(ds_name, sq)

        # Inference
        console.print(f"  Running inference (c_active={ds_cfg['c_active']})...")
        t0 = time.perf_counter()
        preds = run_inference(model, X_array, c_active=ds_cfg["c_active"])
        elapsed = time.perf_counter() - t0
        console.print(f"  [green]{len(X_array)}[/] records in "
                      f"[cyan]{elapsed:.2f}s[/] "
                      f"({len(X_array)/elapsed:.0f} ECG/s)")

        # Confidence analysis
        conf = analyze_confidence(preds, class_names)
        display_confidence(ds_name, conf)

        # Lead reduction (only for 12-lead datasets)
        lr_results = {}
        if ds_cfg["c_active"] == 12 and len(X_array) > 0:
            lr_results = analyze_lead_reduction(model, X_array, class_names)
            display_lead_reduction(ds_name, lr_results)

        # Build summary row
        snr_str = f"{sq['snr_db_mean']:.1f}" if sq.get("snr_db_mean") else "-"
        max_conf_str = f"{conf['max_sigmoid']['mean']:.4f}" if conf else "-"
        avg_pred_str = str(conf.get("avg_predictions_per_record", "-")) if conf else "-"

        summary_tbl.add_row(
            ds_name, str(meta["loaded"]),
            str(ds_cfg["min_leads"]) + ("+") if ds_cfg["min_leads"] < 12 else "12",
            str(ds_cfg["c_active"]),
            f"{meta['native_fs']} Hz",
            max_conf_str, avg_pred_str, snr_str,
        )

        # Store results
        all_results[ds_name] = {
            "meta": {k: v if not isinstance(v, Counter) else dict(v)
                     for k, v in meta.items()},
            "signal_quality": sq,
            "confidence": conf,
            "lead_reduction": lr_results,
            "inference_time_s": round(elapsed, 3),
        }

        console.print()

    # Final summary
    console.print(summary_tbl)

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "lead_robustness_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

    console.print(Panel(
        f"[bold green]Results saved:[/] [dim]{out_path}[/]",
        border_style="green", expand=False,
    ))


if __name__ == "__main__":
    main()
