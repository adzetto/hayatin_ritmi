"""
DCA-CNN TFLite Benchmark + Noise Robustness Test
  - TFLite INT8/FP16/FP32 speed comparison
  - Per-class confusion matrix
  - SNR 6-18 dB noise robustness analysis

Usage: python ai/evaluation/benchmark_and_robustness.py
"""
import os, sys, time, json
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ai" / "training"))

TFLITE_DIR = PROJECT_ROOT / "ai" / "models" / "tflite"
CACHE_DIR  = PROJECT_ROOT / "ai" / "cache"
RESULTS_DIR = PROJECT_ROOT / "ai" / "models" / "results"
SNOMED_CSV = PROJECT_ROOT / "dataset" / "ecg-arrhythmia" / "ConditionNames_SNOMED-CT.csv"

def load_class_names():
    import csv
    names = []
    with open(SNOMED_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            names.append(row["Acronym Name"])
    return names

def load_test_data(n_samples=1000):
    cache = CACHE_DIR / "dataset_cache.npz"
    if not cache.exists():
        print(f"  Cache not found: {cache}")
        return None, None

    data = np.load(cache, allow_pickle=True)
    X, Y = data["X"], data["Y"]
    nan_mask = ~np.isfinite(X).reshape(X.shape[0], -1).all(axis=1)
    X, Y = X[~nan_mask], Y[~nan_mask]

    rng = np.random.RandomState(42)
    n = min(n_samples, len(X))
    idx = rng.choice(len(X), n, replace=False)
    return X[idx], Y[idx]


def benchmark_tflite():
    """Speed benchmark for all TFLite variants."""
    import tensorflow as tf
    print("\n" + "=" * 60)
    print("  TFLITE SPEED BENCHMARK")
    print("=" * 60)

    models = {
        "DCA-CNN INT8":  TFLITE_DIR / "ecg_dca_cnn_int8.tflite",
        "DCA-CNN FP32":  TFLITE_DIR / "ecg_dca_cnn_fp32.tflite",
        "DS-1D-CNN INT8": TFLITE_DIR / "ecg_model_int8.tflite",
        "Combined INT8":  TFLITE_DIR / "ecg_combined_int8.tflite",
    }

    X, _ = load_test_data(200)
    if X is None:
        print("  No test data available")
        return {}

    X_cl = np.transpose(X[:100], (0, 2, 1)).astype(np.float32)  # channels-last
    results = {}

    for name, path in models.items():
        if not path.exists():
            continue

        interp = tf.lite.Interpreter(model_path=str(path))
        interp.allocate_tensors()
        inp_det = interp.get_input_details()[0]
        out_det = interp.get_output_details()[0]
        inp_dtype = inp_det["dtype"]

        q_params = inp_det.get("quantization_parameters", {})
        scales = q_params.get("scales", np.array([]))
        zps = q_params.get("zero_points", np.array([]))
        scale = float(scales[0]) if len(scales) > 0 else 1.0
        zp = int(zps[0]) if len(zps) > 0 else 0

        def prep(s):
            if inp_dtype == np.int8:
                return np.clip(s / scale + zp, -128, 127).astype(np.int8)
            return s.astype(inp_dtype)

        for i in range(10):
            interp.set_tensor(inp_det["index"], prep(X_cl[i:i+1]))
            interp.invoke()

        times = []
        for i in range(100):
            s = prep(X_cl[i % len(X_cl):i % len(X_cl)+1])
            t0 = time.perf_counter()
            interp.set_tensor(inp_det["index"], s)
            interp.invoke()
            times.append((time.perf_counter() - t0) * 1000)

        avg = np.mean(times)
        size_kb = path.stat().st_size / 1024
        print(f"  {name:20s} | {size_kb:7.0f} KB | avg={avg:.2f}ms | {1000/avg:.0f} ECG/s")
        results[name] = {"avg_ms": round(avg, 3), "size_kb": round(size_kb, 1)}

    return results


def confusion_matrix_analysis():
    """Per-class confusion matrix and weak class identification."""
    print("\n" + "=" * 60)
    print("  PER-CLASS CONFUSION MATRIX ANALYSIS")
    print("=" * 60)

    import torch
    from train_dca_cnn import DcaCNN
    from sklearn.metrics import roc_auc_score, classification_report

    CKPT = PROJECT_ROOT / "ai" / "models" / "checkpoints" / "ecg_dca_cnn_best.pt"
    if not CKPT.exists():
        print("  DCA-CNN checkpoint not found")
        return {}

    X, Y = load_test_data(3960)
    if X is None:
        return {}

    model = DcaCNN()
    model.load_state_dict(torch.load(CKPT, map_location="cpu", weights_only=True))
    model.eval()

    class_names = load_class_names()
    X_t = torch.from_numpy(X).float()

    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X_t), 64):
            batch = X_t[i:i+64]
            logits = model(batch)
            probs = torch.sigmoid(logits)
            all_preds.append(probs.numpy())

    preds = np.concatenate(all_preds, axis=0)
    preds = np.nan_to_num(preds, 0.0)

    valid_cols = []
    for c in range(Y.shape[1]):
        if Y[:, c].sum() > 0 and Y[:, c].sum() < len(Y):
            valid_cols.append(c)

    print(f"\n  Active classes: {len(valid_cols)} / {Y.shape[1]}")

    per_class = []
    for c in valid_cols:
        auc = roc_auc_score(Y[:, c], preds[:, c])
        support = int(Y[:, c].sum())
        tp = int(((preds[:, c] > 0.5) & (Y[:, c] == 1)).sum())
        fp = int(((preds[:, c] > 0.5) & (Y[:, c] == 0)).sum())
        fn = int(((preds[:, c] <= 0.5) & (Y[:, c] == 1)).sum())
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        name = class_names[c] if c < len(class_names) else f"class_{c}"
        per_class.append({
            "idx": c, "name": name, "auc": round(auc, 4),
            "precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4), "support": support,
            "tp": tp, "fp": fp, "fn": fn
        })

    per_class.sort(key=lambda x: x["auc"])

    print(f"\n  {'Class':>8s}  {'AUC':>6s}  {'Prec':>6s}  {'Rec':>6s}  {'F1':>6s}  {'Sup':>5s}")
    print("  " + "-" * 50)
    for row in per_class[:10]:
        print(f"  {row['name']:>8s}  {row['auc']:.4f}  {row['precision']:.4f}  "
              f"{row['recall']:.4f}  {row['f1']:.4f}  {row['support']:5d}")
    print("  ...")
    for row in per_class[-5:]:
        print(f"  {row['name']:>8s}  {row['auc']:.4f}  {row['precision']:.4f}  "
              f"{row['recall']:.4f}  {row['f1']:.4f}  {row['support']:5d}")

    weak = [r for r in per_class if r["auc"] < 0.90]
    print(f"\n  Weak classes (AUC < 0.90): {len(weak)}")

    return {"per_class": per_class, "n_weak": len(weak), "n_active": len(valid_cols)}


