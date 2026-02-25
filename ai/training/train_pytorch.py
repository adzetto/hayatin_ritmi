"""
ECG Aritmisi Sınıflandırıcı — PyTorch + CUDA Eğitim Scripti
============================================================
Veri   : PhysioNet SPH 12-Lead ECG Arrhythmia (45,152 kayıt)
Model  : Depthwise Separable 1D CNN (~280K param)
Export : ONNX → TFLite INT8 (Android backend)
GPU    : RTX 4050 Laptop (CUDA 12.4)

Çalıştır:
  python dataset/train_ecg_pytorch.py
"""

import os, sys, csv, time, json, hashlib
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from scipy.signal import butter, filtfilt
import wfdb
from huggingface_hub import HfApi
from sklearn.metrics import roc_auc_score
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich import box

console = Console()

# ── .env'den token oku ──────────────────────────────────────
def _load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ═══════════════════════════════════════════════════════════
#  YAPILANDIRMA
# ═══════════════════════════════════════════════════════════
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR       = os.path.join(PROJECT_ROOT, "ai")
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset", "ecg-arrhythmia")
MODEL_DIR    = os.path.join(AI_DIR, "models", "checkpoints")
RESULTS_DIR  = os.path.join(AI_DIR, "models", "results")
TFLITE_DIR   = os.path.join(AI_DIR, "models", "tflite")
CACHE_DIR    = os.path.join(AI_DIR, "cache")
SNOMED_CSV   = os.path.join(DATASET_PATH, "ConditionNames_SNOMED-CT.csv")
RECORDS_FILE = os.path.join(DATASET_PATH, "RECORDS")

HF_TOKEN   = os.environ.get("HF_TOKEN", "")
HF_REPO_ID = "adzetto/ecg-arrhythmia-classifier"

FS_ORIGINAL = 500
FS_TARGET   = 250
N_SAMPLES   = FS_TARGET * 10   # 2500
N_LEADS     = 12
BATCH_SIZE  = 128               # RTX 4050 6GB → 128 rahat
EPOCHS      = 50
LR          = 1e-3
VAL_RATIO   = 0.15
CACHE_FILE  = os.path.join(CACHE_DIR, "dataset_cache.npz")
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(TFLITE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
#  1. SNOMED-CT LABEL MAP
# ═══════════════════════════════════════════════════════════
def load_snomed_map():
    codes, names = [], []
    with open(SNOMED_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            codes.append(int(row["Snomed_CT"]))
            names.append(row["Acronym Name"])
    return {code: i for i, code in enumerate(codes)}, names

SNOMED_MAP, CONDITION_NAMES = load_snomed_map()
NUM_CLASSES = len(SNOMED_MAP)

# ═══════════════════════════════════════════════════════════
#  2. ÖN İŞLEME + DATASET
# ═══════════════════════════════════════════════════════════
def bandpass(sig, fs=500, lo=0.5, hi=40.0, order=2):
    nyq = fs / 2.0
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, sig, axis=-1)

def preprocess(sig_12xN):
    """(12,5000) → (12,2500) normalize float32. Returns None if signal is degenerate."""
    sig = bandpass(sig_12xN)
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)    # bandpass can produce NaN on bad leads
    sig = sig[:, ::2]                                             # 500→250 Hz
    std = sig.std(axis=1, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)                         # avoid div-by-zero for flat leads
    sig = (sig - sig.mean(axis=1, keepdims=True)) / std
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    out = sig.astype(np.float32)
    if not np.isfinite(out).all():
        return None
    return out                                                    # (12, 2500)

