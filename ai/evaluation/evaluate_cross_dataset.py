"""
Cross-Dataset Evaluation & Combined Retraining
================================================
1. Load our trained DS-1D-CNN model
2. Evaluate on each external 12-lead ECG dataset
3. Report per-class AUC across datasets  
4. Identify weak classes (AUC < 0.90)
5. If weak classes found → combine external data → retrain
"""

import os, sys, csv, json, time, glob, hashlib
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split, ConcatDataset
from scipy.signal import butter, filtfilt, resample
from sklearn.metrics import roc_auc_score
from tqdm import tqdm
import wfdb
from collections import Counter, defaultdict

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR       = os.path.join(PROJECT_ROOT, "ai")
DATASET_DIR  = os.path.join(PROJECT_ROOT, "dataset")
SPH_PATH     = os.path.join(DATASET_DIR, "ecg-arrhythmia")
MODEL_DIR    = os.path.join(AI_DIR, "models", "checkpoints")
RESULTS_DIR  = os.path.join(AI_DIR, "models", "results")
TFLITE_DIR   = os.path.join(AI_DIR, "models", "tflite")
CACHE_DIR    = os.path.join(AI_DIR, "cache")
SNOMED_CSV   = os.path.join(SPH_PATH, "ConditionNames_SNOMED-CT.csv")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── MODEL CONFIG ─────────────────────────────────────────────────────────────
FS_ORIGINAL = 500
FS_TARGET   = 250
N_SAMPLES   = 2500   # 10s at 250Hz
N_LEADS     = 12
BATCH_SIZE  = 128

# ─── SNOMED MAP ───────────────────────────────────────────────────────────────
def load_snomed_map():
    codes, names = [], []
    with open(SNOMED_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            codes.append(int(row["Snomed_CT"]))
            names.append(row["Acronym Name"])
    return {code: i for i, code in enumerate(codes)}, names

SNOMED_MAP, CONDITION_NAMES = load_snomed_map()
NUM_CLASSES = len(SNOMED_MAP)

# Reverse map: index → SNOMED code
IDX_TO_CODE = {i: code for code, i in SNOMED_MAP.items()}

# ─── EXTERNAL DATASETS ───────────────────────────────────────────────────────
EXTERNAL_DATASETS = {
    "cpsc2018":        os.path.join(DATASET_DIR, "cpsc2018"),
    "cpsc2018-extra":  os.path.join(DATASET_DIR, "cpsc2018-extra"),
    "georgia":         os.path.join(DATASET_DIR, "georgia"),
    "chapman-shaoxing":os.path.join(DATASET_DIR, "chapman-shaoxing"),
    "ningbo":          os.path.join(DATASET_DIR, "ningbo"),
}

# ─── PREPROCESSING ────────────────────────────────────────────────────────────
def bandpass(sig, fs=500, lo=0.5, hi=40.0, order=2):
    nyq = fs / 2.0
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, sig, axis=-1)


