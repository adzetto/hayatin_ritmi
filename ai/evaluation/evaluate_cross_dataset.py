"""
Cross-Dataset Evaluation & Combined Retraining
================================================
1. Load our trained DS-1D-CNN model
2. Evaluate on each external 12-lead ECG dataset
3. Report per-class AUC across datasets
4. Identify weak classes (AUC < 0.90)
5. If weak classes found -> combine external data -> retrain
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

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import box

console = Console()

# --- PATHS ----------------------------------------------------------------
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

# --- MODEL CONFIG ----------------------------------------------------------
FS_ORIGINAL = 500
FS_TARGET   = 250
N_SAMPLES   = 2500   # 10s at 250Hz
N_LEADS     = 12
BATCH_SIZE  = 128

# --- SNOMED MAP ------------------------------------------------------------
def load_snomed_map():
    codes, names = [], []
    with open(SNOMED_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            codes.append(int(row["Snomed_CT"]))
            names.append(row["Acronym Name"])
    return {code: i for i, code in enumerate(codes)}, names

SNOMED_MAP, CONDITION_NAMES = load_snomed_map()
NUM_CLASSES = len(SNOMED_MAP)

# Reverse map: index -> SNOMED code
IDX_TO_CODE = {i: code for code, i in SNOMED_MAP.items()}

# --- EXTERNAL DATASETS ----------------------------------------------------
EXTERNAL_DATASETS = {
    "cpsc2018":        os.path.join(DATASET_DIR, "cpsc2018"),
    "cpsc2018-extra":  os.path.join(DATASET_DIR, "cpsc2018-extra"),
    "georgia":         os.path.join(DATASET_DIR, "georgia"),
    "chapman-shaoxing":os.path.join(DATASET_DIR, "chapman-shaoxing"),
    "ningbo":          os.path.join(DATASET_DIR, "ningbo"),
}

# --- PREPROCESSING ---------------------------------------------------------
def bandpass(sig, fs=500, lo=0.5, hi=40.0, order=2):
    nyq = fs / 2.0
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, sig, axis=-1)


def preprocess(sig_12xN, original_fs=500):
    """(12, N) -> (12, 2500) normalized float32."""
    n_leads, n_samples = sig_12xN.shape
    if original_fs != 500:
        target_samples = int(n_samples * 500 / original_fs)
        sig_12xN = resample(sig_12xN, target_samples, axis=1)
        n_samples = target_samples
    if n_samples < 5000:
        pad_width = 5000 - n_samples
        sig_12xN = np.pad(sig_12xN, ((0, 0), (0, pad_width)), mode="constant")
    elif n_samples > 5000:
        sig_12xN = sig_12xN[:, :5000]
    sig = bandpass(sig_12xN, fs=500)
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    sig = sig[:, ::2]  # (12, 2500)
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


# --- MODEL -----------------------------------------------------------------
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


# --- DATA LOADING ----------------------------------------------------------
def load_dataset_records(dataset_path, max_records=None):
    """Load ECG records from a WFDB dataset with #Dx: SNOMED labels."""
    hea_files = glob.glob(os.path.join(dataset_path, "**", "*.hea"), recursive=True)

    X_list, Y_list = [], []
    skipped = 0

    desc = os.path.basename(dataset_path)
    for hea in tqdm(hea_files[:max_records] if max_records else hea_files,
                    desc=f"  Loading {desc}", unit="rec"):
        try:
            rec_path = hea[:-4]
            record = wfdb.rdrecord(rec_path)
            sig = record.p_signal
            if sig is None or sig.shape[1] < 12:
                skipped += 1
                continue
            sig = sig[:, :12].T
            fs = record.fs
            x = preprocess(sig, original_fs=fs)
            if x is None:
                skipped += 1
                continue
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
        except Exception:
            skipped += 1

    if X_list:
        X = np.array(X_list, dtype=np.float32)
        Y = np.array(Y_list, dtype=np.float32)
    else:
        X = np.zeros((0, 12, 2500), dtype=np.float32)
        Y = np.zeros((0, NUM_CLASSES), dtype=np.float32)

    console.print(f"    [green]{len(X_list):,}[/] records loaded, "
                  f"[yellow]{skipped:,}[/] skipped")
    return X, Y


class NpDataset(Dataset):
    def __init__(self, X, Y):
        self.X = torch.from_numpy(X)
        self.Y = torch.from_numpy(Y)
    def __len__(self):
        return len(self.X)
    def __getitem__(self, idx):
        return self.X[idx], self.Y[idx]