def parse_dx(hea_path):
    codes = []
    try:
        with open(hea_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#Dx:"):
                    for c in line.split(":")[1].strip().split(","):
                        try: codes.append(int(c.strip()))
                        except ValueError: pass
    except Exception: pass
    return codes


class EcgDataset(Dataset):
    def __init__(self, X, Y):
        # X: (N,12,2500) float32, Y: (N,49) float32
        self.X = torch.from_numpy(X)
        self.Y = torch.from_numpy(Y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.Y[idx]


def _cache_hash():
    """Hash RECORDS file + SNOMED CSV to detect dataset changes."""
    h = hashlib.md5()
    for p in [RECORDS_FILE, SNOMED_CSV]:
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:12]


def load_all_records():
    # ── Try loading from cache ──
    expected_hash = _cache_hash()
    if os.path.exists(CACHE_FILE):
        console.print("[bold cyan]💾 Önbellek kontrol ediliyor...[/]")
        data = np.load(CACHE_FILE, allow_pickle=True)
        if str(data.get("hash", "")) == expected_hash:
            X, Y = data["X"], data["Y"]
            # Sanitize any NaN/Inf from old cache
            nan_mask = ~np.isfinite(X).reshape(X.shape[0], -1).all(axis=1)
            if nan_mask.any():
                console.print(f"[yellow]⚠  {nan_mask.sum()} NaN kayıt önbellekten temizlendi[/]")
                X, Y = X[~nan_mask], Y[~nan_mask]
            console.print(f"[bold green]⚡ Önbellekten yüklendi![/]  "
                          f"[dim]({CACHE_FILE})[/]")
            console.print(f"   [cyan]{X.shape[0]:,}[/] kayıt, hash=[dim]{expected_hash}[/]")
            return X, Y
        else:
            console.print("[yellow]⚠  Önbellek eskimiş, yeniden yükleniyor...[/]")

    # ── Parse from raw WFDB files ──
    with open(RECORDS_FILE, encoding="utf-8") as f:
        folders = [l.strip() for l in f if l.strip()]

    # Count total .hea files for accurate progress bar
    all_records = []
    for folder in folders:
        fpath = os.path.join(DATASET_PATH, folder)
        if not os.path.isdir(fpath):
            continue
        for fname in sorted(os.listdir(fpath)):
            if fname.endswith(".hea"):
                all_records.append(os.path.join(fpath, fname[:-4]))

    X_list, Y_list, skipped = [], [], 0

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40, style="cyan", complete_style="bold green", finished_style="bold green"),
        TextColumn("[green]{task.completed}/{task.total}"),
        TextColumn("[dim]•[/]"),
        TextColumn("[yellow]{task.fields[loaded]}[/] loaded"),
        TextColumn("[dim]•[/]"),
        TimeElapsedColumn(),
        TextColumn("[dim]ETA[/]"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("ECG kayıtları işleniyor", total=len(all_records), loaded=0)

        for rec in all_records:
            try:
                record = wfdb.rdrecord(rec)
                if record.p_signal.shape != (5000, 12):
                    skipped += 1
                    progress.advance(task)
                    continue
                x = preprocess(record.p_signal.T)
                if x is None:
                    skipped += 1
                    progress.update(task, advance=1, loaded=len(X_list))
                    continue
                label = np.zeros(NUM_CLASSES, dtype=np.float32)
                for code in parse_dx(rec + ".hea"):
                    if code in SNOMED_MAP:
                        label[SNOMED_MAP[code]] = 1.0
                X_list.append(x)
                Y_list.append(label)
            except Exception:
                skipped += 1
            progress.update(task, advance=1, loaded=len(X_list))

    X = np.array(X_list, dtype=np.float32)
    Y = np.array(Y_list, dtype=np.float32)

    # ── Save cache ──
    console.print(f"[bold cyan]💾 Önbelleğe kaydediliyor...[/] [dim]{CACHE_FILE}[/]")
    np.savez_compressed(CACHE_FILE, X=X, Y=Y, hash=expected_hash)
    cache_mb = os.path.getsize(CACHE_FILE) / (1024 * 1024)
    console.print(f"   [green]✅ Kaydedildi[/] ({cache_mb:.0f} MB) — bir sonraki çalıştırmada anında yüklenecek")

    console.print(f"   [green]✅ Toplam:[/] [cyan]{len(X_list):,}[/] kayıt, "
                  f"[yellow]{skipped:,}[/] atlanan")
    return X, Y

# ═══════════════════════════════════════════════════════════
#  3. MODEL — Depthwise Separable 1D CNN
# ═══════════════════════════════════════════════════════════
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
    """
    Girdi : (B, 12, 2500)
    Çıktı : (B, 49) — sigmoid
    Param : ~280K
    """
    def __init__(self, n_leads=N_LEADS, n_classes=NUM_CLASSES):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(n_leads, 32, 15, stride=2, padding=7, bias=False),  # →(B,32,1250)
            nn.BatchNorm1d(32),
            nn.ReLU6(),
        )
        self.blocks = nn.Sequential(
            DSConv1d(32,  64,  kernel_size=7, stride=2),   # →(B, 64, 625)
            DSConv1d(64,  128, kernel_size=7, stride=2),   # →(B,128, 313)
            DSConv1d(128, 128, kernel_size=5, stride=2),   # →(B,128, 157)
            DSConv1d(128, 256, kernel_size=5, stride=2),   # →(B,256,  79)
            DSConv1d(256, 256, kernel_size=3, stride=2),   # →(B,256,  40)
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),       # →(B,256,1)
            nn.Flatten(),                  # →(B,256)
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU6(),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        return self.head(x)   # raw logits — use BCEWithLogitsLoss during training