def preprocess(sig_12xN, original_fs=500):
    """(12, N) → (12, 2500) normalized float32."""
    n_leads, n_samples = sig_12xN.shape
    
    # Resample to 500Hz if needed
    if original_fs != 500:
        target_samples = int(n_samples * 500 / original_fs)
        sig_12xN = resample(sig_12xN, target_samples, axis=1)
        n_samples = target_samples
    
    # Pad or truncate to exactly 5000 samples (10s at 500Hz)
    if n_samples < 5000:
        pad_width = 5000 - n_samples
        sig_12xN = np.pad(sig_12xN, ((0, 0), (0, pad_width)), mode="constant")
    elif n_samples > 5000:
        sig_12xN = sig_12xN[:, :5000]
    
    # Bandpass filter
    sig = bandpass(sig_12xN, fs=500)
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Downsample 500→250
    sig = sig[:, ::2]  # (12, 2500)
    
    # Z-normalize per lead
    std = sig.std(axis=1, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    sig = (sig - sig.mean(axis=1, keepdims=True)) / std
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    
    out = sig.astype(np.float32)
    if not np.isfinite(out).all():
        return None
    return out


def parse_dx(hea_path):
    """Extract SNOMED codes from .hea file (handles '# Dx:' and '#Dx:')."""
    codes = []
    try:
        with open(hea_path, encoding="utf-8") as f:
            for line in f:
                ls = line.strip()
                if ls.startswith("#") and "Dx" in ls:
                    idx = ls.find("Dx:")
                    if idx >= 0:
                        for c in ls[idx + 3:].strip().split(","):
                            c = c.strip()
                            if c.isdigit():
                                codes.append(int(c))
    except Exception:
        pass
    return codes


# ─── MODEL ────────────────────────────────────────────────────────────────────
class DSConv1d(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size=7, stride=1):
        super().__init__()
        self.dw = nn.Conv1d(in_ch, in_ch, kernel_size, stride=stride,
                            padding=kernel_size // 2, groups=in_ch, bias=False)
        self.bn1 = nn.BatchNorm1d(in_ch)
        self.pw  = nn.Conv1d(in_ch, out_ch, 1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.act = nn.ReLU6()

    def forward(self, x):
        x = self.act(self.bn1(self.dw(x)))
        x = self.act(self.bn2(self.pw(x)))
        return x


class EcgDSCNN(nn.Module):
    def __init__(self, n_leads=N_LEADS, n_classes=NUM_CLASSES):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(n_leads, 32, 15, stride=2, padding=7, bias=False),
            nn.BatchNorm1d(32),
            nn.ReLU6(),
        )
        self.blocks = nn.Sequential(
            DSConv1d(32,  64,  kernel_size=7, stride=2),
            DSConv1d(64,  128, kernel_size=7, stride=2),
            DSConv1d(128, 128, kernel_size=5, stride=2),
            DSConv1d(128, 256, kernel_size=5, stride=2),
            DSConv1d(256, 256, kernel_size=3, stride=2),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU6(),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        return self.head(x)


# ─── DATA LOADING ─────────────────────────────────────────────────────────────
def load_dataset_records(dataset_path, max_records=None):
    """Load ECG records from a WFDB dataset with #Dx: SNOMED labels."""
    hea_files = glob.glob(os.path.join(dataset_path, "**", "*.hea"), recursive=True)
    
    X_list, Y_list = [], []
    skipped = 0
    
    desc = os.path.basename(dataset_path)
    for hea in tqdm(hea_files[:max_records] if max_records else hea_files,
                    desc=f"  Loading {desc}", unit="rec"):
        try:
            rec_path = hea[:-4]  # remove .hea
            record = wfdb.rdrecord(rec_path)
            
            sig = record.p_signal  # (N_samples, N_leads)
            if sig is None or sig.shape[1] < 12:
                skipped += 1
                continue
            
            # Take first 12 leads if more
            sig = sig[:, :12].T  # → (12, N)
            
            # Get sampling frequency
            fs = record.fs
            
            # Preprocess
            x = preprocess(sig, original_fs=fs)
            if x is None:
                skipped += 1
                continue
            
            # Parse labels
            codes = parse_dx(hea)
            if not codes:
                skipped += 1
                continue
            
            label = np.zeros(NUM_CLASSES, dtype=np.float32)
            has_known = False
            for code in codes:
                if code in SNOMED_MAP:
                    label[SNOMED_MAP[code]] = 1.0
                    has_known = True
            
            if not has_known:
                skipped += 1
                continue
            
            X_list.append(x)
            Y_list.append(label)
            
        except Exception as e:
            skipped += 1
    
    if X_list:
        X = np.array(X_list, dtype=np.float32)
        Y = np.array(Y_list, dtype=np.float32)
    else:
        X = np.zeros((0, 12, 2500), dtype=np.float32)
        Y = np.zeros((0, NUM_CLASSES), dtype=np.float32)
    
    print(f"    → Loaded {len(X_list):,} records, skipped {skipped:,}")
    return X, Y


class NpDataset(Dataset):
    def __init__(self, X, Y):
        self.X = torch.from_numpy(X)
        self.Y = torch.from_numpy(Y)
    def __len__(self):
        return len(self.X)
    def __getitem__(self, idx):
        return self.X[idx], self.Y[idx]


# ─── EVALUATION ───────────────────────────────────────────────────────────────
def evaluate_on_dataset(model, X, Y, dataset_name):
    """Run inference, compute per-class AUC."""
    if len(X) == 0:
        print(f"  {dataset_name}: No compatible records.")
        return {}
    
    model.eval()
    ds = NpDataset(X, Y)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    all_preds, all_labels = [], []
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(DEVICE)
            pred = torch.sigmoid(model(xb)).cpu().numpy()
            all_preds.append(pred)
            all_labels.append(yb.numpy())
    
    preds = np.vstack(all_preds)
    labels = np.vstack(all_labels)
    preds = np.nan_to_num(preds, nan=0.5, posinf=1.0, neginf=0.0)
    
    # Per-class AUC
    results = {}
    per_class = []
    for i in range(NUM_CLASSES):
        support = int(labels[:, i].sum())
        if support > 0 and support < len(labels):
            try:
                auc = roc_auc_score(labels[:, i], preds[:, i])
            except ValueError:
                auc = None
        else:
            auc = None
        per_class.append({
            "idx": i,
            "condition": CONDITION_NAMES[i],
            "auc": auc,
            "support": support,
        })
    
    # Overall metrics (only classes with support)
    valid_cols = labels.sum(0) > 0
    n_valid = valid_cols.sum()
    both_classes = np.array([
        labels[:, i].sum() > 0 and labels[:, i].sum() < len(labels)
        for i in range(NUM_CLASSES)
    ])
    
    if both_classes.sum() > 0:
        macro_auc = roc_auc_score(labels[:, both_classes], preds[:, both_classes],
                                   average="macro")
        micro_auc = roc_auc_score(labels[:, both_classes], preds[:, both_classes],
                                   average="micro")
    else:
        macro_auc = micro_auc = 0.0
    
    results = {
        "dataset": dataset_name,
        "n_records": len(X),
        "n_classes_with_support": int(n_valid),
        "macro_auc": round(macro_auc, 4),
        "micro_auc": round(micro_auc, 4),
        "per_class": sorted(
            [p for p in per_class if p["auc"] is not None],
            key=lambda x: x["auc"]
        ),
    }
    
    # Print summary
    print(f"\n  === {dataset_name}: {len(X):,} records ===")
    print(f"  Macro AUC: {macro_auc:.4f}  |  Micro AUC: {micro_auc:.4f}")
    print(f"  Classes with support: {int(n_valid)}")
    
    # Show weak classes (AUC < 0.90)
    weak = [p for p in per_class if p["auc"] is not None and p["auc"] < 0.90]
    if weak:
        print(f"  ⚠  WEAK classes (AUC < 0.90):")
        for p in sorted(weak, key=lambda x: x["auc"]):
            print(f"     {p['condition']:>10s}  AUC={p['auc']:.4f}  support={p['support']}")
    
    # Show top classes
    top = sorted([p for p in per_class if p["auc"] is not None],
                 key=lambda x: x["auc"], reverse=True)[:10]
    print(f"  Top 10 classes:")
    for p in top:
        print(f"     {p['condition']:>10s}  AUC={p['auc']:.4f}  support={p['support']}")
    
    return results


# ─── TRAINING ─────────────────────────────────────────────────────────────────
def train_combined(X_train, Y_train, X_val, Y_val, epochs=50, lr=1e-3):
    """Train the model on combined data."""
    train_ds = NpDataset(X_train, Y_train)
    val_ds   = NpDataset(X_val, Y_val)
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True, persistent_workers=True)
    val_loader   = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True, persistent_workers=True)
    
    model = EcgDSCNN().to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", patience=4, factor=0.5, min_lr=1e-6
    )
    criterion = nn.BCEWithLogitsLoss()
    
    best_auc = 0.0
    best_path = os.path.join(MODEL_DIR, "ecg_best_combined.pt")
    no_impr = 0
    log_rows = []
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n{'='*70}")
    print(f"  Combined Training")
    print(f"  Train: {len(train_ds):,}  |  Val: {len(val_ds):,}")
    print(f"  Params: {total_params:,}  |  Device: {DEVICE}")
    print(f"  Epochs: {epochs}  |  LR: {lr}  |  Batch: {BATCH_SIZE}")
    print(f"{'='*70}\n")
    
    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        train_loss = 0.0
        for xb, yb in tqdm(train_loader, desc=f"  Epoch {epoch:2d}/{epochs} [Train]",
                           leave=False):
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= len(train_ds)
        
        # Validate
        model.eval()
        all_preds, all_labels = [], []
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                pred = model(xb)
                val_loss += criterion(pred, yb).item() * len(xb)
                all_preds.append(torch.sigmoid(pred).cpu().numpy())
                all_labels.append(yb.cpu().numpy())
        val_loss /= len(val_ds)
        
        preds_np = np.vstack(all_preds)
        labels_np = np.vstack(all_labels)
        preds_np = np.nan_to_num(preds_np, nan=0.5, posinf=1.0, neginf=0.0)
        
        valid_cols = np.array([
            labels_np[:, i].sum() > 0 and labels_np[:, i].sum() < len(labels_np)
            for i in range(NUM_CLASSES)
        ])
        val_auc = roc_auc_score(labels_np[:, valid_cols], preds_np[:, valid_cols],
                                average="macro") if valid_cols.sum() > 0 else 0.0
        
        scheduler.step(val_auc)
        lr_now = optimizer.param_groups[0]["lr"]
        
        marker = "★" if val_auc > best_auc else " "
        print(f"  {marker} Epoch {epoch:3d}/{epochs} │ "
              f"train {train_loss:.4f} │ val {val_loss:.4f} │ "
              f"AUC {val_auc:.4f} │ lr {lr_now:.1e}")
        
        log_rows.append({"epoch": epoch, "train_loss": round(train_loss, 6),
                         "val_loss": round(val_loss, 6), "val_auc": round(val_auc, 6),
                         "lr": lr_now})
        
        if val_auc > best_auc:
            best_auc = val_auc
            torch.save(model.state_dict(), best_path)
            no_impr = 0
        else:
            no_impr += 1
            if no_impr >= 10:
                print(f"  Early stopping (10 epochs no improvement)")
                break
    
    # Save training log
    log_path = os.path.join(RESULTS_DIR, "training_log_combined.csv")
    with open(log_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=log_rows[0].keys())
        w.writeheader()
        w.writerows(log_rows)
    
    print(f"\n  Best val AUC: {best_auc:.4f}")
    print(f"  Model saved: {best_path}")
    
    model.load_state_dict(torch.load(best_path, map_location=DEVICE, weights_only=True))
    return model, best_auc