def noise_robustness_test():
    """Test model performance at different SNR levels (6-18 dB)."""
    print("\n" + "=" * 60)
    print("  NOISE ROBUSTNESS TEST (SNR 6-18 dB)")
    print("=" * 60)

    import torch
    from train_dca_cnn import DcaCNN
    from sklearn.metrics import roc_auc_score

    CKPT = PROJECT_ROOT / "ai" / "models" / "checkpoints" / "ecg_dca_cnn_best.pt"
    if not CKPT.exists():
        print("  DCA-CNN checkpoint not found")
        return {}

    X, Y = load_test_data(2000)
    if X is None:
        return {}

    model = DcaCNN()
    model.load_state_dict(torch.load(CKPT, map_location="cpu", weights_only=True))
    model.eval()

    snr_levels = [6, 9, 12, 15, 18, 25, 40, None]  # None = clean
    results = {}
    rng = np.random.RandomState(123)

    for snr_db in snr_levels:
        X_noisy = X.copy()
        label = f"SNR={snr_db}dB" if snr_db is not None else "Clean"

        if snr_db is not None:
            for i in range(len(X_noisy)):
                sig_power = np.mean(X_noisy[i] ** 2)
                noise_power = sig_power / (10 ** (snr_db / 10))
                noise = rng.randn(*X_noisy[i].shape) * np.sqrt(noise_power)
                X_noisy[i] = X_noisy[i] + noise.astype(np.float32)

        X_t = torch.from_numpy(X_noisy).float()
        all_preds = []
        with torch.no_grad():
            for j in range(0, len(X_t), 64):
                batch = X_t[j:j+64]
                logits = model(batch)
                probs = torch.sigmoid(logits).numpy()
                all_preds.append(np.nan_to_num(probs, 0.0))
        preds = np.concatenate(all_preds)

        valid_cols = [c for c in range(Y.shape[1])
                      if 0 < Y[:, c].sum() < len(Y)]
        if len(valid_cols) < 2:
            continue

        macro_auc = roc_auc_score(
            Y[:, valid_cols], preds[:, valid_cols], average="macro"
        )
        results[label] = round(macro_auc, 4)
        print(f"  {label:>12s}  Macro AUC = {macro_auc:.4f}")

    return results


if __name__ == "__main__":
    all_results = {}

    speed = benchmark_tflite()
    all_results["speed_benchmark"] = speed

    confusion = confusion_matrix_analysis()
    all_results["confusion_matrix"] = confusion

    noise = noise_robustness_test()
    all_results["noise_robustness"] = noise

    out_path = RESULTS_DIR / "benchmark_robustness_results.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {out_path}")