# --- EVALUATION ------------------------------------------------------------
def evaluate_on_dataset(model, X, Y, dataset_name):
    """Run inference, compute per-class AUC."""
    if len(X) == 0:
        console.print(f"  [yellow]{dataset_name}: No compatible records.[/]")
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

    # --- Rich summary ---
    console.print(Panel(
        f"[bold]{dataset_name}[/]  |  [cyan]{len(X):,}[/] records  |  "
        f"Macro AUC [bold green]{macro_auc:.4f}[/]  |  "
        f"Micro AUC [green]{micro_auc:.4f}[/]  |  "
        f"Classes: {int(n_valid)}",
        border_style="blue", expand=False,
    ))

    weak = [p for p in per_class if p["auc"] is not None and p["auc"] < 0.90]
    if weak:
        weak_tbl = Table(title="Weak Classes (AUC < 0.90)", box=box.SIMPLE,
                         border_style="yellow", expand=False)
        weak_tbl.add_column("Condition", style="yellow")
        weak_tbl.add_column("AUC", justify="right", style="bold red")
        weak_tbl.add_column("Support", justify="right")
        for p in sorted(weak, key=lambda x: x["auc"]):
            weak_tbl.add_row(p["condition"], f"{p['auc']:.4f}", str(p["support"]))
        console.print(weak_tbl)

    top = sorted([p for p in per_class if p["auc"] is not None],
                 key=lambda x: x["auc"], reverse=True)[:10]
    top_tbl = Table(title="Top 10 Classes", box=box.SIMPLE,
                    border_style="green", expand=False)
    top_tbl.add_column("Condition", style="cyan")
    top_tbl.add_column("AUC", justify="right", style="bold green")
    top_tbl.add_column("Support", justify="right")
    for p in top:
        top_tbl.add_row(p["condition"], f"{p['auc']:.4f}", str(p["support"]))
    console.print(top_tbl)

    return results


# --- TRAINING --------------------------------------------------------------
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

    console.print(Panel(
        f"[bold]Combined Training[/]\n"
        f"Train: [cyan]{len(train_ds):,}[/]  |  Val: [cyan]{len(val_ds):,}[/]\n"
        f"Params: [cyan]{total_params:,}[/]  |  Device: [cyan]{DEVICE}[/]\n"
        f"Epochs: [cyan]{epochs}[/]  |  LR: [cyan]{lr}[/]  |  Batch: [cyan]{BATCH_SIZE}[/]",
        border_style="bright_cyan", expand=False,
    ))

    epoch_tbl = Table(box=box.MINIMAL_DOUBLE_HEAD, border_style="dim",
                      show_edge=False, pad_edge=False)
    epoch_tbl.add_column("", style="bold", width=3)
    epoch_tbl.add_column("Epoch", justify="right", style="cyan", width=10)
    epoch_tbl.add_column("Train Loss", justify="right", width=12)
    epoch_tbl.add_column("Val Loss", justify="right", width=12)
    epoch_tbl.add_column("Val AUC", justify="right", style="bold", width=10)
    epoch_tbl.add_column("LR", justify="right", style="dim", width=10)

    for epoch in range(1, epochs + 1):
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

        marker = "[green]**[/]" if val_auc > best_auc else ""
        auc_style = "bold green" if val_auc > best_auc else "white"
        epoch_tbl.add_row(
            marker, f"{epoch}/{epochs}",
            f"{train_loss:.4f}", f"{val_loss:.4f}",
            f"[{auc_style}]{val_auc:.4f}[/]", f"{lr_now:.1e}",
        )

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
                epoch_tbl.add_row("", "[yellow]Early stop[/]", "", "", "", "")
                break

    console.print(epoch_tbl)

    log_path = os.path.join(RESULTS_DIR, "training_log_combined.csv")
    with open(log_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=log_rows[0].keys())
        w.writeheader()
        w.writerows(log_rows)

    console.print(f"\n  Best val AUC: [bold green]{best_auc:.4f}[/]")
    console.print(f"  Model saved: [dim]{best_path}[/]")

    model.load_state_dict(torch.load(best_path, map_location=DEVICE, weights_only=True))
    return model, best_auc


# --- ONNX + TFLITE EXPORT -------------------------------------------------
def export_onnx(model):
    onnx_path = os.path.join(MODEL_DIR, "ecg_combined.onnx")
    console.print(f"\n  Exporting ONNX -> [dim]{onnx_path}[/]")
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
    console.print(f"  ONNX size: [cyan]{size_kb:.1f} KB[/]")
    return onnx_path


def export_tflite(onnx_path):
    console.print(f"\n  Converting ONNX -> TFLite...")
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
                    console.print(f"  TFLite INT8 size: [cyan]{size_kb:.1f} KB[/]")
                    return dst
        else:
            console.print(f"  [yellow]TFLite conversion failed:[/] {result.stderr[-300:]}")
    except Exception as e:
        console.print(f"  [yellow]TFLite conversion skipped:[/] {e}")
    return None