# ─── ONNX + TFLITE EXPORT ────────────────────────────────────────────────────
def export_onnx(model):
    onnx_path = os.path.join(MODEL_DIR, "ecg_combined.onnx")
    print(f"\n  Exporting ONNX → {onnx_path}")
    model.eval().cpu()
    
    class _Wrap(nn.Module):
        def __init__(self, m): super().__init__(); self.m = m
        def forward(self, x): return torch.sigmoid(self.m(x))
    
    wrapped = _Wrap(model)
    wrapped.eval()
    dummy = torch.zeros(1, N_LEADS, N_SAMPLES)
    torch.onnx.export(
        wrapped, dummy, onnx_path,
        input_names=["ecg_input"],
        output_names=["predictions"],
        dynamic_axes={"ecg_input": {0: "batch"}, "predictions": {0: "batch"}},
        opset_version=17,
    )
    import onnx
    onnx.checker.check_model(onnx_path)
    size_kb = os.path.getsize(onnx_path) / 1024
    print(f"  ONNX size: {size_kb:.1f} KB")
    return onnx_path


def export_tflite(onnx_path):
    print(f"\n  Converting ONNX → TFLite...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "onnx2tf",
             "-i", onnx_path, "-o", TFLITE_DIR, "-oiqt",
             "--not_use_onnxsim"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            for f in os.listdir(TFLITE_DIR):
                if f.endswith(".tflite"):
                    src = os.path.join(TFLITE_DIR, f)
                    dst = os.path.join(TFLITE_DIR, "ecg_combined_int8.tflite")
                    if src != dst:
                        os.rename(src, dst)
                    size_kb = os.path.getsize(dst) / 1024
                    print(f"  TFLite INT8 size: {size_kb:.1f} KB")
                    return dst
        else:
            print(f"  TFLite conversion failed: {result.stderr[-300:]}")
    except Exception as e:
        print(f"  TFLite conversion skipped: {e}")
    return None


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # ── Phase 1: Load model ──
    print("=" * 70)
    print("  PHASE 1: Loading trained model")
    print("=" * 70)
    
    model_path = os.path.join(MODEL_DIR, "ecg_best.pt")
    model = EcgDSCNN().to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=True))
    model.eval()
    print(f"  Loaded: {model_path}")
    print(f"  Classes: {NUM_CLASSES}, Device: {DEVICE}")
    
    # ── Phase 2: Load SPH test set (baseline) ──
    print(f"\n{'='*70}")
    print("  PHASE 2: Loading SPH baseline test set")
    print("=" * 70)
    
    sph_cache = os.path.join(CACHE_DIR, "dataset_cache.npz")
    if os.path.exists(sph_cache):
        data = np.load(sph_cache, allow_pickle=True)
        X_sph, Y_sph = data["X"], data["Y"]
        # Remove NaN records
        valid = np.isfinite(X_sph).reshape(X_sph.shape[0], -1).all(axis=1)
        X_sph, Y_sph = X_sph[valid], Y_sph[valid]
        print(f"  SPH cache loaded: {X_sph.shape[0]:,} records")
    else:
        print("  Loading SPH from raw files...")
        X_sph, Y_sph = load_dataset_records(SPH_PATH)
    
    # 70/15/15 split (matching evaluate_model.py)
    n = len(X_sph)
    rng = np.random.RandomState(42)
    idx = rng.permutation(n)
    n_train = int(n * 0.70)
    n_val   = int(n * 0.15)
    
    sph_train_idx = idx[:n_train]
    sph_val_idx   = idx[n_train:n_train + n_val]
    sph_test_idx  = idx[n_train + n_val:]
    
    X_sph_test = X_sph[sph_test_idx]
    Y_sph_test = Y_sph[sph_test_idx]
    print(f"  SPH test set: {len(X_sph_test):,} records")
    
    # Evaluate on SPH test (baseline)
    sph_results = evaluate_on_dataset(model, X_sph_test, Y_sph_test, "SPH (baseline)")
    
    # ── Phase 3: Evaluate on external datasets ──
    print(f"\n{'='*70}")
    print("  PHASE 3: Cross-dataset evaluation")
    print("=" * 70)
    
    all_results = {"sph_baseline": sph_results}
    external_data = {}
    
    for ds_name, ds_path in EXTERNAL_DATASETS.items():
        if not os.path.exists(ds_path):
            print(f"\n  {ds_name}: Directory not found, skipping.")
            continue
        
        cache_file = os.path.join(CACHE_DIR, f"cache_{ds_name}.npz")
        
        if os.path.exists(cache_file):
            data = np.load(cache_file, allow_pickle=True)
            X_ext, Y_ext = data["X"], data["Y"]
            print(f"\n  {ds_name}: Loaded from cache ({X_ext.shape[0]:,} records)")
        else:
            print(f"\n  {ds_name}: Loading from raw files...")
            X_ext, Y_ext = load_dataset_records(ds_path)
            if len(X_ext) > 0:
                np.savez_compressed(cache_file, X=X_ext, Y=Y_ext)
                mb = os.path.getsize(cache_file) / (1024 * 1024)
                print(f"    Cached: {cache_file} ({mb:.0f} MB)")
        
        if len(X_ext) > 0:
            external_data[ds_name] = (X_ext, Y_ext)
            results = evaluate_on_dataset(model, X_ext, Y_ext, ds_name)
            all_results[ds_name] = results
    
    # ── Phase 4: Aggregate weak classes ──
    print(f"\n{'='*70}")
    print("  PHASE 4: Weak class analysis")
    print("=" * 70)
    
    AUC_THRESHOLD = 0.90
    class_aucs = defaultdict(list)  # condition → [(dataset, auc, support)]
    
    for ds_name, res in all_results.items():
        if not res:
            continue
        for p in res.get("per_class", []):
            if p["auc"] is not None:
                class_aucs[p["condition"]].append(
                    (ds_name, p["auc"], p["support"])
                )
    
    # Find classes that are weak in ANY dataset
    weak_classes = {}
    for condition, entries in class_aucs.items():
        worst_auc = min(e[1] for e in entries)
        avg_auc = np.mean([e[1] for e in entries])
        total_support = sum(e[2] for e in entries)
        if worst_auc < AUC_THRESHOLD:
            weak_classes[condition] = {
                "worst_auc": round(worst_auc, 4),
                "avg_auc": round(avg_auc, 4),
                "total_support": total_support,
                "entries": entries,
            }
    
    if weak_classes:
        print(f"\n  Found {len(weak_classes)} weak classes (worst AUC < {AUC_THRESHOLD}):")
        for cond in sorted(weak_classes, key=lambda c: weak_classes[c]["worst_auc"]):
            info = weak_classes[cond]
            print(f"    {cond:>10s}  worst={info['worst_auc']:.4f}  "
                  f"avg={info['avg_auc']:.4f}  total_support={info['total_support']}")
            for ds, auc, sup in info["entries"]:
                print(f"      {ds:>20s}: AUC={auc:.4f}, n={sup}")
    else:
        print("  No weak classes found! All classes have AUC >= 0.90.")
    
    # ── Phase 5: Combine data and retrain ──
    if weak_classes:
        print(f"\n{'='*70}")
        print("  PHASE 5: Combined retraining")
        print("=" * 70)
        
        # Combine SPH training data with ALL external data
        X_train = X_sph[sph_train_idx]
        Y_train = Y_sph[sph_train_idx]
        X_val   = X_sph[sph_val_idx]
        Y_val   = Y_sph[sph_val_idx]
        
        print(f"  SPH train: {len(X_train):,}, val: {len(X_val):,}")
        
        for ds_name, (X_ext, Y_ext) in external_data.items():
            n_ext = len(X_ext)
            n_ext_train = int(n_ext * 0.85)
            perm = np.random.RandomState(42).permutation(n_ext)
            
            X_train = np.concatenate([X_train, X_ext[perm[:n_ext_train]]])
            Y_train = np.concatenate([Y_train, Y_ext[perm[:n_ext_train]]])
            X_val   = np.concatenate([X_val,   X_ext[perm[n_ext_train:]]])
            Y_val   = np.concatenate([Y_val,   Y_ext[perm[n_ext_train:]]])
            print(f"  + {ds_name}: {n_ext_train:,} train, {n_ext - n_ext_train:,} val")
        
        print(f"\n  Combined: {len(X_train):,} train, {len(X_val):,} val")
        
        # Shuffle training data
        perm = np.random.RandomState(42).permutation(len(X_train))
        X_train, Y_train = X_train[perm], Y_train[perm]
        
        # Label distribution
        train_support = Y_train.sum(axis=0)
        print(f"  Active classes in train: {int((train_support > 0).sum())}/{NUM_CLASSES}")
        
        # Train
        model_combined, best_auc = train_combined(X_train, Y_train, X_val, Y_val,
                                                   epochs=50, lr=1e-3)
        
        # ── Phase 6: Evaluate retrained model ──
        print(f"\n{'='*70}")
        print("  PHASE 6: Evaluating retrained model")
        print("=" * 70)
        
        model_combined.to(DEVICE)
        
        # On SPH test
        retrained_sph = evaluate_on_dataset(model_combined, X_sph_test, Y_sph_test,
                                            "SPH (retrained)")
        
        # On external datasets
        retrained_results = {"sph_retrained": retrained_sph}
        for ds_name, (X_ext, Y_ext) in external_data.items():
            res = evaluate_on_dataset(model_combined, X_ext, Y_ext,
                                      f"{ds_name} (retrained)")
            retrained_results[ds_name] = res
        
        # ── Comparison ──
        print(f"\n{'='*70}")
        print("  COMPARISON: Original vs Retrained")
        print("=" * 70)
        print(f"  {'Dataset':<25s} {'Original':<12s} {'Retrained':<12s} {'Δ':>8s}")
        print(f"  {'-'*57}")
        
        for ds in ["sph_baseline"] + list(EXTERNAL_DATASETS.keys()):
            orig = all_results.get(ds, {}).get("macro_auc", 0)
            ds_key = "sph_retrained" if ds == "sph_baseline" else ds
            retr = retrained_results.get(ds_key, {}).get("macro_auc", 0)
            delta = retr - orig
            sign = "+" if delta >= 0 else ""
            print(f"  {ds:<25s} {orig:<12.4f} {retr:<12.4f} {sign}{delta:>7.4f}")
        
        # Export ONNX + TFLite
        onnx_path = export_onnx(model_combined)
        tflite_path = export_tflite(onnx_path)
        
        # Save all results
        all_results["retrained"] = retrained_results
        all_results["retrained_best_auc"] = best_auc
    
    # ── Save results JSON ──
    results_path = os.path.join(RESULTS_DIR, "cross_dataset_evaluation.json")
    
    # Convert numpy types for JSON serialization
    def _convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=_convert)
    print(f"\n  Results saved: {results_path}")
    
    print(f"\n{'='*70}")
    print("  DONE!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