# ═══════════════════════════════════════════════════════════
#  4. EĞİTİM
# ═══════════════════════════════════════════════════════════
def train_model(X, Y):
    dataset = EcgDataset(X, Y)
    n_val   = int(len(dataset) * VAL_RATIO)
    n_train = len(dataset) - n_val
    train_ds, val_ds = random_split(dataset, [n_train, n_val],
                                    generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True, persistent_workers=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True, persistent_workers=True)

    model = EcgDSCNN().to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters())

    # ── Training info table ──
    info_table = Table(box=box.ROUNDED, title="[bold magenta]⚙️  Eğitim Konfigürasyonu[/]",
                       title_style="bold", border_style="bright_blue")
    info_table.add_column("Parametre", style="cyan")
    info_table.add_column("Değer", style="bold white")
    info_table.add_row("Device", f"{DEVICE}" + (f" ({torch.cuda.get_device_name(0)})" if DEVICE.type == 'cuda' else ""))
    info_table.add_row("Train / Val", f"{n_train:,} / {n_val:,}")
    info_table.add_row("Parametre", f"{total_params:,}")
    info_table.add_row("Batch / Epoch", f"{BATCH_SIZE} / {EPOCHS}")
    info_table.add_row("Learning Rate", f"{LR}")
    info_table.add_row("Loss", "BCEWithLogitsLoss")
    info_table.add_row("Optimizer", "Adam + ReduceLROnPlateau")
    console.print(info_table)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", patience=4, factor=0.5, min_lr=1e-6
    )
    criterion = nn.BCEWithLogitsLoss()

    best_auc  = 0.0
    best_path = os.path.join(MODEL_DIR, "ecg_best.pt")
    no_impr   = 0
    log_rows  = []

    console.print("\n[bold green]🚂 Eğitim başlıyor...[/]\n")

    for epoch in range(1, EPOCHS + 1):
        # ── Train ──
        model.train()
        train_loss = 0.0
        t0 = time.time()

        train_bar = tqdm(train_loader, desc=f"  Epoch {epoch:2d}/{EPOCHS} [Train]",
                         leave=False, ncols=100,
                         bar_format="{l_bar}{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
        for xb, yb in train_bar:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * len(xb)
            train_bar.set_postfix(loss=f"{loss.item():.4f}")
        train_loss /= n_train

        # ── Val ──
        model.eval()
        all_preds, all_labels = [], []
        val_loss = 0.0

        val_bar = tqdm(val_loader, desc=f"  Epoch {epoch:2d}/{EPOCHS} [Val]  ",
                       leave=False, ncols=100,
                       bar_format="{l_bar}{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
        with torch.no_grad():
            for xb, yb in val_bar:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                pred = model(xb)
                val_loss += criterion(pred, yb).item() * len(xb)
                all_preds.append(torch.sigmoid(pred).cpu().numpy())
                all_labels.append(yb.cpu().numpy())
        val_loss /= n_val

        preds_np  = np.vstack(all_preds)
        labels_np = np.vstack(all_labels)
        preds_np  = np.nan_to_num(preds_np, nan=0.5, posinf=1.0, neginf=0.0)

        valid_cols = labels_np.sum(0) > 0
        val_auc = roc_auc_score(labels_np[:, valid_cols], preds_np[:, valid_cols],
                                average="macro") if valid_cols.sum() > 0 else 0.0

        scheduler.step(val_auc)
        elapsed = time.time() - t0
        lr_now  = optimizer.param_groups[0]["lr"]

        # ── Colorful epoch summary ──
        auc_color = "bold green" if val_auc > best_auc else "yellow"
        console.print(
            f"  [bold cyan]Epoch {epoch:3d}/{EPOCHS}[/] │ "
            f"train [red]{train_loss:.4f}[/] │ "
            f"val [red]{val_loss:.4f}[/] │ "
            f"AUC [{auc_color}]{val_auc:.4f}[/] │ "
            f"lr [dim]{lr_now:.1e}[/] │ "
            f"[dim]{elapsed:.0f}s[/]",
        )

        log_rows.append({"epoch": epoch, "train_loss": train_loss,
                         "val_loss": val_loss, "val_auc": val_auc, "lr": lr_now})

        if val_auc > best_auc:
            best_auc = val_auc
            torch.save(model.state_dict(), best_path)
            console.print(f"    [bold green]★ Yeni en iyi model![/] AUC={best_auc:.4f}")
            no_impr = 0
        else:
            no_impr += 1
            if no_impr >= 10:
                console.print(f"  [bold red]⏹  Early stopping[/] (10 epoch iyileşme yok)")
                break

    # Log kaydet
    import csv as csv_mod
    log_path = os.path.join(RESULTS_DIR, "training_log.csv")
    with open(log_path, "w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=log_rows[0].keys())
        writer.writeheader()
        writer.writerows(log_rows)

    console.print(f"\n[bold green]🏆 En iyi val AUC: {best_auc:.4f}[/]")

    model.load_state_dict(torch.load(best_path, map_location=DEVICE))
    return model, best_auc

# ═══════════════════════════════════════════════════════════
#  5. ONNX EXPORT
# ═══════════════════════════════════════════════════════════
def export_onnx(model, onnx_path):
    print(f"\n📦 ONNX export: {onnx_path}")
    model.eval().cpu()

    # Wrap with sigmoid so ONNX output is probabilities (not logits)
    class _SigmoidWrapper(nn.Module):
        def __init__(self, m): super().__init__(); self.m = m
        def forward(self, x): return torch.sigmoid(self.m(x))

    export_model = _SigmoidWrapper(model)
    export_model.eval()
    dummy = torch.zeros(1, N_LEADS, N_SAMPLES)
    torch.onnx.export(
        export_model, dummy, onnx_path,
        input_names=["ecg_input"],
        output_names=["predictions"],
        dynamic_axes={"ecg_input": {0: "batch"}, "predictions": {0: "batch"}},
        opset_version=17,
    )
    import onnx
    onnx.checker.check_model(onnx_path)
    size_kb = os.path.getsize(onnx_path) / 1024
    print(f"   ✅ ONNX boyutu: {size_kb:.1f} KB")
    return onnx_path

# ═══════════════════════════════════════════════════════════
#  6. ONNX → TFLite (onnx2tf)
# ═══════════════════════════════════════════════════════════
def export_tflite(onnx_path, tflite_dir):
    print(f"\n📦 TFLite dönüşümü...")
    try:
        import subprocess
        result = subprocess.run(
            [
                sys.executable,
                "-m", "onnx2tf",
                "-i", onnx_path,
                "-o", tflite_dir,
                "-oiqt",              # INT8 quantization
                "--not_use_onnxsim",
            ],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            tflite_path = os.path.join(tflite_dir, "ecg_model_int8.tflite")
            # onnx2tf dosyayı farklı isimle kaydedebilir, bul
            for f in os.listdir(tflite_dir):
                if f.endswith(".tflite"):
                    src = os.path.join(tflite_dir, f)
                    tflite_path = os.path.join(tflite_dir, "ecg_model_int8.tflite")
                    os.rename(src, tflite_path)
                    break
            size_kb = os.path.getsize(tflite_path) / 1024
            print(f"   ✅ TFLite boyutu: {size_kb:.1f} KB")
            return tflite_path
        else:
            print(f"   ⚠️  onnx2tf hatası: {result.stderr[-500:]}")
            print("   ℹ️  ONNX dosyası HF'e yükleniyor (Android ONNX Runtime ile kullanılabilir)")
            return None
    except Exception as e:
        print(f"   ⚠️  TFLite dönüşümü atlandı: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#  7. HUGGINGFace'E YÜKLEME
# ═══════════════════════════════════════════════════════════
def push_to_hub(model, onnx_path, tflite_path, best_auc):
    if not HF_TOKEN:
        print("⚠️  HF_TOKEN yok, yükleme atlandı.")
        return

    print(f"\n🤗 HuggingFace'e yükleniyor: {HF_REPO_ID}")
    api = HfApi(token=HF_TOKEN)

    # PyTorch weights
    pt_path = os.path.join(MODEL_DIR, "ecg_best.pt")
    api.upload_file(path_or_fileobj=pt_path, path_in_repo="ecg_best.pt",
                    repo_id=HF_REPO_ID, repo_type="model", token=HF_TOKEN,
                    commit_message=f"PyTorch weights (val_auc={best_auc:.4f})")

    # ONNX
    api.upload_file(path_or_fileobj=onnx_path, path_in_repo="ecg_model.onnx",
                    repo_id=HF_REPO_ID, repo_type="model", token=HF_TOKEN,
                    commit_message="ONNX model for cross-framework use")

    # TFLite (varsa)
    if tflite_path and os.path.exists(tflite_path):
        api.upload_file(path_or_fileobj=tflite_path, path_in_repo="ecg_model_int8.tflite",
                        repo_id=HF_REPO_ID, repo_type="model", token=HF_TOKEN,
                        commit_message="INT8 TFLite model for Android")

    # Training log
    log_path = os.path.join(MODEL_DIR, "training_log.csv")
    if os.path.exists(log_path):
        api.upload_file(path_or_fileobj=log_path, path_in_repo="training_log.csv",
                        repo_id=HF_REPO_ID, repo_type="model", token=HF_TOKEN,
                        commit_message="Training log")

    # Model config (Android için)
    config = {
        "conditions": CONDITION_NAMES,
        "num_classes": NUM_CLASSES,
        "input_shape_onnx": [1, N_LEADS, N_SAMPLES],
        "input_shape_tflite": [1, N_SAMPLES, N_LEADS],
        "sample_rate_hz": FS_TARGET,
        "original_sample_rate_hz": FS_ORIGINAL,
        "best_val_auc": round(best_auc, 6),
        "architecture": "DS-1D-CNN (Depthwise Separable)",
        "framework": "PyTorch 2.6 + CUDA 12.4",
        "project": "TÜBİTAK 2209-A — Hayatın Ritmi",
    }
    api.upload_file(
        path_or_fileobj=json.dumps(config, indent=2, ensure_ascii=False).encode(),
        path_in_repo="model_config.json",
        repo_id=HF_REPO_ID, repo_type="model", token=HF_TOKEN,
        commit_message="Model config with label names"
    )

    print(f"   ✅ Yüklendi: https://huggingface.co/{HF_REPO_ID}")

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold white]ECG ARİTMİ EĞİTİMİ[/]\n"
        "[cyan]PyTorch + CUDA · DS-1D-CNN · RTX 4050[/]\n"
        "[dim]TÜBİTAK 2209-A — Hayatın Ritmi[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE,
        padding=(1, 4),
    ))

    # GPU info
    if DEVICE.type == "cuda":
        console.print(f"  [bold green]🖥️  GPU:[/] {torch.cuda.get_device_name(0)} "
                      f"([cyan]{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB[/] VRAM)")
    else:
        console.print("  [bold yellow]⚠  CPU modu[/]")
    console.print(f"  [bold green]🏷️  Sınıflar:[/] {NUM_CLASSES} SNOMED-CT kondisyon")
    console.print()

    # 1. Dataset yükle
    X, Y = load_all_records()

    # Dataset stats table
    stats_table = Table(box=box.SIMPLE_HEAVY, border_style="cyan", title="[bold]📊 Dataset İstatistikleri[/]")
    stats_table.add_column("Metrik", style="cyan")
    stats_table.add_column("Değer", style="bold white")
    stats_table.add_row("Kayıt sayısı", f"{X.shape[0]:,}")
    stats_table.add_row("Lead sayısı", f"{X.shape[1]}")
    stats_table.add_row("Örnek uzunluğu", f"{X.shape[2]:,} ({X.shape[2]/FS_TARGET:.0f}s @ {FS_TARGET}Hz)")
    stats_table.add_row("Sınıf sayısı", str(Y.shape[1]))
    stats_table.add_row("Pozitif oran", f"{Y.mean():.4f}")
    stats_table.add_row("X bellek", f"{X.nbytes / 1024**3:.2f} GB")
    console.print(stats_table)

    # 2. Eğit
    model, best_auc = train_model(X, Y)

    # 3. ONNX export
    onnx_path = os.path.join(MODEL_DIR, "ecg_model.onnx")
    export_onnx(model, onnx_path)

    # 4. TFLite dönüşümü (onnx2tf varsa)
    os.makedirs(TFLITE_DIR, exist_ok=True)
    tflite_path = export_tflite(onnx_path, TFLITE_DIR)

    # 5. HuggingFace'e yükle
    push_to_hub(model, onnx_path, tflite_path, best_auc)

    # Final summary
    result_table = Table(box=box.DOUBLE_EDGE, title="[bold green]✅ TAMAMLANDI[/]",
                         border_style="green", title_style="bold")
    result_table.add_column("Çıktı", style="cyan")
    result_table.add_column("Yol", style="white")
    result_table.add_row("PT model", os.path.join(MODEL_DIR, 'ecg_best.pt'))
    result_table.add_row("ONNX", onnx_path)
    result_table.add_row("TFLite", tflite_path or '[dim]dönüşüm atlandı[/]')
    result_table.add_row("HF Repo", f"https://huggingface.co/{HF_REPO_ID}")
    console.print(result_table)
    print(f"   Val AUC   : {best_auc:.4f}")