# --- MAIN ------------------------------------------------------------------
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    # == Phase 1: Load model ==
    console.print(Panel("[bold]PHASE 1:[/] Loading trained model",
                        border_style="bright_cyan", expand=False))

    model_path = os.path.join(MODEL_DIR, "ecg_best.pt")
    model = EcgDSCNN().to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=True))
    model.eval()
    console.print(f"  Loaded: [dim]{model_path}[/]")
    console.print(f"  Classes: [cyan]{NUM_CLASSES}[/], Device: [cyan]{DEVICE}[/]")

    # == Phase 2: Load SPH test set (baseline) ==
    console.print(Panel("[bold]PHASE 2:[/] Loading SPH baseline test set",
                        border_style="bright_cyan", expand=False))

    sph_cache = os.path.join(CACHE_DIR, "dataset_cache.npz")
    if os.path.exists(sph_cache):
        data = np.load(sph_cache, allow_pickle=True)
        X_sph, Y_sph = data["X"], data["Y"]
        valid = np.isfinite(X_sph).reshape(X_sph.shape[0], -1).all(axis=1)
        X_sph, Y_sph = X_sph[valid], Y_sph[valid]
        console.print(f"  SPH cache loaded: [green]{X_sph.shape[0]:,}[/] records")
    else:
        console.print("  Loading SPH from raw files...")
        X_sph, Y_sph = load_dataset_records(SPH_PATH)

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
    console.print(f"  SPH test set: [green]{len(X_sph_test):,}[/] records")

    sph_results = evaluate_on_dataset(model, X_sph_test, Y_sph_test, "SPH (baseline)")

    # == Phase 3: Cross-dataset evaluation ==
    console.print(Panel("[bold]PHASE 3:[/] Cross-dataset evaluation",
                        border_style="bright_cyan", expand=False))

    all_results = {"sph_baseline": sph_results}
    external_data = {}

    for ds_name, ds_path in EXTERNAL_DATASETS.items():
        if not os.path.exists(ds_path):
            console.print(f"\n  [yellow]{ds_name}: Directory not found, skipping.[/]")
            continue

        cache_file = os.path.join(CACHE_DIR, f"cache_{ds_name}.npz")

        if os.path.exists(cache_file):
            data = np.load(cache_file, allow_pickle=True)
            X_ext, Y_ext = data["X"], data["Y"]
            console.print(f"\n  [green]{ds_name}:[/] Loaded from cache "
                          f"([cyan]{X_ext.shape[0]:,}[/] records)")
        else:
            console.print(f"\n  {ds_name}: Loading from raw files...")
            X_ext, Y_ext = load_dataset_records(ds_path)
            if len(X_ext) > 0:
                np.savez_compressed(cache_file, X=X_ext, Y=Y_ext)
                mb = os.path.getsize(cache_file) / (1024 * 1024)
                console.print(f"    Cached: [dim]{cache_file}[/] ({mb:.0f} MB)")

        if len(X_ext) > 0:
            external_data[ds_name] = (X_ext, Y_ext)
            results = evaluate_on_dataset(model, X_ext, Y_ext, ds_name)
            all_results[ds_name] = results

    # == Phase 4: Aggregate weak classes ==
    console.print(Panel("[bold]PHASE 4:[/] Weak class analysis",
                        border_style="bright_cyan", expand=False))

    AUC_THRESHOLD = 0.90
    class_aucs = defaultdict(list)

    for ds_name, res in all_results.items():
        if not res:
            continue
        for p in res.get("per_class", []):
            if p["auc"] is not None:
                class_aucs[p["condition"]].append(
                    (ds_name, p["auc"], p["support"])
                )

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
        console.print(f"\n  Found [bold red]{len(weak_classes)}[/] weak classes "
                      f"(worst AUC < {AUC_THRESHOLD}):")
        weak_summary = Table(box=box.ROUNDED, border_style="yellow", expand=False)
        weak_summary.add_column("Condition", style="yellow")
        weak_summary.add_column("Worst AUC", justify="right", style="bold red")
        weak_summary.add_column("Avg AUC", justify="right")
        weak_summary.add_column("Total Support", justify="right")

        for cond in sorted(weak_classes, key=lambda c: weak_classes[c]["worst_auc"]):
            info = weak_classes[cond]
            weak_summary.add_row(
                cond, f"{info['worst_auc']:.4f}",
                f"{info['avg_auc']:.4f}", str(info["total_support"]),
            )
        console.print(weak_summary)

        # Detail per dataset
        for cond in sorted(weak_classes, key=lambda c: weak_classes[c]["worst_auc"]):
            info = weak_classes[cond]
            detail_tbl = Table(title=f"{cond}", box=box.SIMPLE, expand=False,
                               border_style="dim")
            detail_tbl.add_column("Dataset", style="cyan")
            detail_tbl.add_column("AUC", justify="right")
            detail_tbl.add_column("n", justify="right")
            for ds, auc, sup in info["entries"]:
                auc_style = "red" if auc < 0.90 else "green"
                detail_tbl.add_row(ds, f"[{auc_style}]{auc:.4f}[/]", str(sup))
            console.print(detail_tbl)
    else:
        console.print("  [bold green]No weak classes found![/] "
                      "All classes have AUC >= 0.90.")

    # == Phase 5: Combine data and retrain ==
    if weak_classes:
        console.print(Panel("[bold]PHASE 5:[/] Combined retraining",
                            border_style="bright_cyan", expand=False))

        X_train = X_sph[sph_train_idx]
        Y_train = Y_sph[sph_train_idx]
        X_val   = X_sph[sph_val_idx]
        Y_val   = Y_sph[sph_val_idx]

        split_tbl = Table(box=box.SIMPLE, expand=False)
        split_tbl.add_column("Dataset", style="cyan")
        split_tbl.add_column("Train", justify="right")
        split_tbl.add_column("Val", justify="right")
        split_tbl.add_row("SPH", f"{len(X_train):,}", f"{len(X_val):,}")

        for ds_name, (X_ext, Y_ext) in external_data.items():
            n_ext = len(X_ext)
            n_ext_train = int(n_ext * 0.85)
            perm = np.random.RandomState(42).permutation(n_ext)

            X_train = np.concatenate([X_train, X_ext[perm[:n_ext_train]]])
            Y_train = np.concatenate([Y_train, Y_ext[perm[:n_ext_train]]])
            X_val   = np.concatenate([X_val,   X_ext[perm[n_ext_train:]]])
            Y_val   = np.concatenate([Y_val,   Y_ext[perm[n_ext_train:]]])
            split_tbl.add_row(ds_name, f"{n_ext_train:,}", f"{n_ext - n_ext_train:,}")

        split_tbl.add_row("[bold]Combined[/]", f"[bold]{len(X_train):,}[/]",
                          f"[bold]{len(X_val):,}[/]")
        console.print(split_tbl)

        perm = np.random.RandomState(42).permutation(len(X_train))
        X_train, Y_train = X_train[perm], Y_train[perm]

        train_support = Y_train.sum(axis=0)
        console.print(f"  Active classes in train: "
                      f"[cyan]{int((train_support > 0).sum())}/{NUM_CLASSES}[/]")

        model_combined, best_auc = train_combined(X_train, Y_train, X_val, Y_val,
                                                   epochs=50, lr=1e-3)

        # == Phase 6: Evaluate retrained model ==
        console.print(Panel("[bold]PHASE 6:[/] Evaluating retrained model",
                            border_style="bright_cyan", expand=False))

        model_combined.to(DEVICE)

        retrained_sph = evaluate_on_dataset(model_combined, X_sph_test, Y_sph_test,
                                            "SPH (retrained)")

        retrained_results = {"sph_retrained": retrained_sph}
        for ds_name, (X_ext, Y_ext) in external_data.items():
            res = evaluate_on_dataset(model_combined, X_ext, Y_ext,
                                      f"{ds_name} (retrained)")
            retrained_results[ds_name] = res

        # -- Comparison table --
        cmp_tbl = Table(title="Original vs Retrained", box=box.DOUBLE_EDGE,
                        border_style="bright_green")
        cmp_tbl.add_column("Dataset", style="cyan")
        cmp_tbl.add_column("Original", justify="right")
        cmp_tbl.add_column("Retrained", justify="right", style="bold")
        cmp_tbl.add_column("Delta", justify="right")

        for ds in ["sph_baseline"] + list(EXTERNAL_DATASETS.keys()):
            orig = all_results.get(ds, {}).get("macro_auc", 0)
            ds_key = "sph_retrained" if ds == "sph_baseline" else ds
            retr = retrained_results.get(ds_key, {}).get("macro_auc", 0)
            delta = retr - orig
            delta_style = "green" if delta >= 0 else "red"
            sign = "+" if delta >= 0 else ""
            cmp_tbl.add_row(
                ds, f"{orig:.4f}", f"{retr:.4f}",
                f"[{delta_style}]{sign}{delta:.4f}[/]",
            )
        console.print(cmp_tbl)

        onnx_path = export_onnx(model_combined)
        tflite_path = export_tflite(onnx_path)

        all_results["retrained"] = retrained_results
        all_results["retrained_best_auc"] = best_auc

    # == Save results JSON ==
    results_path = os.path.join(RESULTS_DIR, "cross_dataset_evaluation.json")

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

    console.print(Panel(
        f"[bold green]DONE![/]\nResults saved: [dim]{results_path}[/]",
        border_style="green", expand=False,
    ))


if __name__ == "__main__":
    main()
